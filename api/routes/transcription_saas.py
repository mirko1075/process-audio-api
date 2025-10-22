"""
Updated transcription routes with dual authentication support.
Supports both JWT (web frontend) and API keys (Make.com, external integrations).
"""

from flask import Blueprint, request, jsonify, g
import logging

from utils.auth_middleware import dual_auth_required, require_user_provider_config, increment_user_usage, check_user_limits
from services.user_provider import UserProviderService
from services.transcription_saas import DeepgramService, WhisperService
from utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

transcription_bp = Blueprint('transcription', __name__, url_prefix='/transcriptions')


@transcription_bp.route('/deepgram', methods=['POST'])
@dual_auth_required
@require_user_provider_config('deepgram')
def transcribe_deepgram():
    """
    Transcribe audio using user's Deepgram API key.
    Supports both JWT and API key authentication.
    """
    try:
        # Check user limits
        if not check_user_limits():
            return jsonify({
                'error': 'Usage limit exceeded for your plan. Please upgrade or wait for the next billing cycle.'
            }), 429
        
        # Get uploaded file
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Get parameters
        language = request.form.get('language', 'en')
        model = request.form.get('model', 'nova-2')
        diarize = request.form.get('diarize', 'false').lower() == 'true'
        punctuate = request.form.get('punctuate', 'true').lower() == 'true'
        paragraphs = request.form.get('paragraphs', 'false').lower() == 'true'
        
        # Get user's Deepgram API key from provider configuration
        provider_service = UserProviderService()
        api_key = provider_service.require_user_api_key('deepgram')
        
        # Initialize Deepgram service
        deepgram_service = DeepgramService()
        
        # Perform transcription
        result = deepgram_service.transcribe(
            audio_file=audio_file,
            language=language,
            model=model,
            diarize=diarize,
            punctuate=punctuate,
            paragraphs=paragraphs
        )
        
        # Calculate costs (example pricing - adjust as needed)
        audio_duration_minutes = result.get('duration_seconds', 0) / 60
        cost_per_minute = 0.0048  # Deepgram pricing example
        total_cost = audio_duration_minutes * cost_per_minute
        
        # Update usage statistics
        provider_service.update_usage_stats(
            provider_name='deepgram',
            cost_usd=total_cost,
            audio_minutes=audio_duration_minutes
        )
        
        # Update user's monthly usage
        increment_user_usage(api_calls=1, audio_minutes=audio_duration_minutes)
        
        logger.info(f"Deepgram transcription completed for user {g.current_user.email} "
                   f"via {g.auth_method} authentication")
        
        return jsonify(result), 200
        
    except ConfigurationError as e:
        logger.warning(f"Configuration error for user {g.current_user.email}: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Deepgram transcription failed for user {g.current_user.email}: {e}")
        return jsonify({'error': 'Transcription failed'}), 500


@transcription_bp.route('/whisper', methods=['POST'])
@dual_auth_required  
@require_user_provider_config('openai')
def transcribe_whisper():
    """
    Transcribe audio using user's OpenAI Whisper API key.
    Supports both JWT and API key authentication.
    """
    try:
        # Check user limits
        if not check_user_limits():
            return jsonify({
                'error': 'Usage limit exceeded for your plan. Please upgrade or wait for the next billing cycle.'
            }), 429
        
        # Get uploaded file
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Get parameters
        language = request.form.get('language', None)
        
        # Get user's OpenAI API key from provider configuration
        provider_service = UserProviderService()
        api_key = provider_service.require_user_api_key('openai')
        
        # Initialize Whisper service
        whisper_service = WhisperService()
        
        # Perform transcription
        result = whisper_service.transcribe(
            audio_file=audio_file,
            language=language
        )
        
        # Calculate costs (example pricing - adjust as needed)
        audio_duration_minutes = result.get('duration', 0) / 60
        cost_per_minute = 0.006  # OpenAI Whisper pricing
        total_cost = audio_duration_minutes * cost_per_minute
        
        # Update usage statistics
        provider_service.update_usage_stats(
            provider_name='openai',
            cost_usd=total_cost,
            audio_minutes=audio_duration_minutes
        )
        
        # Update user's monthly usage
        increment_user_usage(api_calls=1, audio_minutes=audio_duration_minutes)
        
        logger.info(f"Whisper transcription completed for user {g.current_user.email} "
                   f"via {g.auth_method} authentication")
        
        return jsonify(result), 200
        
    except ConfigurationError as e:
        logger.warning(f"Configuration error for user {g.current_user.email}: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Whisper transcription failed for user {g.current_user.email}: {e}")
        return jsonify({'error': 'Transcription failed'}), 500


@transcription_bp.route('/test-auth', methods=['GET'])
@dual_auth_required
def test_authentication():
    """
    Test endpoint to verify authentication is working.
    Shows which authentication method was used and user info.
    """
    user = g.current_user
    auth_method = g.auth_method
    
    provider_service = UserProviderService()
    configured_providers = provider_service.get_user_configured_providers()
    
    return jsonify({
        'message': 'Authentication successful!',
        'user': {
            'id': user.id,
            'email': user.email,
            'plan': user.plan,
            'is_active': user.is_active
        },
        'authentication': {
            'method': auth_method,
            'description': 'JWT Bearer token' if auth_method == 'jwt' else 'API key'
        },
        'providers_configured': configured_providers,
        'usage_stats': provider_service.get_user_usage_summary()
    }), 200


@transcription_bp.route('/providers/test/<provider_name>', methods=['POST'])
@dual_auth_required
def test_provider_configuration(provider_name):
    """
    Test if a provider is properly configured for the current user.
    """
    try:
        provider_service = UserProviderService()
        result = provider_service.test_provider_config(provider_name)
        
        return jsonify({
            'provider': provider_name,
            'test_result': result,
            'user': g.current_user.email,
            'auth_method': g.auth_method
        }), 200
        
    except Exception as e:
        logger.error(f"Error testing provider {provider_name} for user {g.current_user.email}: {e}")
        return jsonify({
            'error': f'Failed to test {provider_name} configuration',
            'provider': provider_name
        }), 500