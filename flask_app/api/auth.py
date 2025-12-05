"""Authentication API blueprint for mobile app login.

⚠️  SECURITY WARNING - DEPRECATED ENDPOINTS
=====================================
The endpoints in this module provide session-based authentication WITHOUT
real credential verification. This is a SECURITY VULNERABILITY in production.

These endpoints should ONLY be used in development/testing environments with
the ALLOW_INSECURE_SESSION_AUTH=true flag.

For production:
- Use Auth0 JWT tokens exclusively
- Remove or disable these endpoints
- Implement proper authentication if session tokens are required

See COPILOT_SUGGESTIONS_RESOLVED.md for security recommendations.
"""
import logging
import os
from flask import Blueprint, request, jsonify
from flask_app.services.session_manager import get_session_manager

bp = Blueprint('mobile_auth', __name__)
logger = logging.getLogger(__name__)

# Get session manager instance
session_manager = get_session_manager()

# Security: Check if insecure auth is enabled
ALLOW_INSECURE_SESSION_AUTH = os.getenv('ALLOW_INSECURE_SESSION_AUTH', 'false').lower() == 'true'

if not ALLOW_INSECURE_SESSION_AUTH:
    logger.warning(
        "⚠️  Mobile auth endpoints are DEPRECATED and DISABLED in secure mode. "
        "Set ALLOW_INSECURE_SESSION_AUTH=true only in development/testing."
    )


@bp.route('/login', methods=['POST'])
def login():
    """[DEPRECATED - INSECURE] Simulate login and generate session token.
    
    ⚠️  SECURITY WARNING: This endpoint does NOT verify credentials!
    It generates tokens for ANY username without authentication.
    
    This is a CRITICAL SECURITY VULNERABILITY and should NOT be used in production.
    
    Use Auth0 authentication instead for production environments.

    Accepts JSON with:
    - username: User identifier
    - password: User password (NOT VALIDATED - SECURITY ISSUE)

    Returns:
    - auth_token: Session token for WebSocket authentication
    - user_id: User identifier
    - expires_at: Token expiration timestamp
    """
    # Block endpoint in production (secure mode)
    if not ALLOW_INSECURE_SESSION_AUTH:
        logger.warning("Attempt to use deprecated /mobile-auth/login endpoint in secure mode")
        return jsonify({
            'error': 'endpoint_disabled',
            'message': 'This endpoint is disabled in production. Use Auth0 authentication.',
            'details': 'Set ALLOW_INSECURE_SESSION_AUTH=true only in development/testing.'
        }), 403

    logger.warning("⚠️  Using INSECURE mobile auth endpoint - development mode only!")
    logger.info("Login request received")

    data = request.get_json()
    if not data or 'username' not in data:
        logger.warning("Login failed: missing username")
        return jsonify({'error': 'Username is required'}), 400

    username = data.get('username')
    
    # ⚠️  SECURITY ISSUE: No password validation!
    # This allows ANYONE to create a session for ANY username
    
    # Create session using session manager
    session_data = session_manager.create_session(username, expires_hours=24)

    logger.warning(f"INSECURE session created for user: {username} (no credential check)")

    return jsonify({
        **session_data,
        'message': 'Login successful (DEVELOPMENT MODE - NO REAL AUTH)',
        'warning': 'This endpoint does not verify credentials. Use Auth0 for production.'
    }), 200


@bp.route('/logout', methods=['POST'])
def logout():
    """[DEPRECATED - INSECURE] Invalidate session token.
    
    ⚠️  This endpoint is deprecated. Only enabled in development mode.

    Accepts JSON with:
    - auth_token: Session token to invalidate
    """
    if not ALLOW_INSECURE_SESSION_AUTH:
        return jsonify({
            'error': 'endpoint_disabled',
            'message': 'This endpoint is disabled in production.'
        }), 403
    
    data = request.get_json()
    auth_token = data.get('auth_token') if data else None

    if session_manager.invalidate_session(auth_token):
        return jsonify({'message': 'Logout successful'}), 200

    return jsonify({'message': 'Invalid or expired token'}), 401


@bp.route('/verify', methods=['POST'])
def verify_token():
    """[DEPRECATED - INSECURE] Verify if a session token is valid.
    
    ⚠️  This endpoint is deprecated. Only enabled in development mode.

    Accepts JSON with:
    - auth_token: Session token to verify
    """
    if not ALLOW_INSECURE_SESSION_AUTH:
        return jsonify({
            'error': 'endpoint_disabled',
            'message': 'This endpoint is disabled in production.'
        }), 403
    
    data = request.get_json()
    auth_token = data.get('auth_token') if data else None

    session_info = session_manager.get_session_info(auth_token)
    
    if session_info:
        return jsonify({
            'valid': True,
            'user_id': session_info['user_id'],
            'username': session_info['username']
        }), 200

    return jsonify({'valid': False, 'message': 'Invalid token'}), 401


def is_valid_session(auth_token: str) -> bool:
    """Check if a session token is valid (used by WebSocket handler).
    
    ⚠️  Only works when ALLOW_INSECURE_SESSION_AUTH=true
    """
    if not ALLOW_INSECURE_SESSION_AUTH:
        return False
    return session_manager.validate_session(auth_token)


def get_session_info(auth_token: str) -> dict:
    """Get session information for a valid token.
    
    ⚠️  Only works when ALLOW_INSECURE_SESSION_AUTH=true
    """
    if not ALLOW_INSECURE_SESSION_AUTH:
        return None
    return session_manager.get_session_info(auth_token)
