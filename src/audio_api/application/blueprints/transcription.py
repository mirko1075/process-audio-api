import os
import time
import logging
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, g
from distutils.util import strtobool

from ..auth import require_api_key
from audio_api.domain.process_audio import (
    transcribe_with_deepgram,
    transcript_with_whisper_large_files,
    transcribe_audio_openai,
    translate_text_with_openai,
    translate_text_google,
    upload_to_gcs,
    delete_from_gcs,
    convert_to_wav,
    get_audio_duration_from_form_file,
)
import assemblyai as aai

transcription_bp = Blueprint('transcription', __name__)

@transcription_bp.route('/transcribe_and_translate', methods=['POST'])
@require_api_key
def transcribe_and_translate():
    try:
        audio_file = request.files.get('audio')
        translate = strtobool(request.form.get('translate', 'false'))
        transcript_model = request.form.get('transcript_model', 'deepgram')
        translation_model = request.form.get('translation_model', 'google')
        language = request.form.get('language', 'en')
        target_language = request.form.get('target_language', 'en')

        if not audio_file:
            return jsonify({'error': 'No file uploaded'}), 400
        if translate and translation_model not in ['google', 'openai']:
            return jsonify({'error': 'Invalid translation model'}), 400

        resp = transcribe_with_deepgram(audio_file, language, transcript_model)
        formatted = resp.get('formatted_transcript_array')
        transcript = resp.get('transcript')
        translated_text = None
        if translate:
            if translation_model == 'google':
                translated_text = translate_text_google(transcript, target_language)
            else:
                translated_text = translate_text_with_openai(transcript, language, target_language)

        return jsonify({
            'formatted_transcript_array': formatted,
            'transcript': transcript,
            'translated_text': translated_text,
        })
    except Exception as e:
        logging.error(f"Error in transcribe_and_translate: {e}")
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/transcript-with-whisper', methods=['POST'])
@require_api_key
def transcript_with_whisper():
    audio_file = request.files.get('audio')
    language = request.form.get('language', 'en')
    if not audio_file:
        return jsonify({'error': 'No file uploaded'}), 400

    input_path = os.path.join('/tmp', audio_file.filename)
    wav_path = os.path.join('/tmp', f"{os.path.splitext(audio_file.filename)[0]}.wav")
    temp_dir = '/tmp/temp'
    try:
        audio_file.save(input_path)
        if not input_path.lower().endswith('.wav'):
            convert_to_wav(input_path, wav_path)
        else:
            wav_path = input_path

        transcription = transcript_with_whisper_large_files(wav_path, temp_dir, language)
        if not transcription or not isinstance(transcription, str):
            return jsonify({'error': 'Transcription failed'}), 500

        return jsonify({'message': 'Processing complete', 'transcription': transcription})
    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(wav_path) and wav_path != input_path:
            os.remove(wav_path)
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))

@transcription_bp.route('/transcribe-with-deepgram-whisper', methods=['POST'])
@require_api_key
def transcribe_with_deepgram_whisper():
    try:
        audio_file = request.files.get('audio')
        language = request.form.get('language', 'en')
        if not audio_file:
            return jsonify({'error': 'No file uploaded'}), 400

        resp = transcribe_with_deepgram(audio_file, language)
        formatted = resp.get('formatted_transcript_array')
        transcript = resp.get('transcript')
        return jsonify({'formatted_transcript_array': formatted, 'transcript': transcript})
    except Exception as e:
        logging.error(f"Error in transcribe_with_deepgram_whisper: {e}")
        return jsonify({'error': str(e)}), 500

@transcription_bp.route('/transcribe-with-assemblyai', methods=['POST'])
@require_api_key
def transcribe_with_assemblyai():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio_file = request.files.get('audio')
    is_dev = request.form.get('isDev')
    source_language = request.form.get('sourceLanguage')
    target_language = request.form.get('targetLanguage')
    file_name = request.form.get('fileName')
    duration = request.form.get('duration')
    drive_id = request.form.get('driveId')
    group_id = request.form.get('groupId')
    file_id = request.form.get('fileId')
    folder_id = request.form.get('folderId')
    project_name = request.form.get('projectName')
    required = [source_language, target_language, file_name, duration, drive_id, group_id, file_id, folder_id, project_name]
    if not all(required):
        return jsonify({'error': 'Missing required form parameters'}), 400

    temp_path = f"temp_{audio_file.filename}"
    audio_file.save(temp_path)
    # Select model based on language
    if source_language in [
        'en', 'en_us', 'en_uk', 'es', 'fr', 'de', 'it', 'pt', 'nl',
        'hi', 'ja', 'zh', 'fi', 'ko', 'pl', 'ru', 'tr', 'uk', 'vi'
    ]:
        model = aai.SpeechModel.best
        speaker_labels = True
    else:
        model = aai.SpeechModel.nano
        speaker_labels = False

    try:
        config = aai.TranscriptionConfig(
            language_code=source_language,
            speech_model=model,
            speaker_labels=speaker_labels
        )
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_path, config)
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({'error': transcript.error}), 500

        if speaker_labels:
            formatted = ''.join(
                f"speaker{utt.speaker}: {utt.text}\n" for utt in transcript.utterances
            )
        else:
            formatted = transcript.text

        url = (
            'https://hook.eu2.make.com/1qn49rif17gctwp53zee3xbjb6aqvbko'
            if is_dev == 'true' else
            'https://hook.eu2.make.com/qcc3jfwa2stoz8xqzjvap6581hqyl2oy'
        )
        resp = requests.post(
            url,
            data={
                'transcription': formatted,
                'fileName': file_name,
                'duration': duration,
                'driveId': drive_id,
                'groupId': group_id,
                'folderId': folder_id,
                'fileId': file_id,
                'projectName': project_name,
                'sourceLanguage': source_language,
            }
        )
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to send request to Make'}), 500
        return jsonify({'message': 'Request sent to Make'}), 200
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)