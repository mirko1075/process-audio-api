#!/usr/bin/env python3

from collections import defaultdict
import html
from html.parser import HTMLParser
import os
from pathlib import Path
from pprint import pprint
import subprocess
import logging
import ffmpeg
from dotenv import load_dotenv
import tiktoken
from transformers import pipeline
import re
import time
import openai
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from google.cloud import translate_v2 as translate
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from bs4 import BeautifulSoup  # This works with beautifulsoup4

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Constants
MAX_CHUNK_SIZE_MB = 20  # Max file size in MB before we chunk
OVERLAP_SECONDS = 30  # Overlap between chunks (in seconds)
CHUNK_DURATION_SECONDS = 19 * 60  # Each chunk is 19 minutes (in seconds)


logging.basicConfig(level=logging.DEBUG)


# Check if credentials are set
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "config/secrets/gcs.json")
if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    raise FileNotFoundError(f"Google credentials not found at {GOOGLE_CREDENTIALS_PATH}")

# Initialize clients
speech_client = speech.SpeechClient()
storage_client = storage.Client()
client = openai.OpenAI(api_key=OPENAI_API_KEY)  # ✅ Correct OpenAI Client initialization


def split_text_at_sentences(text):
    # Split text at sentence boundaries (., !, ?)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return sentences

def get_audio_duration(input_file):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
        'default=noprint_wrappers=1:nokey=1', input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    logging.debug(f"FFprobe output: {result.stdout.strip()}")  # Log the output
    if result.returncode != 0:
        logging.error(f"FFprobe error: {result.stderr.strip()}")  # Log any errors
        raise RuntimeError(f"FFprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())

def split_audio(input_file, output_dir, chunk_duration=CHUNK_DURATION_SECONDS, overlap=OVERLAP_SECONDS):
    """
    Splits the input audio file into smaller chunks with specified duration and overlap.
    """
    try:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        total_duration = get_audio_duration(input_file)
        start_times = [
            max(0, i * (chunk_duration - overlap))
            for i in range(int(total_duration // chunk_duration) + 1)
        ]

        chunk_files = []
        for idx, start in enumerate(start_times):
            chunk_filename = os.path.join(output_dir, f"{Path(input_file).stem}_chunk{idx + 1}.mp3")
            duration = min(chunk_duration, total_duration - start)

            # Use ffmpeg-python to create the chunk
            (
                ffmpeg
                .input(input_file, ss=start, t=duration)
                .output(chunk_filename, acodec='libmp3lame')
                .run(overwrite_output=True)
            )

            # Check if the chunk file was created successfully
            if os.path.exists(chunk_filename):
                logging.debug(f"Chunk created: {chunk_filename}")
                chunk_files.append(chunk_filename)
            else:
                logging.error(f"Failed to create chunk: {chunk_filename}")

        return chunk_files

    except Exception as e:
        logging.error(f"Error splitting audio: {e}")
        raise

def transcribe_audio_openai(audio_file, language):
    """
    Transcribes an audio file using OpenAI's Whisper API.
    """
    try:
        # Set your OpenAI API key

        # Open the audio file in binary mode
        with open(audio_file, "rb") as file:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=file,
                temperature=0.0,
                language=language
            )
        return response.text
    except Exception as e:
        logging.error(f"Error transcribing {audio_file}: {e}")
        raise

def perform_sentiment_analysis(text=None, best_model=False):
    """
    Performs sentiment analysis on the given text.

    Args:
        text (str): The text to analyze.
        best_model (bool): Whether to use the best model (not used in this example).

    Returns:
        dict: Sentiment analysis results.
    """
    try:

        # Load a pre-trained sentiment analysis model
        sentiment_analyzer = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
        # Split text into sentences
        sentences = split_text_at_sentences(text)

        # Analyze sentiment for each sentence
        results = []
        for sentence in sentences:
            if sentence.strip():  # Skip empty strings
                result = sentiment_analyzer(sentence)
                results.append((sentence, result[0]['label'], result[0]['score'] * 100))

        # Aggregate sentiment results
        sentiment_counts = defaultdict(int)
        total_score = 0

        for sentence, label, score in results:
            sentiment_counts[label] += 1
            total_score += score if label == "positive" else -score

        # Calculate average sentiment
        average_sentiment = "POSITIVE" if total_score >= 0 else "NEGATIVE"
        average_confidence = abs(total_score) / len(results)

        # Return results
        return {
            "sentiment_analysis": results,
            "average_sentiment": average_sentiment,
            "average_confidence": average_confidence,
            "positive_sentences": sentiment_counts.get("positive", 0),
            "negative_sentences": sentiment_counts.get("negative", 0),
            "neutral_sentences": sentiment_counts.get("neutral", 0)
        }

    except Exception as e:
        return {"error": str(e)}

def transcribe_audio_with_google_diarization(gcs_uri, language_code="en-US", diarization=True):
    """Transcribes audio from GCS with speaker diarization."""
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_automatic_punctuation=True,
        enable_speaker_diarization=diarization,
        diarization_speaker_count=2  # Adjust based on expected speakers
    )

    audio = speech.RecognitionAudio(uri=gcs_uri)

    # Long-running recognition for large files
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    logging.info("Waiting for transcription to complete...")

    while not operation.done():
        logging.info("Transcription in progress...")
        time.sleep(5)

    response = operation.result()
    result_text = ""

    for result in response.results:
        for alt in result.alternatives:
            result_text += f"{alt.transcript}\n"

    return result_text

def upload_to_gcs(file_path, bucket_name, destination_blob_name):
    """Uploads a file to Google Cloud Storage."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    return f"gs://{bucket_name}/{destination_blob_name}"

def delete_from_gcs(gcs_uri):
    """Deletes a file from Google Cloud Storage."""
    bucket_name, blob_name = gcs_uri.split("/blob/")[-2:]
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()

def translate_text_google(text_list, target_language):
    """
    Translates text using Google Translate API in batches of max 128 segments.
    """
    try:
        logging.info(f"Translating text to: {target_language}")
        translate_client = translate.Client()
        
        # Ensure input is a list
        if not isinstance(text_list, list):
            text_list = [text_list]

        # Google Translate API allows max 128 segments per request
        MAX_SEGMENTS = 128  
        translated_texts = []

        # Split text_list into batches of MAX_SEGMENTS
        for i in range(0, len(text_list), MAX_SEGMENTS):
            batch = text_list[i:i + MAX_SEGMENTS]  # Create a batch

            response = translate_client.translate(
                batch, target_language=target_language
            )

            # Extract translated text
            translated_texts.extend([res["translatedText"] for res in response])

        return {'translated_texts': translated_texts, 'joined_translated_text': ' '.join(translated_texts)}

    except Exception as e:
        logging.error(f"Error during translation: {e}")
        raise

def format_transcript(response):
    """Formats the transcript with speaker diarization"""
    try:
        result = response.results.channels[0].alternatives[0]
        formatted_transcript_array = []
        current_speaker = None
        current_text = ""
            
        for word in result.words:
            if word.speaker != current_speaker:
                if current_speaker is not None:
                    formatted_transcript_array.append(f"Speaker {current_speaker}: {html.unescape(BeautifulSoup(current_text.strip(), 'html.parser').text)}")
                current_speaker = word.speaker
                current_text = ""
            current_text += word.punctuated_word + " "

        if current_text:
            formatted_transcript_array.append(f"Speaker {current_speaker}: {html.unescape(BeautifulSoup(current_text.strip(), 'html.parser').text)}")
        logging.info(f"TYPE OF FORMATTED TRANSCRIPT: {type(formatted_transcript_array)}")
        return {
            "formatted_transcript_array": formatted_transcript_array,
            "transcript": html.unescape(BeautifulSoup(response.results.channels[0].alternatives[0].paragraphs.transcript, 'html.parser').text)
        }

    except Exception as e:
        logging.error(f"Error formatting transcript: {e}")
        raise

def transcribe_with_deepgram(audio_file, language="en"):
    """Processes and transcribes an uploaded audio file"""
    try:
        logging.info(f"Processing audio file: {audio_file.filename}")

        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        buffer_data = audio_file.read()

        payload: FileSource = {"buffer": buffer_data}

        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            language=language,
            diarize=True,
            dictation=True,
            filler_words=True,
            utterances=True,
        )

        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options, timeout=240)
        return format_transcript(response)

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        raise


# Tokenizer for chunking large texts
def split_text_into_chunks(text, model="gpt-4-turbo", max_tokens=1000):
    """Splits text into chunks without cutting sentences."""
    enc = tiktoken.encoding_for_model(model)
    words = text.split("\n")  # Splitting by lines
    chunks = []
    current_chunk = []
    current_chunk_tokens = 0

    for line in words:
        line_tokens = len(enc.encode(line))  # Get token count for this line
        if current_chunk_tokens + line_tokens > max_tokens:
            chunks.append("\n".join(current_chunk))  # Save the current chunk
            current_chunk = [line]  # Start a new chunk
            current_chunk_tokens = line_tokens
        else:
            current_chunk.append(line)
            current_chunk_tokens += line_tokens
    
    # Append the last chunk
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def translate_text_with_openai(text, source_lang="auto", target_lang="en"):
    """Translates text using OpenAI GPT-4 with the most accurate possible output."""
    try:
        logging.info(f"Translating from {source_lang} to {target_lang} using OpenAI GPT-4 Turbo")

        # Split text into chunks to avoid token limits
        text_chunks = split_text_into_chunks(text)
        translated_chunks = []
        text_chunks_length = len(text_chunks)
        logging.info(f"Translating {text_chunks_length} chunks")
        for i, chunk in enumerate(text_chunks, 1):
            if chunk != "":
                logging.info(f"Translating chunk {i} of {text_chunks_length}")
                prompt = f"""You are an expert translator. Translate the following text from {source_lang} to {target_lang}. 
                Ensure perfect accuracy, preserving meaning and idioms.
                
                Text:
                {chunk}

                Translated Text:
                """
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "system", "content": prompt}],
                    temperature=0.1
                )
                translated_text = response.choices[0].message.content.strip()
                translated_chunks.append(translated_text)

        return "\n".join(translated_chunks)  # Join chunks together

    except Exception as e:
        logging.error(f"Error during translation: {e}")
        raise

def convert_to_wav(input_path, output_path):
    """
    Converts an audio file to WAV format using FFmpeg.
    """
    try:
        logging.debug(f"Converting {input_path} to WAV format")
        cmd = [
            "ffmpeg", "-i", input_path,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            "-y",
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.debug(f"File converted to WAV: {output_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        raise RuntimeError(f"Failed to convert file to WAV: {e.stderr.decode()}")


def transcribe_audio_with_whisper(audio_file, language):
    """
    Transcribes an audio file using OpenAI's Whisper API.
    """
    try:
        # Set your OpenAI API key

        # Open the audio file in binary mode
        with open(audio_file, "rb") as file:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=file,
                temperature=0.0,
                language=language
            )
        return response.text
    except Exception as e:
        logging.error(f"Error transcribing {audio_file}: {e}")
        raise

def transcript_with_whisper_large_files(file_path, temp_dir, language):
    """
    Processes a single audio file: splits if necessary, transcribes, and combines results.
    """
    try:
        logging.debug(f"Starting to process file: {file_path}")

        file_size = os.path.getsize(file_path)
        duration = get_audio_duration(file_path)
        logging.debug(f"File size: {file_size / (1024 * 1024):.2f} MB")
        logging.debug(f"Duration: {duration / 60:.2f} minutes")

        if file_size <= MAX_CHUNK_SIZE_MB * 1024 * 1024:
            logging.info("File under size limit - processing as single file")

            text = transcribe_audio_with_whisper(file_path, language)  # Use the Whisper API
            logging.debug(f"Transcription result: {text}")
            return text
        else:
            logging.info(f"File over {MAX_CHUNK_SIZE_MB}MB - splitting into chunks")
            chunk_files = split_audio(file_path, temp_dir)
            logging.debug(f"Split into {len(chunk_files)} chunks")

            combined_texts = []
            for i, chunk in enumerate(chunk_files, 1):
                logging.debug(f"Processing chunk {i}/{len(chunk_files)}: {chunk}")
                text = transcribe_audio_with_whisper(chunk, language)  # Use the Whisper API
                combined_texts.append(text)
                os.remove(chunk)
                logging.info(f"Chunk {i} processed and removed")

            logging.debug(f"Combined transcription results: {combined_texts}")
            return "\n".join(combined_texts)

    except Exception as e:
        logging.error(f"Error processing file: {file_path}, {e}")
        raise