"""Transcription API blueprint - Flask best practices style."""
import logging
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from flask_app.services.transcription import DeepgramService, WhisperService, AssemblyAIService
from utils.auth import require_api_key
from utils.exceptions import TranscriptionError


bp = Blueprint('transcription', __name__)
logger = logging.getLogger(__name__)


@bp.route('/deepgram', methods=['POST'])
@require_api_key
def deepgram_transcription():
    """Transcribe audio using Deepgram Nova-2 model.
    
    Accepts multipart/form-data with:
    - audio: Audio file
    - language: Language code (optional, default: 'en')
    - model: Deepgram model (optional, default: 'nova-2')
    """
    logger.info("Deepgram transcription request received")
    
    # Validate audio file
    if 'audio' not in request.files:
        raise BadRequest('No audio file provided')
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        raise BadRequest('No audio file selected')
    
    # Get optional parameters
    language = request.form.get('language', 'en')
    model = request.form.get('model', 'nova-2')
    
    logger.info(f"Processing Deepgram transcription: language={language}, model={model}")
    
    try:
        # Use service to handle transcription
        service = DeepgramService()
        result = service.transcribe(audio_file, language=language, model=model)
        
        logger.info("Deepgram transcription completed successfully")
        return jsonify(result)
        
    except TranscriptionError as e:
        logger.error(f"Deepgram transcription error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in Deepgram transcription: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/whisper', methods=['POST'])
@require_api_key
def whisper_transcription():
    """Transcribe audio using OpenAI Whisper with automatic chunking.
    
    Accepts multipart/form-data with:
    - audio: Audio file
    - language: Language code (optional, default: 'en')
    
    Automatically handles large files by chunking them into smaller segments.
    """
    logger.info("Whisper transcription request received")
    
    # Validate audio file
    if 'audio' not in request.files:
        raise BadRequest('No audio file provided')
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        raise BadRequest('No audio file selected')
    
    # Get optional parameters
    language = request.form.get('language', 'en')
    
    logger.info(f"Processing Whisper transcription: language={language}")
    
    try:
        # Use service to handle transcription with automatic chunking
        service = WhisperService()
        result = service.transcribe(audio_file, language=language)
        
        logger.info("Whisper transcription completed successfully")
        
        # Log chunking info if applicable
        if result.get('processing_method') == 'chunked':
            logger.info(f"Processed {result.get('total_chunks')} chunks")
        
        return jsonify(result)
        
    except TranscriptionError as e:
        logger.error(f"Whisper transcription error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in Whisper transcription: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/assemblyai', methods=['POST'])
@require_api_key
def assemblyai_transcription():
    """Transcribe audio using AssemblyAI.
    
    Accepts multipart/form-data with:
    - audio: Audio file
    - language: Language code (optional, default: 'en')
    """
    logger.info("AssemblyAI transcription request received")
    
    # Validate audio file
    if 'audio' not in request.files:
        raise BadRequest('No audio file provided')
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        raise BadRequest('No audio file selected')
    
    # Get optional parameters
    language = request.form.get('language', 'en')
    
    logger.info(f"Processing AssemblyAI transcription: language={language}")
    
    try:
        # Use service to handle transcription
        service = AssemblyAIService()
        result = service.transcribe(audio_file, language=language)
        
        logger.info("AssemblyAI transcription completed successfully")
        return jsonify(result)
        
    except TranscriptionError as e:
        logger.error(f"AssemblyAI transcription error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in AssemblyAI transcription: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Error handlers specific to this blueprint
@bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large errors."""
    logger.warning("File too large error - this should be handled by chunking")
    return jsonify({
        'error': 'File too large. Note: Whisper endpoint automatically handles large files with chunking.'
    }), 413


@bp.route('/transcribe-and-translate', methods=['POST'])
@require_api_key
def transcribe_and_translate():
    """Combined transcription and translation endpoint.
    
    Accepts multipart/form-data with:
    - audio: Audio file
    - translate: Whether to translate (true/false, optional, default: false)
    - transcript_model: Transcription model ('deepgram', 'whisper', optional, default: 'deepgram')
    - translation_model: Translation model ('google', 'openai', optional, default: 'google')
    - language: Source language code (optional, default: 'en')
    - target_language: Target language code (optional, default: 'en')
    """
    logger.info("Combined transcribe and translate request received")
    
    # Validate audio file
    if 'audio' not in request.files:
        raise BadRequest('No audio file provided')
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        raise BadRequest('No audio file selected')
    
    # Get parameters
    translate = request.form.get('translate', 'false').lower() == 'true'
    transcript_model = request.form.get('transcript_model', 'deepgram')
    translation_model = request.form.get('translation_model', 'google')
    language = request.form.get('language', 'en')
    target_language = request.form.get('target_language', 'en')
    
    # Validate translation model
    if translate and translation_model not in ['google', 'openai']:
        raise BadRequest('Invalid translation model. Must be "google" or "openai"')
    
    logger.info(f"Processing combined request: transcript_model={transcript_model}, translate={translate}")
    
    try:
        # Step 1: Transcribe audio using specified model
        if transcript_model == 'whisper':
            service = WhisperService()
            transcription_result = service.transcribe(audio_file, language=language)
        elif transcript_model == 'assemblyai':
            service = AssemblyAIService()
            transcription_result = service.transcribe(audio_file, language=language)
        else:  # Default to deepgram
            service = DeepgramService()
            transcription_result = service.transcribe(audio_file, language=language)
        
        # Extract transcript text
        transcript = transcription_result.get('transcript', '')
        formatted_transcript_array = transcription_result.get('formatted_transcript_array', [])
        
        # Step 2: Translate if requested
        translated_text = None
        if translate and transcript:
            logger.info(f"Translating transcript using {translation_model}")
            
            if translation_model == 'openai':
                from flask_app.services.translation import OpenAITranslationService
                translation_service = OpenAITranslationService()
                translation_result = translation_service.translate(transcript, language, target_language)
                translated_text = translation_result.get('translated_text')
            else:  # Default to google
                from flask_app.services.translation import GoogleTranslationService
                translation_service = GoogleTranslationService()
                translation_result = translation_service.translate(transcript, target_language)
                translated_text = translation_result.get('translated_text')
        
        # Prepare response
        result = {
            'formatted_transcript_array': formatted_transcript_array,
            'transcript': transcript,
            'translated_text': translated_text
        }
        
        logger.info("Combined transcribe and translate completed successfully")
        return jsonify(result)
        
    except TranscriptionError as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in combined transcribe and translate: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {error.description}")
    return jsonify({'error': error.description}), 400