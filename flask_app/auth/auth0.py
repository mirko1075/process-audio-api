"""Auth0 JWT authentication for Flask API and SocketIO WebSocket."""
import os
import logging
from functools import wraps
from typing import Dict, Optional, Callable
import requests
from flask import request, jsonify, g
import jwt
from jwt import PyJWKClient
from werkzeug.exceptions import Unauthorized

logger = logging.getLogger(__name__)

# Auth0 Configuration from environment
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE')
ALGORITHMS = ["RS256"]

# Timeout for Auth0 API requests (in seconds)
AUTH0_REQUEST_TIMEOUT = int(os.getenv('AUTH0_REQUEST_TIMEOUT', '30'))

# Security: Feature flag to allow insecure session token fallback
# WARNING: This should ONLY be enabled in development/testing environments
# In production, this MUST be set to 'false' or omitted entirely
ALLOW_INSECURE_SESSION_AUTH = os.getenv('ALLOW_INSECURE_SESSION_AUTH', 'false').lower() == 'true'

if ALLOW_INSECURE_SESSION_AUTH:
    logger.warning(
        "⚠️  SECURITY WARNING: ALLOW_INSECURE_SESSION_AUTH is enabled! "
        "Session token fallback allows unauthenticated access. "
        "This should NEVER be enabled in production."
    )

# Cache PyJWKClient instance to avoid repeated JWKS downloads
_jwks_client = None


def get_jwks_client():
    """Get cached PyJWKClient instance for JWKS key retrieval.
    
    Returns:
        Cached PyJWKClient instance
    """
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(get_jwks_url())
    return _jwks_client


class Auth0Error(Exception):
    """Custom exception for Auth0 authentication errors."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_jwks_url() -> str:
    """Get JWKS URL from Auth0 domain."""
    if not AUTH0_DOMAIN:
        raise Auth0Error("AUTH0_DOMAIN not configured", 500)
    return f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"


def get_token_from_header() -> Optional[str]:
    """Extract JWT token from Authorization header.

    Returns:
        Token string or None if not found
    """
    auth_header = request.headers.get('Authorization', None)

    if not auth_header:
        return None

    parts = auth_header.split()

    if parts[0].lower() != 'bearer':
        raise Auth0Error('Authorization header must start with Bearer')
    elif len(parts) == 1:
        raise Auth0Error('Token not found')
    elif len(parts) > 2:
        raise Auth0Error('Authorization header must be Bearer token')

    return parts[1]


def verify_jwt(token: str) -> Dict:
    """Verify and decode Auth0 JWT token with RS256 algorithm.

    Downloads JWKS from Auth0, validates:
    - Issuer (iss)
    - Audience (aud)
    - Algorithm (RS256)
    - Expiration (exp)
    - Signature

    Args:
        token: JWT token string

    Returns:
        Decoded token payload as dict

    Raises:
        Auth0Error: If token is invalid or verification fails
    """
    if not AUTH0_DOMAIN:
        raise Auth0Error("AUTH0_DOMAIN environment variable not set", 500)

    if not AUTH0_AUDIENCE:
        raise Auth0Error("AUTH0_AUDIENCE environment variable not set", 500)

    try:
        # Get JWKS URL
        jwks_url = get_jwks_url()

        # Get cached PyJWKClient instance (avoids repeated JWKS downloads)
        jwks_client = get_jwks_client()

        # Get the signing key from JWT header
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )

        logger.info(f"Token verified successfully for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        raise Auth0Error("Token has expired")
    except jwt.InvalidAudienceError:
        raise Auth0Error("Invalid audience")
    except jwt.InvalidIssuerError:
        raise Auth0Error("Invalid issuer")
    except jwt.InvalidSignatureError:
        raise Auth0Error("Invalid signature")
    except jwt.InvalidTokenError as e:
        raise Auth0Error(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.exception(f"Token verification error: {e}")
        raise Auth0Error("Token verification failed")


def require_auth(f: Callable) -> Callable:
    """Decorator for Flask routes requiring Auth0 authentication.

    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user = request.user  # Access decoded token payload
            return {'user': user}

    The decorated function will have access to:
    - request.user: Full decoded JWT payload
    - request.user_id: User ID from 'sub' claim
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get token from Authorization header
            token = get_token_from_header()

            if not token:
                return jsonify({
                    'error': 'Authorization header is required',
                    'message': 'Please provide a valid Bearer token'
                }), 401

            # Verify and decode token
            payload = verify_jwt(token)

            # Attach user info and token to request object
            request.user = payload
            request.user_id = payload.get('sub')
            request.auth_token = token  # Store the validated token for reuse

            # Also store in Flask's g object for access in nested functions
            g.user = payload
            g.user_id = payload.get('sub')
            g.auth_token = token  # Store token in g as well

            return f(*args, **kwargs)

        except Auth0Error as e:
            logger.warning(f"Authentication failed: {e.message}")
            return jsonify({
                'error': 'authentication_failed',
                'message': e.message
            }), e.status_code
        except Exception as e:
            logger.error(f"Unexpected error in auth decorator: {e}")
            return jsonify({
                'error': 'internal_error',
                'message': 'An unexpected error occurred'
            }), 500

    return decorated_function


def verify_websocket_token(token: str) -> Dict:
    """Verify Auth0 token for WebSocket connections.

    This is a convenience wrapper around verify_jwt for WebSocket handlers.

    Args:
        token: JWT token from WebSocket auth handshake

    Returns:
        Decoded token payload

    Raises:
        Auth0Error: If token is invalid

    Usage in SocketIO:
        @socketio.on('connect', namespace='/audio-stream')
        def handle_connect(auth):
            try:
                token = auth.get('token')
                user = verify_websocket_token(token)
                # Connection allowed
                return True
            except Auth0Error as e:
                # Connection rejected
                return False
    """
    if not token:
        raise Auth0Error("Token is required for WebSocket connection")

    return verify_jwt(token)


def get_user_info(access_token: str) -> Dict:
    """Get user profile information from Auth0 userinfo endpoint.

    Args:
        access_token: Valid Auth0 access token

    Returns:
        User profile data as dict

    Raises:
        Auth0Error: If request fails
    """
    if not AUTH0_DOMAIN:
        raise Auth0Error("AUTH0_DOMAIN not configured", 500)

    userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"

    try:
        response = requests.get(
            userinfo_url,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=AUTH0_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        logger.error(f"Failed to fetch user info: {e}")
        raise Auth0Error(f"Failed to fetch user info: {str(e)}")


# Error handler for Auth0 errors
def register_auth_error_handlers(app):
    """Register error handlers for Auth0 authentication errors.

    Call this in your app factory to enable automatic error handling.

    Usage:
        from flask_app.auth.auth0 import register_auth_error_handlers
        register_auth_error_handlers(app)
    """
    @app.errorhandler(Auth0Error)
    def handle_auth_error(error):
        return jsonify({
            'error': 'authentication_error',
            'message': error.message
        }), error.status_code

    @app.errorhandler(Unauthorized)
    def handle_unauthorized(error):
        return jsonify({
            'error': 'unauthorized',
            'message': 'Authentication required'
        }), 401
