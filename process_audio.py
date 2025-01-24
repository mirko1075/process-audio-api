#!/usr/bin/env python3

import os
from pathlib import Path
import subprocess
import logging
import ffmpeg
import openai
import requests
from dotenv import load_dotenv
import whisper

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_API_URL = os.getenv("DEEPGRAM_API_URL")
print(f"DEEPGRAM_API_KEY: {DEEPGRAM_API_KEY}")
print(f"DEEPGRAM_API_URL: {DEEPGRAM_API_URL}")

# Constants
MAX_CHUNK_SIZE_MB = 20  # Max file size in MB before we chunk
OVERLAP_SECONDS = 30  # Overlap between chunks (in seconds)
CHUNK_DURATION_SECONDS = 19 * 60  # Each chunk is 19 minutes (in seconds)

logging.basicConfig(level=logging.DEBUG)

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
        openai.api_key = os.getenv("OPENAI_API_KEY")

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

def process_file(file_path, temp_dir):
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

            # Detect language and transcribe the single file
            detected_language = detect_language_with_deepgram(file_path)
            logging.info(f"Detected language: {detected_language}")

            text = transcribe_audio(file_path, detected_language)  # Use the Whisper API
            logging.debug(f"Transcription result: {text}")
            return text
        else:
            logging.info(f"File over {MAX_CHUNK_SIZE_MB}MB - splitting into chunks")
            chunk_files = split_audio(file_path, temp_dir)
            logging.debug(f"Split into {len(chunk_files)} chunks")


            # Detect language from the first chunk
            detected_language = detect_language_with_deepgram(chunk_files[0])
            logging.info(f"Detected language from first chunk: {detected_language}")


            combined_texts = []
            for i, chunk in enumerate(chunk_files, 1):
                logging.debug(f"Processing chunk {i}/{len(chunk_files)}: {chunk}")
                text = transcribe_audio(chunk, detected_language)  # Use the Whisper API
                combined_texts.append(text)
                os.remove(chunk)
                logging.info(f"Chunk {i} processed and removed")

            logging.debug(f"Combined transcription results: {combined_texts}")
            return "\n".join(combined_texts)

    except Exception as e:
        logging.error(f"Error processing file: {file_path}, {e}")
        raise

def detect_language_with_deepgram(audio_file_path):
    """
    Detect the language of the audio file using Deepgram's API.
    """
    logging.debug(f"Detecting language with Deepgram for {audio_file_path}")
    logging.debug(f"DEEPGRAM_API_KEY: {DEEPGRAM_API_KEY}")
    try:
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav",
        }
        params = {
            "model": "nova-2-general",
            "detect_language": "true",
        }

        with open(audio_file_path, "rb") as file:
            response = requests.post(DEEPGRAM_API_URL, headers=headers, params=params, data=file)
            response.raise_for_status()
            result = response.json()

            # Extract the detected language
            detected_language = result["results"]["channels"][0]["detected_language"]
            confidence = result["results"]["channels"][0].get("language_confidence", 1.0)
            logging.info(f"Detected language: {detected_language} (Confidence: {confidence:.2f})")
            return detected_language
    except requests.RequestException as e:
        logging.error(f"Error detecting language with Deepgram: {e}")
        return "en"  # Default to English on error
    
def detect_language_with_whisper(audio_file):
    """
    Detect the language of an audio file using Whisper.
    """
    try:
        # Save the file temporarily
        temp_path = os.path.join("/tmp", audio_file.filename)
        audio_file.save(temp_path)
        
        logging.debug(f"Detecting language with Whisper for {temp_path}")
        
        # Load Whisper model
        model = whisper.load_model("large")
        
        # Ensure the audio file is in the correct format (Mono, 16kHz)
        processed_audio_path = os.path.join("/tmp", f"processed_{audio_file.filename}")
        subprocess.run([
            "ffmpeg", "-i", temp_path, 
            "-ac", "1", "-ar", "16000", "-y", processed_audio_path
        ], check=True)
        
        # Load and preprocess audio
        audio = whisper.load_audio(processed_audio_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        
        # Detect language
        _, probs = model.detect_language(mel)
        detected_language = max(probs, key=probs.get)
        
        logging.info(f"Detected language: {detected_language}")
        
        # Clean up temporary files
        os.remove(temp_path)
        os.remove(processed_audio_path)
        
        return detected_language
    except Exception as e:
        logging.error(f"Error detecting language with Whisper: {e}")
        return "en"  # Default to English on error
