"""Translation API blueprint - Flask best practices style."""
import logging
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

from flask_app.services.translation import OpenAITranslationService, GoogleTranslationService
from utils.auth import require_api_key
from utils.exceptions import TranslationError


bp = Blueprint('translation', __name__)
logger = logging.getLogger(__name__)


@bp.route('/openai', methods=['POST'])
@require_api_key
def openai_translation():
    """Translate text using OpenAI GPT with automatic text chunking.
    
    Accepts JSON with:
    - text: Text to translate
    - source_language: Source language code (optional, default: 'auto')
    - target_language: Target language code (required)
    
    Automatically handles long texts by chunking them into smaller segments.
    """
    logger.info("OpenAI translation request received")
    
    # Validate JSON request
    if not request.is_json:
        raise BadRequest('Request must be JSON')
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        raise BadRequest('Missing required field: text')
    if 'target_language' not in data:
        raise BadRequest('Missing required field: target_language')
    
    text = data['text']
    source_language = data.get('source_language', 'auto')
    target_language = data['target_language']
    
    # Validate text is not empty
    if not text.strip():
        raise BadRequest('Text cannot be empty')
    
    logger.info(f"Processing OpenAI translation: {source_language} -> {target_language} (text length: {len(text)})")
    
    try:
        # Use service to handle translation with automatic chunking
        service = OpenAITranslationService()
        result = service.translate(text, source_language, target_language)
        
        logger.info("OpenAI translation completed successfully")
        
        # Log chunking info if applicable
        if 'chunks_processed' in result:
            logger.info(f"Processed {result['chunks_processed']} text chunks")
        
        return jsonify(result)
        
    except TranslationError as e:
        logger.error(f"OpenAI translation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in OpenAI translation: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/google', methods=['POST'])
@require_api_key
def google_translation():
    """Translate text using Google Cloud Translation API.
    
    Accepts JSON with:
    - text: Text to translate
    - target_language: Target language code (required)
    
    Note: Google Cloud Translation API must be enabled for your project.
    """
    logger.info("Google translation request received")
    
    # Validate JSON request
    if not request.is_json:
        raise BadRequest('Request must be JSON')
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        raise BadRequest('Missing required field: text')
    if 'target_language' not in data:
        raise BadRequest('Missing required field: target_language')
    
    text = data['text']
    target_language = data['target_language']
    
    # Validate text is not empty
    if not text.strip():
        raise BadRequest('Text cannot be empty')
    
    logger.info(f"Processing Google translation to {target_language} (text length: {len(text)})")
    
    try:
        # Use service to handle translation
        service = GoogleTranslationService()
        result = service.translate(text, target_language)
        
        logger.info("Google translation completed successfully")
        return jsonify(result)
        
    except TranslationError as e:
        logger.error(f"Google translation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in Google translation: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Error handlers specific to this blueprint
@bp.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {error.description}")
    return jsonify({'error': error.description}), 400