"""Protected API routes requiring Auth0 authentication."""
from flask import Blueprint, jsonify, request
from flask_app.auth.auth0 import require_auth, get_user_info, Auth0Error
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('protected', __name__)


@bp.route('/api/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current authenticated user information.

    Returns user data from JWT token payload.

    Returns:
        JSON response with user information

    Example:
        GET /api/me
        Authorization: Bearer <token>

        Response:
        {
            "user": {
                "sub": "auth0|123456789",
                "email": "user@example.com",
                "email_verified": true,
                ...
            }
        }
    """
    try:
        # User data is already attached to request by @require_auth decorator
        user_data = request.user

        return jsonify({
            'user': user_data,
            'user_id': request.user_id
        }), 200

    except Exception as e:
        logger.error(f"Error in /api/me: {e}")
        return jsonify({
            'error': 'internal_error',
            'message': 'Failed to retrieve user information'
        }), 500


@bp.route('/api/userinfo', methods=['GET'])
@require_auth
def get_userinfo():
    """Get detailed user information from Auth0 userinfo endpoint.

    Fetches extended user profile from Auth0's /userinfo endpoint.

    Returns:
        JSON response with detailed user profile

    Example:
        GET /api/userinfo
        Authorization: Bearer <token>

        Response:
        {
            "sub": "auth0|123456789",
            "email": "user@example.com",
            "name": "John Doe",
            "picture": "https://...",
            ...
        }
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None

        if not token:
            return jsonify({
                'error': 'missing_token',
                'message': 'Authorization token is required'
            }), 401

        # Fetch user info from Auth0
        user_info = get_user_info(token)

        return jsonify(user_info), 200

    except Auth0Error as e:
        logger.error(f"Auth0 error in /api/userinfo: {e.message}")
        return jsonify({
            'error': 'auth0_error',
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.error(f"Error in /api/userinfo: {e}")
        return jsonify({
            'error': 'internal_error',
            'message': 'Failed to retrieve user information'
        }), 500


@bp.route('/api/protected/test', methods=['GET'])
@require_auth
def protected_test():
    """Test endpoint to verify authentication is working.

    Simple test endpoint that requires authentication.

    Returns:
        JSON response confirming authentication

    Example:
        GET /api/protected/test
        Authorization: Bearer <token>

        Response:
        {
            "message": "Authentication successful",
            "user_id": "auth0|123456789"
        }
    """
    return jsonify({
        'message': 'Authentication successful',
        'user_id': request.user_id,
        'authenticated': True
    }), 200
