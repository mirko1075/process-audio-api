"""Authentication system with JWT and API Key support."""

from functools import wraps
from flask import request, jsonify, g, current_app
import logging

logger = logging.getLogger(__name__)

def require_auth(allow_api_key=True, allow_jwt=True):
    """
    Flexible authentication decorator that supports both JWT and API Key authentication.
    
    Args:
        allow_api_key: Allow API key authentication (includes legacy support)
        allow_jwt: Allow JWT authentication
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = None
            auth_method = None
            auth_error = None
            
            # Try JWT first (Bearer token)
            if allow_jwt:
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    try:
                        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
                        from models.user import User
                        
                        verify_jwt_in_request()
                        user_id = get_jwt_identity()
                        user = User.query.get(user_id)
                        if user and user.is_active:
                            auth_method = 'jwt'
                            logger.info(f"JWT auth successful for user {user.id}")
                        elif user and not user.is_active:
                            auth_error = {'reason': 'user_inactive', 'message': 'User account is inactive'}
                    except Exception as e:
                        logger.warning(f"JWT verification failed: {str(e)}")
                        # Distinguish between different JWT errors
                        error_str = str(e).lower()
                        if 'expired' in error_str or 'signature has expired' in error_str:
                            auth_error = {'reason': 'token_expired', 'message': 'JWT token has expired'}
                        elif 'invalid' in error_str or 'signature' in error_str:
                            auth_error = {'reason': 'token_invalid', 'message': 'JWT token is invalid'}
                        else:
                            auth_error = {'reason': 'token_error', 'message': 'JWT token verification failed'}
            
            # Try API Key if JWT failed
            if not user and allow_api_key:
                api_key = request.headers.get('x-api-key')
                if api_key:
                    # Try new user API keys first
                    from models.user import ApiKey
                    user = ApiKey.verify_key(api_key)
                    if user:
                        auth_method = 'api_key'
                        logger.info(f"API key auth successful for user {user.id}")
                    else:
                        # Legacy fallback (static API key)
                        from utils.config import get_app_config
                        if api_key == get_app_config().api_key:
                            # Create temporary "system" user for legacy support
                            user = type('LegacyUser', (), {
                                'id': 0,
                                'email': 'system@legacy.com',
                                'plan': 'legacy',
                                'is_active': True,
                                'api_calls_month': 0,
                                'audio_minutes_month': 0.0
                            })()
                            auth_method = 'legacy'
                            logger.info("Legacy API key authentication")
                        else:
                            logger.warning(f"Invalid API key attempted")
                            auth_error = {'reason': 'api_key_invalid', 'message': 'Invalid API key'}
                elif allow_api_key and not allow_jwt:
                    # API key is required but missing
                    auth_error = {'reason': 'api_key_missing', 'message': 'API key is required'}
            
            # Handle authentication failure with specific error
            if not user:
                if not auth_error:
                    # No credentials provided at all
                    if request.headers.get('Authorization') or request.headers.get('x-api-key'):
                        auth_error = {'reason': 'auth_failed', 'message': 'Authentication failed'}
                    else:
                        auth_error = {'reason': 'credentials_missing', 'message': 'Authentication credentials required'}
                
                return jsonify({
                    'error': 'Authentication required',
                    'details': auth_error
                }), 401
            
            # Set user context for the request
            g.current_user = user
            g.auth_method = auth_method
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Legacy decorator for backward compatibility
def require_api_key(f):
    """Legacy API key decorator - now supports both old and new API keys."""
    return require_auth(allow_api_key=True, allow_jwt=False)(f)

def require_jwt(f):
    """Require JWT authentication only."""
    return require_auth(allow_api_key=False, allow_jwt=True)(f)

def require_any_auth(f):
    """Allow both JWT and API key authentication."""
    return require_auth(allow_api_key=True, allow_jwt=True)(f)

def log_usage(service, endpoint, **kwargs):
    """Log API usage for billing purposes."""
    try:
        from models.user import UsageLog
        from models import db
        
        if hasattr(g, 'current_user') and g.current_user.id != 0:  # Skip legacy user
            usage_log = UsageLog(
                user_id=g.current_user.id,
                service=service,
                endpoint=endpoint,
                audio_duration_seconds=kwargs.get('audio_duration'),
                tokens_used=kwargs.get('tokens_used'),
                characters_processed=kwargs.get('characters_processed'),
                cost_usd=kwargs.get('cost_usd'),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            
            db.session.add(usage_log)
            db.session.commit()
            
            logger.info(f"Usage logged for user {g.current_user.id}: {service}/{endpoint}")
    except Exception as e:
        logger.error(f"Failed to log usage: {str(e)}")
