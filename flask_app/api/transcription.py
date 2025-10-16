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
    """Transcribe audio using Deepgram Nova-2 model with enhanced options.
    
    Accepts multipart/form-data with:
    - audio: Audio file (required)
    - language: Language code (optional, default: 'en')
    - model: Deepgram model (optional, default: 'nova-2')
    - diarize: Enable speaker diarization (optional, default: 'false')
    - punctuate: Enable smart punctuation (optional, default: 'true')
    - paragraphs: Enable paragraph detection (optional, default: 'false')
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
    diarize = request.form.get('diarize', 'false').lower() == 'true'
    punctuate = request.form.get('punctuate', 'true').lower() == 'true'
    paragraphs = request.form.get('paragraphs', 'false').lower() == 'true'
    
    logger.info(f"Processing Deepgram transcription: language={language}, model={model}, diarize={diarize}")
    
    try:
        # Use service to handle transcription with enhanced options
        service = DeepgramService()
        result = service.transcribe(
            audio_file, 
            language=language, 
            model=model,
            diarize=diarize,
            punctuate=punctuate,
            paragraphs=paragraphs
        )
        
        # Add processing metadata
        processing_info = {
            "service": "deepgram",
            "model_used": model,
            "language_requested": language,
            "diarization_enabled": diarize,
            "paragraphs_enabled": paragraphs
        }
        
        # Merge processing info with result
        final_result = {**result, "processing_info": processing_info}
        
        logger.info(f"Deepgram transcription completed successfully (speakers: {result.get('diarization', {}).get('speakers_detected', 'N/A')})")
        return jsonify(final_result)
        
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


@bp.route('/video', methods=['POST'])
@require_api_key
def video_transcription():
    """Transcribe video from URL or uploaded file using Whisper.
    
    Accepts either:
    1. JSON with video_url for processing YouTube/web videos
    2. multipart/form-data with video file upload
    
    Optional parameters:
    - language: Language code (optional, auto-detect if not provided)
    - model_size: Whisper model size (tiny, base, small, medium, large, default: base)
    """
    logger.info("Video transcription request received")
    
    try:
        from flask_app.services.video_transcription import VideoTranscriptionService
        service = VideoTranscriptionService()
        
        # Check if request contains video URL or file upload
        if request.content_type and 'application/json' in request.content_type:
            # Process video URL
            data = request.get_json()
            if not data or 'video_url' not in data:
                raise BadRequest('video_url is required for JSON requests')
            
            video_url = data['video_url']
            language = data.get('language')  # None for auto-detect
            model_size = data.get('model_size', 'base')
            
            logger.info(f"Processing video URL: {video_url}, language={language}, model={model_size}")
            result = service.transcribe_from_url(video_url, language=language, model_size=model_size)
            
        elif 'video' in request.files:
            # Process uploaded video file
            video_file = request.files['video']
            if video_file.filename == '':
                raise BadRequest('No video file selected')
            
            language = request.form.get('language')  # None for auto-detect
            model_size = request.form.get('model_size', 'base')
            
            logger.info(f"Processing uploaded video: {video_file.filename}, language={language}, model={model_size}")
            result = service.transcribe_from_file(video_file, language=language, model_size=model_size)
            
        else:
            raise BadRequest('Either video_url (JSON) or video file (multipart) is required')
        
        logger.info("Video transcription completed successfully")
        return jsonify(result)
        
    except BadRequest as e:
        logger.error(f"Bad request in video transcription: {e.description}")
        return jsonify({'error': e.description}), 400
    except TranscriptionError as e:
        logger.error(f"Video transcription error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in video transcription: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {error.description}")
    return jsonify({'error': error.description}), 400