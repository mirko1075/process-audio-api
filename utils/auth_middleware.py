"""
Authentication middleware for dual authentication support.
Supports both JWT tokens (web frontend) and API keys (Make.com, external integrations).
"""

from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
import logging

from models.auth import User, ApiKey

logger = logging.getLogger(__name__)


def dual_auth_required(f):
    """
    Middleware for transcription/translation endpoints that supports both:
    1. JWT Bearer tokens (for web frontend users)
    2. API keys (for Make.com and external integrations)
    
    Sets g.current_user to the authenticated user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None
        auth_method = None
        
        # Try JWT authentication first
        try:
            # Check for Bearer token
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                user = User.query.filter_by(id=user_id, is_active=True).first()
                if user:
                    auth_method = 'jwt'
                    logger.info(f"JWT authentication successful for user {user.email}")
        except Exception as e:
            logger.debug(f"JWT authentication failed: {e}")
        
        # If JWT failed, try API key authentication
        if not user:
            try:
                # Check for x-api-key header
                api_key = request.headers.get('x-api-key') or request.headers.get('X-API-Key')
                if api_key:
                    user = ApiKey.authenticate(api_key)
                    if user:
                        auth_method = 'api_key'
                        logger.info(f"API key authentication successful for user {user.email}")
            except Exception as e:
                logger.debug(f"API key authentication failed: {e}")
        
        # Check if user is authenticated
        if not user:
            logger.warning(f"Authentication failed for {request.endpoint} from {request.remote_addr}")
            return jsonify({
                'error': 'Authentication required. Provide either a valid JWT Bearer token or API key.'
            }), 401
        
        # Check if user account is active
        if not user.is_active:
            logger.warning(f"Inactive user {user.email} attempted access")
            return jsonify({
                'error': 'User account is deactivated'
            }), 401
        
        # Set current user in global context
        g.current_user = user
        g.auth_method = auth_method
        
        logger.debug(f"User {user.email} authenticated via {auth_method} for {request.endpoint}")
        
        return f(*args, **kwargs)
    
    return decorated_function


def jwt_required_only(f):
    """
    Middleware for endpoints that only support JWT authentication.
    Used for user-config, auth profile, etc.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.filter_by(id=user_id, is_active=True).first()
            
            if not user:
                logger.warning(f"JWT token valid but user {user_id} not found or inactive")
                return jsonify({'error': 'User not found or account deactivated'}), 401
            
            g.current_user = user
            g.auth_method = 'jwt'
            
            logger.debug(f"JWT authentication successful for user {user.email}")
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.warning(f"JWT authentication failed: {e}")
            return jsonify({'error': 'Invalid or missing JWT token'}), 401
    
    return decorated_function


def get_current_user():
    """
    Helper function to get the current authenticated user from Flask's g object.
    Returns None if no user is authenticated.
    """
    return getattr(g, 'current_user', None)


def get_auth_method():
    """
    Helper function to get the authentication method used.
    Returns 'jwt' or 'api_key' or None.
    """
    return getattr(g, 'auth_method', None)


def increment_user_usage(api_calls=1, audio_minutes=0.0):
    """
    Helper function to increment user usage statistics.
    Call this after successful API operations.
    """
    user = get_current_user()
    if user:
        try:
            user.increment_usage(api_calls=api_calls, audio_minutes=audio_minutes)
            logger.debug(f"Updated usage for user {user.email}: +{api_calls} calls, +{audio_minutes} minutes")
        except Exception as e:
            logger.error(f"Failed to update usage for user {user.email}: {e}")


def check_user_limits():
    """
    Helper function to check if user has reached their limits.
    Returns True if user can proceed, False if limits exceeded.
    """
    user = get_current_user()
    if not user:
        return False
    
    # Add your business logic for checking limits based on user.plan
    # For now, always allow (implement limits based on your business requirements)
    
    if user.plan == 'free':
        # Example: Free plan limit of 100 API calls per month
        if user.api_calls_month >= 100:
            logger.warning(f"User {user.email} exceeded free plan limit")
            return False
    elif user.plan == 'pro':
        # Example: Pro plan limit of 1000 API calls per month
        if user.api_calls_month >= 1000:
            logger.warning(f"User {user.email} exceeded pro plan limit")
            return False
    # Enterprise plans have no limits
    
    return True


def require_user_provider_config(provider_name):
    """
    Decorator to ensure user has configured the specified provider.
    Use this for endpoints that require specific provider API keys.
    
    Args:
        provider_name (str): Provider name like 'openai', 'deepgram', etc.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Check if user has configured this provider
            from models.provider import Provider, UserProviderConfig
            
            provider = Provider.query.filter_by(name=provider_name, is_active=True).first()
            if not provider:
                return jsonify({'error': f'Provider {provider_name} not available'}), 400
            
            config = UserProviderConfig.query.filter_by(
                user_id=user.id,
                provider_id=provider.id,
                is_active=True
            ).first()
            
            if not config:
                return jsonify({
                    'error': f'Provider {provider_name} not configured. Please add your API key in user configuration.',
                    'provider': provider_name,
                    'setup_required': True
                }), 400
            
            # Store provider config in g for use in the endpoint
            g.provider_config = config
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator