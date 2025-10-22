"""
Authentication routes for user registration, login, and API key management.
These endpoints use JWT-only authentication (no API key support).
"""

from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import logging
from datetime import timedelta

from models.auth import User, ApiKey
from models import db
from utils.auth_middleware import jwt_required_only
from utils.exceptions import InvalidRequestError

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Check password length
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 400
        
        # Create new user
        user = User(
            email=email,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            company=data.get('company', ''),
            plan=data.get('plan', 'free')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create initial API key for the user
        api_key_obj, api_key = ApiKey.create_for_user(
            user_id=user.id,
            name="Default API Key"
        )
        
        # Create JWT token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )
        
        logger.info(f"New user registered: {email}")
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'api_key': api_key,  # Show API key only once
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login with email and password."""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Update last login
        user.update_login()
        
        # Create JWT token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required_only
def get_profile():
    """Get current user profile and API keys."""
    try:
        user = g.current_user
        api_keys = ApiKey.query.filter_by(user_id=user.id, is_active=True).all()
        
        return jsonify({
            'user': user.to_dict(include_sensitive=True),
            'api_keys': [key.to_dict() for key in api_keys]
        }), 200
        
    except Exception as e:
        logger.error(f"Get profile failed: {e}")
        return jsonify({'error': 'Failed to retrieve profile'}), 500


@auth_bp.route('/api-keys', methods=['POST'])
@jwt_required_only
def create_api_key():
    """Create a new API key for the current user."""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'Unnamed API Key')
        
        user = g.current_user
        
        # Create new API key
        api_key_obj, api_key = ApiKey.create_for_user(
            user_id=user.id,
            name=name
        )
        
        logger.info(f"New API key created for user {user.email}: {name}")
        
        return jsonify({
            'message': 'API key created successfully',
            'api_key': api_key,  # Show full key only once
            'name': name,
            'id': api_key_obj.id,
            'preview': api_key_obj.key_preview
        }), 201
        
    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create API key'}), 500


@auth_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@jwt_required_only
def delete_api_key(key_id):
    """Deactivate an API key."""
    try:
        user = g.current_user
        
        # Find API key belonging to current user
        api_key = ApiKey.query.filter_by(
            id=key_id,
            user_id=user.id,
            is_active=True
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Deactivate the key
        api_key.deactivate()
        
        logger.info(f"API key deactivated for user {user.email}: {api_key.key_preview}")
        
        return jsonify({'message': 'API key deactivated'}), 200
        
    except Exception as e:
        logger.error(f"API key deletion failed: {e}")
        return jsonify({'error': 'Failed to deactivate API key'}), 500


@auth_bp.route('/test', methods=['GET'])
@jwt_required_only
def test_jwt():
    """Test endpoint to verify JWT authentication."""
    user = g.current_user
    
    return jsonify({
        'message': 'JWT authentication successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'plan': user.plan
        },
        'authentication_method': 'jwt'
    }), 200