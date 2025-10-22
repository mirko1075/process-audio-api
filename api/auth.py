"""Authentication endpoints for user management."""

import logging
import re
from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import IntegrityError
from utils.exceptions import InvalidRequestError

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__)


def validate_password(password):
    """
    Validate password meets security requirements.
    
    Args:
        password (str): Password to validate
        
    Raises:
        InvalidRequestError: If password doesn't meet requirements
        
    Returns:
        bool: True if password is valid
    """
    if not password:
        raise InvalidRequestError("Password is required")
    
    if len(password) < 8:
        raise InvalidRequestError("Password must be at least 8 characters long")
    
    # Additional security checks (recommended)
    if len(password.strip()) != len(password):
        raise InvalidRequestError("Password cannot start or end with whitespace")
    
    # Check for at least one letter and one number (recommended for stronger passwords)
    if not re.search(r'[a-zA-Z]', password):
        raise InvalidRequestError("Password must contain at least one letter")
    
    if not re.search(r'\d', password):
        raise InvalidRequestError("Password must contain at least one number")
    
    return True


def validate_email(email):
    """
    Validate email format.
    
    Args:
        email (str): Email to validate
        
    Raises:
        InvalidRequestError: If email format is invalid
        
    Returns:
        bool: True if email is valid
    """
    if not email:
        raise InvalidRequestError("Email is required")
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise InvalidRequestError("Invalid email format")
    
    return True

@bp.route('/register', methods=['POST'])
def register():
    """Register new user account."""
    try:
        from flask_jwt_extended import create_access_token
        from models.user import User
        from models import db
        
        data = request.get_json()
        
        # Validation
        required_fields = ['email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Validate email format
        try:
            validate_email(email)
        except InvalidRequestError as e:
            return jsonify({'error': str(e)}), 400
        
        # Validate password before proceeding
        try:
            validate_password(password)
        except InvalidRequestError as e:
            return jsonify({'error': str(e)}), 400
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
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
        
        # Generate first API key
        api_key_value = user.generate_api_key("Default API Key")
        
        # Create JWT token
        access_token = create_access_token(identity=user.id)
        
        logger.info(f"New user registered: {email}")
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'api_key': api_key_value  # Show only once!
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Email already registered'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@bp.route('/login', methods=['POST'])
def login():
    """User login with email and password."""
    try:
        from flask_jwt_extended import create_access_token
        from models.user import User
        from models import db
        from datetime import datetime
        
        data = request.get_json()
        
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account deactivated'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create JWT token
        access_token = create_access_token(identity=user.id)
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        from models.user import User
        
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict(),
            'api_keys': [key.to_dict() for key in user.api_keys if key.is_active]
        })
        
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return jsonify({'error': 'Authentication required'}), 401

@bp.route('/api-keys', methods=['POST'])
def create_api_key():
    """Generate new API key for current user."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        from models.user import User
        
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        name = data.get('name', 'API Key')
        
        # Generate new key
        api_key_value = user.generate_api_key(name)
        
        logger.info(f"New API key created for user {user.email}: {name}")
        
        return jsonify({
            'message': 'API key created successfully',
            'api_key': api_key_value,  # Show only once!
            'name': name
        }), 201
        
    except Exception as e:
        logger.error(f"API key creation error: {str(e)}")
        return jsonify({'error': 'Failed to create API key'}), 500

@bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
def delete_api_key(key_id):
    """Deactivate an API key."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        from models.user import ApiKey
        from models import db
        
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        api_key = ApiKey.query.filter_by(
            id=key_id,
            user_id=user_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        api_key.is_active = False
        db.session.commit()
        
        logger.info(f"API key deactivated: {key_id}")
        
        return jsonify({'message': 'API key deactivated'})
        
    except Exception as e:
        logger.error(f"API key deletion error: {str(e)}")
        return jsonify({'error': 'Failed to deactivate API key'}), 500