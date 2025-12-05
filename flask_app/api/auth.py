"""Authentication API blueprint for mobile app login."""
import logging
from flask import Blueprint, request, jsonify
from flask_app.services.session_manager import get_session_manager

bp = Blueprint('mobile_auth', __name__)
logger = logging.getLogger(__name__)

# Get session manager instance
session_manager = get_session_manager()


@bp.route('/login', methods=['POST'])
def login():
    """Simulate login and generate session token.

    Accepts JSON with:
    - username: User identifier
    - password: User password (not validated in demo)

    Returns:
    - auth_token: Session token for WebSocket authentication
    - user_id: User identifier
    - expires_at: Token expiration timestamp
    """
    logger.info("Login request received")

    data = request.get_json()
    if not data or 'username' not in data:
        logger.warning("Login failed: missing username")
        return jsonify({'error': 'Username is required'}), 400

    username = data.get('username')
    
    # Create session using session manager
    session_data = session_manager.create_session(username, expires_hours=24)

    logger.info(f"Login successful for user: {username}")

    return jsonify({
        **session_data,
        'message': 'Login successful'
    }), 200


@bp.route('/logout', methods=['POST'])
def logout():
    """Invalidate session token.

    Accepts JSON with:
    - auth_token: Session token to invalidate
    """
    data = request.get_json()
    auth_token = data.get('auth_token') if data else None

    if session_manager.invalidate_session(auth_token):
        return jsonify({'message': 'Logout successful'}), 200

    return jsonify({'message': 'Invalid or expired token'}), 401


@bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify if a session token is valid.

    Accepts JSON with:
    - auth_token: Session token to verify
    """
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
    """Check if a session token is valid (used by WebSocket handler)."""
    return session_manager.validate_session(auth_token)


def get_session_info(auth_token: str) -> dict:
    """Get session information for a valid token."""
    return session_manager.get_session_info(auth_token)
