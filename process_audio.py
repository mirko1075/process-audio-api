#!/usr/bin/env python3

from collections import defaultdict
import os
from pathlib import Path
from pprint import pprint
import subprocess
import logging
import ffmpeg
import openai
from dotenv import load_dotenv
import assemblyai as aai
from transformers import pipeline
import re
import tiktoken
import time
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage

load_dotenv()

# Constants
MAX_CHUNK_SIZE_MB = 20  # Max file size in MB before we chunk
OVERLAP_SECONDS = 30  # Overlap between chunks (in seconds)
CHUNK_DURATION_SECONDS = 19 * 60  # Each chunk is 19 minutes (in seconds)

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not aai.settings.api_key:
    raise ValueError("ASSEMBLYAI_API_KEY must be set in the .env file")

logging.basicConfig(level=logging.DEBUG)


# Check if credentials are set
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "config/secrets/gcs.json")
if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    raise FileNotFoundError(f"Google credentials not found at {GOOGLE_CREDENTIALS_PATH}")

# Initialize clients
speech_client = speech.SpeechClient()
storage_client = storage.Client()


def split_text_at_sentences(text):
    # Split text at sentence boundaries (., !, ?)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return sentences

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
        print(f"FFmpeg error: {e.stderr.decode()}")
        raise RuntimeError(f"Failed to convert file to WAV: {e.stderr.decode()}")


def get_duration(input_file):
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

        total_duration = get_duration(input_file)
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

def transcribe_audio(audio_file, language):
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

def process_file(file_path, temp_dir, language):
    """
    Processes a single audio file: splits if necessary, transcribes, and combines results.
    """
    try:
        logging.debug(f"Starting to process file: {file_path}")

        file_size = os.path.getsize(file_path)
        duration = get_duration(file_path)
        logging.debug(f"File size: {file_size / (1024 * 1024):.2f} MB")
        logging.debug(f"Duration: {duration / 60:.2f} minutes")

        if file_size <= MAX_CHUNK_SIZE_MB * 1024 * 1024:
            logging.info("File under size limit - processing as single file")

            text = transcribe_audio(file_path, language)  # Use the Whisper API
            logging.debug(f"Transcription result: {text}")
            return text
        else:
            logging.info(f"File over {MAX_CHUNK_SIZE_MB}MB - splitting into chunks")
            chunk_files = split_audio(file_path, temp_dir)
            logging.debug(f"Split into {len(chunk_files)} chunks")

            combined_texts = []
            for i, chunk in enumerate(chunk_files, 1):
                logging.debug(f"Processing chunk {i}/{len(chunk_files)}: {chunk}")
                text = transcribe_audio(chunk, language)  # Use the Whisper API
                combined_texts.append(text)
                os.remove(chunk)
                logging.info(f"Chunk {i} processed and removed")

            logging.debug(f"Combined transcription results: {combined_texts}")
            return "\n".join(combined_texts)

    except Exception as e:
        logging.error(f"Error processing file: {file_path}, {e}")
        raise

def transcribe_audio_assemblyai(file_path=None, language=None, best_model=False):
    """
    Transcribes audio using AssemblyAI API. Supports both file URLs and local file paths.

    Args:
        file_url (str): URL of the audio file to transcribe.
        file_path (str): Local path of the audio file to transcribe.

    Returns:
        dict: Transcription result or error message.
    """
    try:
        if best_model:
            speech_model = aai.SpeechModel.best
        else:
            speech_model = aai.SpeechModel.nano
        if not file_path:
            raise ValueError("Either file_url or file_path must be provided.")

        if language:
            language = language
            language_detection = False
        else:
            language = None
            language_detection = True

        config = aai.TranscriptionConfig(speech_model=speech_model, language_detection=True, speaker_labels=True, punctuate=True, format_text=True)

        transcriber = aai.Transcriber()
        FILE_URL = file_path
        # Transcribe from a URL
        transcript = transcriber.transcribe(FILE_URL, config=config)
        logging.debug(f"ASSEMBLYAI TRANSCRIPT DONE")
        # Handle errors
        if transcript.status == aai.TranscriptStatus.error:
            return {"ASSEMBLYAI error": transcript.error}
        
        final_text = ""
        for utterance in transcript.utterances:
            final_text += f"Speaker {utterance.speaker}: {utterance.text}\n"

        # Return transcription text
        return final_text

    except Exception as e:
        return {"error": str(e)}


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


def split_diarized_text(speaker_lines, model="gpt-3.5-turbo", max_tokens=1000):
    """Splits a diarized transcript (list format) into chunks without cutting a speaker's sentence"""
    
    if not isinstance(speaker_lines, list):  # Ensure the input is a list
        raise ValueError(f"Expected a list of strings, but got {type(speaker_lines)}")

    logging.debug(f"Splitting text into chunks with model: {model} and max tokens: {max_tokens}")
    
    enc = tiktoken.encoding_for_model(model)

    # Join the list into a single text block with newline separation
    text = "\n".join(speaker_lines)

    tokens = enc.encode(text)  # Tokenize the entire text
    logging.debug(f"Total tokens: {len(tokens)}")

    chunks = []
    current_chunk = []
    current_chunk_tokens = 0

    for line in speaker_lines:
        if not line.strip():  # Skip empty lines
            continue

        line_tokens = len(enc.encode(line))  # Get token count for this line
        logging.debug(f"Processing line: {line[:30]}... | Tokens: {line_tokens}")

        # If adding this line exceeds the token limit, start a new chunk
        if current_chunk_tokens + line_tokens > max_tokens:
            chunks.append("\n".join(current_chunk))  # Save the current chunk
            current_chunk = [line]  # Start a new chunk with the current line
            current_chunk_tokens = line_tokens  # Reset token counter
        else:
            current_chunk.append(line)
            current_chunk_tokens += line_tokens
    
    # Append the last chunk if not empty
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def transcribe_audio(gcs_uri, language_code="en-US", diarization=True):
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
    print("Waiting for transcription to complete...")

    while not operation.done():
        print("Transcription in progress...")
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
