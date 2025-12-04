"""Authentication API blueprint for mobile app login."""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import secrets

bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# In-memory session storage (for demo purposes)
# In production, use Redis or database
active_sessions = {}


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
    password = data.get('password', '')  # Not validated in demo

    # Generate secure session token
    auth_token = f"session_{secrets.token_urlsafe(32)}"
    expires_at = datetime.utcnow() + timedelta(hours=24)

    # Store session in memory
    active_sessions[auth_token] = {
        'username': username,
        'user_id': username.lower().replace(' ', '_'),
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': expires_at.isoformat()
    }

    logger.info(f"Login successful for user: {username}")

    return jsonify({
        'auth_token': auth_token,
        'user_id': username.lower().replace(' ', '_'),
        'expires_at': expires_at.isoformat(),
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

    if auth_token and auth_token in active_sessions:
        username = active_sessions[auth_token]['username']
        del active_sessions[auth_token]
        logger.info(f"Logout successful for user: {username}")
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

    if auth_token and auth_token in active_sessions:
        session = active_sessions[auth_token]
        expires_at = datetime.fromisoformat(session['expires_at'])

        # Check if token is expired
        if datetime.utcnow() > expires_at:
            del active_sessions[auth_token]
            return jsonify({'valid': False, 'message': 'Token expired'}), 401

        return jsonify({
            'valid': True,
            'user_id': session['user_id'],
            'username': session['username']
        }), 200

    return jsonify({'valid': False, 'message': 'Invalid token'}), 401


def is_valid_session(auth_token: str) -> bool:
    """Check if a session token is valid (used by WebSocket handler)."""
    if not auth_token or auth_token not in active_sessions:
        return False

    session = active_sessions[auth_token]
    expires_at = datetime.fromisoformat(session['expires_at'])

    # Check if token is expired
    if datetime.utcnow() > expires_at:
        del active_sessions[auth_token]
        return False

    return True


def get_session_info(auth_token: str) -> dict:
    """Get session information for a valid token."""
    if auth_token in active_sessions:
        return active_sessions[auth_token]
    return None
