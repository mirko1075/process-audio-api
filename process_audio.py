#!/usr/bin/env python3

from collections import defaultdict
import html
import io
import json
import os
from pathlib import Path
import subprocess
import logging
import tempfile
import ffmpeg
from dotenv import load_dotenv
import httpx
import pandas as pd
import requests
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
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from docx import Document
import os
from pydub import AudioSegment
import deepl
load_dotenv()

# Constants
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    raise ValueError("Missing AssemblyAI API key. Set it in .env file as ASSEMBLYAI_API_KEY.")

ASSEMBLYAI_URL = "https://api.assemblyai.com/v2/upload"
TRANSCRIPTION_URL = "https://api.assemblyai.com/v2/transcript"



headers = {"authorization": ASSEMBLYAI_API_KEY}
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_CHUNK_SIZE_MB = 20  # Max file size in MB before we chunk
OVERLAP_SECONDS = 30  # Overlap between chunks (in seconds)
CHUNK_DURATION_SECONDS = 19 * 60  # Each chunk is 19 minutes (in seconds)
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "config/secrets/gcs.json")
# Tariffa per minuto (€12 per ora = €0,20 al minuto)
RATE_PER_MINUTE = 12 / 60  
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_PATH, scope)

google_client = gspread.authorize(creds)


logging.basicConfig(level=logging.INFO)


# Check if credentials are set

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

#get audio duration from form file

def get_audio_duration_from_form_file(audio_file):
    try:
        # Save uploaded audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
            temp_file.write(audio_file.read())
            temp_file_path = temp_file.name

        # Use ffprobe to get the duration
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                temp_file_path
            ],
            capture_output=True,
            text=True
        )

        os.remove(temp_file_path)  # Clean up temp file

        if result.returncode != 0:
            return None, "FFprobe failed to analyze audio."

        duration_data = json.loads(result.stdout)
        seconds = float(duration_data["format"]["duration"])
        minutes = round(seconds / 60, 2)

        return minutes, None

    except Exception as e:
        return None, f"Error reading audio duration: {str(e)}"
    
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
        sentiment_analyzer = pipeline("sentiment-analysis", model="brettclaus/Hospital_Reviews")
        print(f"Sentiment analyzer: {sentiment_analyzer}")
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
        logging.info(f"RESULT: {result}")
        for word in result.words:
            logging.info(f"WORD: {word}")
            if word.speaker != current_speaker:
                if current_speaker is not None:
                    clean_text = html.unescape(BeautifulSoup(current_text.strip(), 'html.parser').text)
                    formatted_transcript_array.append(f"Speaker {current_speaker}: {clean_text}")
                current_speaker = word.speaker
                current_text = ""
            current_text += word.punctuated_word + " "
        if current_text:
            clean_text = html.unescape(BeautifulSoup(current_text.strip(), 'html.parser').text)
            formatted_transcript_array.append(f"Speaker {current_speaker}: {clean_text}")
        logging.info(f"TYPE OF FORMATTED TRANSCRIPT: {type(formatted_transcript_array)}")
        # Join the array with newline characters; these will be properly escaped in JSON.
        transcript = "\n".join(formatted_transcript_array)
        return {
            "formatted_transcript_array": formatted_transcript_array,
            "transcript": transcript
        }
    except Exception as e:
        logging.error(f"Error formatting transcript: {e}")
        raise


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
            model="whisper",
            smart_format=True,
            language=language,
            paragraphs=True,
            utterances=True
        )
        timeout = httpx.Timeout(300.0, connect=10.0)
        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options, timeout=timeout)
        return format_transcript(response)

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        raise


# Tokenizer for chunking large texts
def split_text_into_chunks(text, model="gpt-4o", max_tokens=500):
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

def split_text_into_chunks_oriental(text, language_hint="th", max_tokens=500):
    """Optimized chunking for Asian languages with sentence boundary awareness."""
    # Asian language sentence boundaries (add more as needed)
    sentence_delimiters = {
        "th": [" ", "\n", "。", "．", "ฯ", "ๆ"],
        "zh": ["\n", "。", "，", "；", "！", "？"],
        "ja": ["\n", "。", "、", "！", "？", "」"],
        "default": ["\n", ".", "!", "?", "\r"]
    }
    
    # Use character count approximation for Asian languages
    if language_hint in ["th", "zh", "ja", "ko"]:
        max_chars = max_tokens * 2  # Conservative estimate (2 chars/token)
        delimiter_set = sentence_delimiters.get(language_hint, sentence_delimiters["default"])
    else:
        max_chars = max_tokens * 4  # Default estimate (4 chars/token for Western languages)
        delimiter_set = sentence_delimiters["default"]

    chunks = []
    current_chunk = []
    current_length = 0
    buffer = ""

    def safe_add(chunk, buffer):
        if buffer:
            chunk.append(buffer.strip())
            return len(buffer)
        return 0

    for char in text:
        buffer += char
        current_length += 1
        
        # Check for sentence boundaries
        if char in delimiter_set:
            # Check if adding this would exceed limit
            if (current_length + len(buffer)) > max_chars:
                # Flush current buffer to chunk
                chunk_length = safe_add(current_chunk, buffer)
                current_length = chunk_length
                buffer = ""
                
                # Start new chunk if over limit
                if chunk_length >= max_chars:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

    # Add remaining text
    safe_add(current_chunk, buffer)
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # Final cleanup for small chunks
    merged_chunks = []
    current_merged = []
    current_merged_length = 0
    
    for chunk in chunks:
        chunk_length = len(chunk)
        if current_merged_length + chunk_length <= max_chars * 1.2:
            current_merged.append(chunk)
            current_merged_length += chunk_length
        else:
            merged_chunks.append("\n".join(current_merged))
            current_merged = [chunk]
            current_merged_length = chunk_length
    
    if current_merged:
        merged_chunks.append("\n".join(current_merged))

    return merged_chunks

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
                system_prompt = f"""You are a professional medical translator specialized in translating Thai to English. You are also an expert in medical terminology, treatments, and pharmacological terms. You are helping translate transcriptions of interviews between doctors and patients in the medical research field.

                You must:
                - Translate all content accurately from Thai to English.
                - Ensure correct use of clinical, pharmaceutical, and disease-specific terms. Avoid general terms if precise medical equivalents exist.
                - Perform speaker diarization by identifying from context who is speaking (either "Interviewer" or "Interviewee").
                - Maintain paragraph grouping: if the same speaker continues for multiple sentences, their text must remain under the same speaker label.
                - Maintain the logical structure of a professional interview, avoid adding, omitting, or altering intent or meaning.
                - Format the translation cleanly with alternating speaker blocks starting with "Interviewer:" or "Interviewee:" followed by their respective content.

                Do not explain your reasoning. Your response must only contain the clean translated dialogue.
                Do not add extra text at the beginning nor at the end. No titles, no footers, no comments, no explanations, no notes, no nothing.
                """
                prompt = f"""
                    Please translate the following medical interview transcript from Thai to English.

                    Follow these rules:
                    - Identify who is speaking: Interviewer or Interviewee.
                    - Maintain correct speaker attribution and group multiple sentences from the same speaker into a single block.
                    - Use medically precise English language.
                    - Do not skip or summarize. Translate all parts fully.

                    Thai transcript:

                    Text TO TRANSLATE:  
                    {chunk}

                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    temperature=0.0
                )
                translated_text = response.choices[0].message.content.strip()
                translated_chunks.append(translated_text)

        return "\n".join(translated_chunks)  # Join chunks together

    except Exception as e:
        logging.error(f"Error during translation: {e}")
        raise


def translate_text_with_openai_oriental(text, source_lang="auto", target_lang="en"):
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
                system_prompt = f"""As a medical translation expert, translate this {source_lang} text to {target_lang} with:
                                - Exact preservation of medical terminology
                                - Natural handling of Asian language particles (ครับ/ค่ะ/-san/-sama)
                                - Explicit [Note:] markers for ambiguous terms, but only if the term is ambiguous, in any case write the translation of the term.
                                - Strict structural fidelity
                """
                prompt = f"""
                    Translate the following text from {source_lang} to {target_lang} with extreme precision, especially in medical terminology, molecule names, test names, and ambiguous phrases. Strictly follow these guidelines:

                    **Accuracy is Paramount** 
                    Ensure to not leave any part of the text untranslated.
                    Ensure that all medical terms, anatomical references, and disease names are translated with precision and according to standard medical terminology in {target_lang}.  
                    DO NOT assume common meanings—always verify potential medical interpretations before finalizing the translation.

                    **Molecule Names & Test Names**  
                    Always retain the full and precise name of any molecule, biomarker, protein, enzyme, drug, or laboratory test.  
                    If the {source_lang} term seems truncated or missing qualifiers (e.g., missing the organ/system of origin), verify the full form based on context and use the medically correct name in {target_lang}.  
                    If a term refers to a specific diagnostic test, branded test, or proprietary medical product, explicitly use its official {target_lang} name instead of a generic translation.

                    **Handling Ambiguous or Implicit Terms**  
                    If the {source_lang} text omits crucial clarifications, assess the context and select the most medically appropriate translation in {target_lang}.  
                    If uncertain, add a clarifying note in brackets (e.g., “elastase [assumed pancreatic elastase-1 based on context]”).  
                    If a term has multiple medical interpretations, prioritize the most relevant meaning for the given context.  
                    If a term has a non-medical common meaning but is used in a medical context, translate it using the appropriate medical terminology.

                    **Double-Check for Proprietary or Branded Terms**  
                    If the term could refer to a specific branded medical test, reagent, or molecule, research the correct name in {target_lang} and use it explicitly instead of a generic translation.

                    **Contextual Understanding & Verification**  
                    Read the entire passage before translating individual terms to ensure correct medical interpretation.  
                    If necessary, restructure phrases to match the correct medical syntax in {target_lang} while preserving accuracy.

                    **Standard Terminology**  
                    Use official medical nomenclature from sources such as ICD, MedDRA, WHO, or equivalent regulatory bodies in {target_lang}.  
                    If a direct translation does not exist, use the closest medical equivalent or provide a brief clarifying phrase.

                    **Understandability in {target_lang}**  
                    If the {source_lang} text includes colloquial, abbreviated, or commonly-used phrasing that is recognized in conversation or transcription, translate it into the most **natural, clear, and understandable** equivalent in {target_lang} while preserving medical accuracy and context.  
                    Prefer terminology that would be readily understood by healthcare professionals or patients in a clinical setting in {target_lang}.

                    

                    **Diarization**  
                    If the text is diarized, keep the diarization in the translation but use as Speaker names Speaker A, Speaker B, etc.
                    If the text is not diarized, add diarization to the translation to indicate the speaker of the text, use Speaker A, Speaker B, etc.

                    **Post-Translation Verification**
                    After producing the translation, **perform a second pass**  to double check that all the input text has been translated.
                    After producing the translation, **perform a third pass** to double-check that the result is **coherent, medically meaningful, and contextually accurate**.  
                    Look for phrases that could be made **more fluent or precise** in {target_lang}, and improve them without altering the original meaning.  
                    Prioritize clarity and alignment with common usage in medical documentation or clinical communication.

                    **SPECIFIC REQUIREMENTS:**
                    1. Preserve numerical values and measurements exactly
                    2. Handle Asian-specific:
                    - Thai honorific particles → natural equivalents if applies
                    - Chinese measure words → localized properly if applies
                    - Japanese contextual honorifics if applies
                    3. Mark uncertain terms with [Assumed:...]
                    4. Maintain original speaker labels (Speaker A/B), use always A, B, C instead of numbers to identify the Speakers.
                    5. **IMPORTANT** Do not add any other text or comments to the translation
                    6. **IMPORTANT** Do not add any other text or titles that are not part of the translation, no Title, No footer, nothing more than translation and text for translated text explication.
                    7. **IMPORTANT** Do not add any other text or comments to the translation, no Title, No footer, nothing more than translation and text for translated text explication.
                    7. **IMPORTANT** Remove any title as **TRANSLATION TASK:**

                    Text TO TRANSLATE:  
                    {chunk}

                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    temperature=0.0
                )
                translated_text = response.choices[0].message.content.strip()
                translated_chunks.append(translated_text)

        return "\n".join(translated_chunks)  # Join chunks together

    except Exception as e:
        logging.error(f"Error during translation: {e}")
        raise


def translate_text_with_deepseek(text, source_lang="auto", target_lang="en"):
    """Translates text using DeepSeek API with medical accuracy"""
    try:
        logging.info(f"Translating from {source_lang} to {target_lang} using DeepSeek")

        # Configure your DeepSeek credentials
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
        DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }

        text_chunks = split_text_into_chunks_oriental(text, language_hint=source_lang)
        translated_chunks = []
        text_chunks_length = len(text_chunks)
        logging.info(f"Translating {text_chunks_length} chunks")
        for i, chunk in enumerate(text_chunks, 0):
            if chunk.strip():
                logging.info(f"Translating chunk {i} of {text_chunks_length}")
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""As a medical translation expert, translate this {source_lang} text to {target_lang} with:
                                - Exact preservation of medical terminology
                                - Natural handling of Asian language particles (ครับ/ค่ะ/-san/-sama)
                                - Explicit [Note:] markers for ambiguous terms
                                - Strict structural fidelity"""
                        },
                        {
                            "role": "user",
                            "content": f"""TRANSLATION TASK:
                            {chunk}
                            **Accuracy is Paramount** 
                            Ensure to not leave any part of the text untranslated.
                            Ensure that all medical terms, anatomical references, and disease names are translated with precision and according to standard medical terminology in {target_lang}.  
                            DO NOT assume common meanings—always verify potential medical interpretations before finalizing the translation.

                            **Molecule Names & Test Names**  
                            Always retain the full and precise name of any molecule, biomarker, protein, enzyme, drug, or laboratory test.  
                            If the {source_lang} term seems truncated or missing qualifiers (e.g., missing the organ/system of origin), verify the full form based on context and use the medically correct name in {target_lang}.  
                            If a term refers to a specific diagnostic test, branded test, or proprietary medical product, explicitly use its official {target_lang} name instead of a generic translation.

                            **Handling Ambiguous or Implicit Terms**  
                            If the {source_lang} text omits crucial clarifications, assess the context and select the most medically appropriate translation in {target_lang}.  
                            If uncertain, add a clarifying note in brackets (e.g., “elastase [assumed pancreatic elastase-1 based on context]”).  In this case, be sure to write as well the translation.
                            If a term has multiple medical interpretations, prioritize the most relevant meaning for the given context.  
                            If a term has a non-medical common meaning but is used in a medical context, translate it using the appropriate medical terminology.

                            **Double-Check for Proprietary or Branded Terms**  
                            If the term could refer to a specific branded medical test, reagent, or molecule, research the correct name in {target_lang} and use it explicitly instead of a generic translation.

                            **Contextual Understanding & Verification**  
                            Read the entire passage before translating individual terms to ensure correct medical interpretation.  
                            If necessary, restructure phrases to match the correct medical syntax in {target_lang} while preserving accuracy.

                            **Standard Terminology**  
                            Use official medical nomenclature from sources such as ICD, MedDRA, WHO, or equivalent regulatory bodies in {target_lang}.  
                            If a direct translation does not exist, use the closest medical equivalent or provide a brief clarifying phrase.

                            **Understandability in {target_lang}**  
                            If the {source_lang} text includes colloquial, abbreviated, or commonly-used phrasing that is recognized in conversation or transcription, translate it into the most **natural, clear, and understandable** equivalent in {target_lang} while preserving medical accuracy and context.  
                            Prefer terminology that would be readily understood by healthcare professionals or patients in a clinical setting in {target_lang}.
                            **SPECIFIC REQUIREMENTS:**
                            1. Preserve numerical values and measurements exactly
                            2. Handle Asian-specific:
                            - Thai honorific particles → natural equivalents if applies
                            - Chinese measure words → localized properly if applies
                            - Japanese contextual honorifics if applies
                            3. Mark uncertain terms with [Assumed:...]
                            4. Maintain original speaker labels (Speaker A/B), use always A, B, C instead of numbers to identify the Speakers.
                            5. **IMPORTANT** Do not add any other text or comments to the translation
                            6. **IMPORTANT** Be sure that ALL the original text is translated, DO NOT miss any part of the text.
                            7. **IMPORTANT** Do not add any other text or comments to the translation, no Title, No footer, nothing more than translation and text for translated text explication.
                            7. **IMPORTANT** Remove any title as **TRANSLATION TASK:**
                            
                            """
                            
                        }
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 4000,
                }

                response = requests.post(
                    DEEPSEEK_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=120
                )

                if response.status_code != 200:
                    raise Exception(f"DeepSeek API error: {response.text}")

                translated_text = response.json()['choices'][0]['message']['content']
                translated_chunks.append(translated_text)
                logging.info(f"Translated chunk {i} of {text_chunks_length}")

        return "\n".join(translated_chunks)

    except Exception as e:
        logging.error(f"DeepSeek translation error: {e}")
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


def load_excel_file(excel_file):
    """
    Loads the Excel file and validates required columns.
    Expected columns: 'Scope', 'Persona', 'Query'
    """
    df = pd.read_excel(excel_file, sheet_name=0)
    required_columns = ['Scope', 'Persona', 'Query']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"Excel file must contain columns: {required_columns}")
    return df

def process_query(query, text_to_analyze):
    """
    Uses ChatGPT (gpt-3.5-turbo) to check if the query is answered in the provided text.
    Returns the response or an error message.
    """
    prompt = (
        f"You are an expert in analyzing text responses. Given the following text:\n\n"
        f"'''{text_to_analyze}'''\n\n"
        f"Please check if the following query is answered in the text: '{query}'. "
        "If the query is answered, provide the relevant excerpt from the text; if not, reply with 'Not answered'."
    )
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        answer = completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error processing query '{query}': {e}")
        answer = f"Error: {str(e)}"
    return answer

def process_queries(df, text_to_analyze):
    """
    Processes each query in the DataFrame and returns a list of responses.
    """
    responses = []
    for _, row in df.iterrows():
        query = row['Query']
        answer = process_query(query, text_to_analyze)
        responses.append(answer)
    return responses


def create_sentiment_details_df(sentiment_results):
    """
    Creates a DataFrame from the detailed sentiment analysis.
    Each row corresponds to one analyzed sentence.
    Expected columns: ["Sentence", "Rating", "Confidence"]
    """
    details = sentiment_results.get("sentiment_analysis", [])
    df = pd.DataFrame(details, columns=["Sentence", "Rating", "Confidence"])
    return df

def create_sentiment_summary_df(details_df):
    """
    Creates a summary DataFrame that computes counts, percentages, and additional metrics
    from the detailed sentiment analysis.
    
    Classification:
      - Negative: rating is 1 or 2
      - Neutral: rating is 3
      - Positive: rating is 4 or 5

    It also extracts extreme values (highest/lowest rating and confidence) and provides an actionable insight.
    """
    # Ensure ratings are treated as strings and extract the numeric part.
    details_df["RatingStr"] = details_df["Rating"].apply(lambda x: str(x).strip())
    details_df["RatingDigit"] = details_df["RatingStr"].apply(lambda x: int(x.split()[0]) if x.split() else None)

    negative_count = details_df["RatingDigit"].apply(lambda x: x in [1, 2]).sum()
    neutral_count  = details_df["RatingDigit"].apply(lambda x: x == 3).sum()
    positive_count = details_df["RatingDigit"].apply(lambda x: x in [4, 5]).sum()
    total = len(details_df)

    avg_confidence = details_df["Confidence"].mean() if total > 0 else 0
    negative_pct = (negative_count / total) * 100 if total > 0 else 0
    neutral_pct  = (neutral_count  / total) * 100 if total > 0 else 0
    positive_pct = (positive_count / total) * 100 if total > 0 else 0

    # Determine overall sentiment based on counts.
    if positive_count > negative_count:
        overall_sentiment = "POSITIVE"
    elif negative_count > positive_count:
        overall_sentiment = "NEGATIVE"
    else:
        overall_sentiment = "NEUTRAL"

    # Identify extreme cases.
    highest_rating_row = details_df.loc[details_df["RatingDigit"].idxmax()] if total > 0 else None
    lowest_rating_row = details_df.loc[details_df["RatingDigit"].idxmin()] if total > 0 else None
    highest_conf_row = details_df.loc[details_df["Confidence"].idxmax()] if total > 0 else None
    lowest_conf_row = details_df.loc[details_df["Confidence"].idxmin()] if total > 0 else None

    rows = [
        ("Total Sentences", total),
        ("Negative Sentences", negative_count),
        ("Neutral Sentences", neutral_count),
        ("Positive Sentences", positive_count),
        ("Negative Percentage", f"{negative_pct:.1f}%"),
        ("Neutral Percentage", f"{neutral_pct:.1f}%"),
        ("Positive Percentage", f"{positive_pct:.1f}%"),
        ("Average Confidence", f"{avg_confidence:.1f}"),
        ("Overall Sentiment", overall_sentiment)
    ]

    if highest_rating_row is not None:
        rows.append(("Highest Rated Sentence", highest_rating_row["Sentence"]))
        rows.append(("Highest Rating", highest_rating_row["RatingStr"]))
    if lowest_rating_row is not None:
        rows.append(("Lowest Rated Sentence", lowest_rating_row["Sentence"]))
        rows.append(("Lowest Rating", lowest_rating_row["RatingStr"]))
    if highest_conf_row is not None:
        rows.append(("Highest Confidence Sentence", highest_conf_row["Sentence"]))
        rows.append(("Highest Confidence", f"{highest_conf_row['Confidence']:.1f}"))
    if lowest_conf_row is not None:
        rows.append(("Lowest Confidence Sentence", lowest_conf_row["Sentence"]))
        rows.append(("Lowest Confidence", f"{lowest_conf_row['Confidence']:.1f}"))
    
    # Create an actionable insight based on the overall sentiment.
    if overall_sentiment == "NEGATIVE":
        insight = "Investigate negative feedback trends and consider targeted improvements."
    elif overall_sentiment == "POSITIVE":
        insight = "Leverage positive feedback in your campaigns to boost your brand."
    else:
        insight = "Monitor neutral sentiment for opportunities to enhance customer engagement."
    rows.append(("Actionable Insight", insight))

    df_summary = pd.DataFrame(rows, columns=["Metric", "Value"])
    return df_summary

def generate_multi_sheet_excel(df_queries, df_sentiment_details, df_sentiment_summary):
    """
    Generates an Excel file with three sheets:
      - Sheet "Queries": queries with their ChatGPT responses.
      - Sheet "Sentiment Details": detailed sentiment analysis data.
      - Sheet "Sentiment Summary": general sentiment metrics and actionable insights.
    Returns a BytesIO object containing the Excel file.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_queries.to_excel(writer, sheet_name="Queries", index=False)
        df_sentiment_details.to_excel(writer, sheet_name="Sentiment Details", index=False)
        df_sentiment_summary.to_excel(writer, sheet_name="Sentiment Summary", index=False)
    output.seek(0)
    return output

def create_word_document(content: str, filename: str = "transcription.docx") -> str:
    """
    Generates a Word document (.docx) with the given content.

    Args:
        content (str): The text content to be added to the Word file.
        filename (str): The name of the Word document.

    Returns:
        str: The path of the saved Word document.
    """
    try:
        doc = Document()
        doc.add_paragraph(content)

        # Define the file path (modify if needed)
        file_path = f"/tmp/{filename}"

        # Save the document
        doc.save(file_path)

        return file_path

    except Exception as e:
        raise Exception(f"Error generating Word document: {e}")


def get_or_create_sheet(user_code):
    """
    Verifica se il foglio Google Sheets esiste, altrimenti lo crea con la struttura necessaria.
    """
    sheet_name = f"{user_code}_usage_audio_translate"

    print(f"DEBUG: Verifica foglio con nome: {sheet_name}")

    try:
        sheet = google_client.open(sheet_name).sheet1  # Prova ad aprire il foglio esistente
        print(f"DEBUG: Il foglio {sheet_name} esiste già.")
    except gspread.exceptions.SpreadsheetNotFound:
        try:
            print(f"DEBUG: Il foglio {sheet_name} non esiste. Creazione in corso...")
            sheet = google_client.create(sheet_name).sheet1
            sheet.append_row(["Data e Ora", "Nome File", "Durata (minuti)", "Costo Unitario (€)", "Costo Totale (€)"])
            print(f"DEBUG: Creato nuovo foglio: {sheet_name}")
        except Exception as e:
            print(f"DEBUG: Errore durante la creazione del foglio: {e}")
            return None

    return sheet



def log_audio_processing(user_code, filename, duration):
    """
    Registra la trascrizione e la durata dell'audio nel Google Sheet.
    """
    try:
        sheet = get_or_create_sheet(user_code)  # Assicura che il foglio esista

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ensure duration is a float
        try:
            duration = float(duration)
        except ValueError as ve:
            logging.error(f"ERROR: Invalid duration value: {duration} - {ve}")
            return None  # Avoid raising an error

        cost_per_minute = RATE_PER_MINUTE
        total_cost = duration * cost_per_minute

        # Debug: Print values before inserting into Google Sheets
        logging.info(f"DEBUG: Logging to Google Sheets -> {now}, {filename}, {duration}, {cost_per_minute}, {total_cost}")

        sheet.append_row([now, filename, duration, f"{cost_per_minute:.2f}", f"{total_cost:.2f}", 'YES'])
        logging.info(f"Dati salvati su Google Sheet: {filename} - {duration} min - €{total_cost:.2f}")

        return True  # Indicate success

    except Exception as e:
        logging.error(f"Errore durante il salvataggio dei dati su Google Sheet: {e}")
        return None  # Don't raise the error, just return None



def get_usage_data(user_code, columns=None):
    """
    Fetches usage data from Google Sheets for a given user.
    Filters records where 'Billed' is 'YES'.
    Extracts only the specified columns if provided.

    :param user_code: The user identifier for the sheet name.
    :param columns: List of column names to extract (optional).
    :return: List of dictionaries with the requested columns.
    """
    # Get the instance of the Spreadsheet
    sheet = google_client.open(f'{user_code}_usage_audio_translate')

    # Get the first sheet of the Spreadsheet
    worksheet = sheet.get_worksheet(0)

    # Get all records of the data
    records = worksheet.get_all_records()

    # Filter by 'Billed' === 'YES'
    records = [record for record in records if record.get('Billed') == 'YES']

    # Extract only specified columns if provided
    if columns:
        records = [{col: record[col] for col in columns if col in record} for record in records]

    return records
