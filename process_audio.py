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
from transformers import pipeline
import re
import time
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from google.cloud import translate_v2 as translate
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from bs4 import BeautifulSoup  # This works with beautifulsoup4

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
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


def split_text_at_sentences(text):
    # Split text at sentence boundaries (., !, ?)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return sentences

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

def translate_text(text_list, target_language):
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

        return translated_texts

    except Exception as e:
        logging.error(f"Error during translation: {e}")
        raise

def format_transcript(response):
    """Formats the transcript with speaker diarization"""
    try:
        result = response.results.channels[0].alternatives[0]
        formatted_transcript = []
        current_speaker = None
        current_text = ""

        for word in result.words:
            if word.speaker != current_speaker:
                if current_speaker is not None:
                    formatted_transcript.append(f"Speaker {current_speaker}: {html.unescape(BeautifulSoup(current_text.strip(), 'html.parser').text)}")
                current_speaker = word.speaker
                current_text = ""
            current_text += word.punctuated_word + " "

        if current_text:
            formatted_transcript.append(f"Speaker {current_speaker}: {html.unescape(BeautifulSoup(current_text.strip(), 'html.parser').text)}")

        return formatted_transcript

    except Exception as e:
        logging.error(f"Error formatting transcript: {e}")
        raise

def process_audio_file(audio_file, language="en"):
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
            detect_entities=True,
            sentiment=True
        )

        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options, timeout=240)

        return format_transcript(response)

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        raise