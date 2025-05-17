import logging
import requests
from flask import Blueprint, request, jsonify

from ..auth import require_api_key
from audio_api.domain.process_audio import translate_text_with_openai, translate_text_with_deepseek

translation_bp = Blueprint('translation', __name__)

@translation_bp.route('/translate-with-openai', methods=['POST'])
@require_api_key
def translate_with_openai():
    try:
        text = request.form.get('text')
        is_dev = request.form.get('isDev')
        is_local = request.form.get('isLocal')
        source_language = request.form.get('sourceLanguage')
        target_language = request.form.get('targetLanguage')
        file_name = request.form.get('fileName')
        duration = request.form.get('duration')
        drive_id = request.form.get('driveId')
        group_id = request.form.get('groupId')
        file_id = request.form.get('fileId')
        folder_id = request.form.get('folderId')
        project_name = request.form.get('projectName')
        required = [text, source_language, target_language, file_name, duration, drive_id, group_id, file_id, folder_id, project_name]
        if not all(required):
            return jsonify({'error': 'Missing required form parameters'}), 400

        translated_text = translate_text_with_openai(text, source_language, target_language)
        if is_local == 'true':
            return jsonify({'translated_text': translated_text})

        url = (
            'https://hook.eu2.make.com/57p7fp7akfp3wx2xt2rfr993tgpx1u82'
            if is_local == 'true' else
            'https://hook.eu2.make.com/xjxlm9ehhdn16mhtfnp77sxpgidvagqe'
        )
        if is_dev == 'true':
            url = 'https://hook.eu2.make.com/62p3xl6a7nnr14y89i6av1bxapyvxpxn'

        resp = requests.post(
            url,
            data={
                'translation': translated_text,
                'transcription': text,
                'fileName': file_name,
                'duration': duration,
                'driveId': drive_id,
                'groupId': group_id,
                'folderId': folder_id,
                'fileId': file_id,
                'projectName': project_name
            }
        )
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to send request to Make'}), 500

        return jsonify({'message': 'Request sent to Make'}), 200
    except Exception as e:
        logging.error(f"Error in translate_with_openai endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@translation_bp.route('/translate-with-deepseek', methods=['POST'])
@require_api_key
def translate_with_deepseek():
    try:
        text = request.form.get('text')
        is_dev = request.form.get('isDev')
        is_local = request.form.get('isLocal')
        source_language = request.form.get('sourceLanguage')
        target_language = request.form.get('targetLanguage')
        file_name = request.form.get('fileName')
        duration = request.form.get('duration')
        drive_id = request.form.get('driveId')
        group_id = request.form.get('groupId')
        file_id = request.form.get('fileId')
        folder_id = request.form.get('folderId')
        project_name = request.form.get('projectName')
        required = [text, source_language, target_language, file_name, duration, drive_id, group_id, file_id, folder_id, project_name]
        if not all(required):
            return jsonify({'error': 'Missing required form parameters'}), 400

        translated_text = translate_text_with_deepseek(text, source_language, target_language)
        if is_local == 'true':
            return jsonify({'translated_text': translated_text})

        url = (
            'https://hook.eu2.make.com/xjxlm9ehhdn16mhtfnp77sxpgidvagqe'
        )
        if is_dev == 'true':
            url = 'https://hook.eu2.make.com/62p3xl6a7nnr14y89i6av1bxapyvxpxn'

        resp = requests.post(
            url,
            data={
                'translation': translated_text,
                'transcription': text,
                'fileName': file_name,
                'duration': duration,
                'driveId': drive_id,
                'groupId': group_id,
                'folderId': folder_id,
                'fileId': file_id,
                'projectName': project_name
            }
        )
        if resp.status_code != 200:
            return jsonify({'error': 'Failed to send request to Make'}), 500

        return jsonify({'message': 'Request sent to Make'}), 200
    except Exception as e:
        logging.error(f"Error in translate_with_deepseek endpoint: {e}")
        return jsonify({'error': str(e)}), 500