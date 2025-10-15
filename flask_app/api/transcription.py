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


@bp.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {error.description}")
    return jsonify({'error': error.description}), 400