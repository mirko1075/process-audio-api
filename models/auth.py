"""User and API Key models for authentication system."""

from datetime import datetime
from models import db
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import hashlib


class User(db.Model):
    """User accounts for the SaaS platform."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    
    # Subscription and status
    plan = db.Column(db.String(20), default='free', nullable=False)  # free, pro, enterprise
    is_active = db.Column(db.Boolean, default=True, index=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Usage tracking
    api_calls_month = db.Column(db.Integer, default=0)
    audio_minutes_month = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    api_keys = db.relationship('ApiKey', back_populates='user', cascade='all, delete-orphan')
    provider_configs = db.relationship('UserProviderConfig', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary for API responses."""
        result = {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'plan': self.plan,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'api_calls_month': self.api_calls_month,
            'audio_minutes_month': self.audio_minutes_month,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            result['api_keys_count'] = len(self.api_keys)
            result['providers_configured'] = len([c for c in self.provider_configs if c.is_active])
        
        return result
    
    def update_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def increment_usage(self, api_calls=1, audio_minutes=0.0):
        """Increment monthly usage counters."""
        self.api_calls_month += api_calls
        self.audio_minutes_month += audio_minutes
        db.session.commit()


class ApiKey(db.Model):
    """API keys for programmatic access (Make.com, etc.)"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # API key data
    key_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    key_preview = db.Column(db.String(50), nullable=False)  # usr_123_****
    name = db.Column(db.String(100), nullable=True)  # "Production Integration"
    
    # Status and usage
    is_active = db.Column(db.Boolean, default=True, index=True)
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='api_keys')
    
    def __repr__(self):
        return f'<ApiKey {self.key_preview} user={self.user_id}>'
    
    @staticmethod
    def generate_key(user_id):
        """Generate a new API key for a user."""
        # Format: usr_{user_id}_{random_string}
        random_part = secrets.token_urlsafe(32)
        key = f"usr_{user_id}_{random_part}"
        return key
    
    @staticmethod
    def hash_key(key):
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def create_preview(key):
        """Create a preview of the API key for display."""
        if len(key) < 16:
            return key[:4] + "****"
        return key[:12] + "****" + key[-4:]
    
    @classmethod
    def create_for_user(cls, user_id, name=None):
        """Create a new API key for a user."""
        key = cls.generate_key(user_id)
        key_hash = cls.hash_key(key)
        key_preview = cls.create_preview(key)
        
        api_key = cls(
            user_id=user_id,
            key_hash=key_hash,
            key_preview=key_preview,
            name=name,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return api_key, key  # Return both the model and the actual key
    
    @classmethod
    def authenticate(cls, key):
        """Authenticate an API key and return the associated user."""
        if not key or not key.startswith('usr_'):
            return None
        
        key_hash = cls.hash_key(key)
        api_key = cls.query.filter_by(
            key_hash=key_hash,
            is_active=True
        ).first()
        
        if not api_key:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Update usage
        api_key.usage_count += 1
        api_key.last_used = datetime.utcnow()
        db.session.commit()
        
        return api_key.user
    
    def to_dict(self):
        """Convert API key to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'key_preview': self.key_preview,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def deactivate(self):
        """Deactivate this API key."""
        self.is_active = False
        db.session.commit()