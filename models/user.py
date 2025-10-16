"""User model with API key support for authentication."""

import secrets
import hashlib
from datetime import datetime, timedelta
from . import db, bcrypt

class User(db.Model):
    """User model for SaaS authentication."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Profile info
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    
    # SaaS fields
    plan = db.Column(db.String(20), default='free')  # free, pro, enterprise
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Usage tracking
    api_calls_month = db.Column(db.Integer, default=0)
    audio_minutes_month = db.Column(db.Float, default=0.0)
    
    # Relationships
    api_keys = db.relationship('ApiKey', backref='user', lazy=True, cascade='all, delete-orphan')
    usage_logs = db.relationship('UsageLog', backref='user', lazy=True)
    
    def set_password(self, password):
        """Set encrypted password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check password against hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def generate_api_key(self, name="Default API Key"):
        """Generate new API key for this user."""
        # Format: usr_<user_id>_<random_token>
        random_token = secrets.token_urlsafe(32)
        key_value = f"usr_{self.id}_{random_token}"
        
        # Hash for storage
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        
        api_key = ApiKey(
            user_id=self.id,
            name=name,
            key_hash=key_hash,
            key_prefix=f"usr_{self.id}_"
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return key_value  # Return unhashed key only once
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'plan': self.plan,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'api_calls_month': self.api_calls_month,
            'audio_minutes_month': self.audio_minutes_month
        }


class ApiKey(db.Model):
    """API Keys for external integrations."""
    
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)  # "Make.com Integration"
    key_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA256 hash
    key_prefix = db.Column(db.String(20), nullable=False)  # usr_123_ for display
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Usage tracking
    last_used = db.Column(db.DateTime, nullable=True)
    usage_count = db.Column(db.Integer, default=0)
    
    # Security
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration
    
    @staticmethod
    def verify_key(key_value):
        """Verify API key and return associated user."""
        if not key_value or not key_value.startswith('usr_'):
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        
        # Find active key
        api_key = ApiKey.query.filter_by(
            key_hash=key_hash,
            is_active=True
        ).first()
        
        if not api_key:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Update usage
        api_key.last_used = datetime.utcnow()
        api_key.usage_count += 1
        db.session.commit()
        
        return api_key.user
    
    def to_dict(self):
        """Convert API key to dictionary (without sensitive data)."""
        return {
            'id': self.id,
            'name': self.name,
            'key_preview': f"{self.key_prefix}****",
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class UsageLog(db.Model):
    """Track API usage for billing."""
    
    __tablename__ = 'usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Service info
    service = db.Column(db.String(50), nullable=False)  # 'deepgram', 'whisper', etc.
    endpoint = db.Column(db.String(100), nullable=False)  # '/transcriptions/deepgram'
    
    # Usage data
    audio_duration_seconds = db.Column(db.Float, nullable=True)
    tokens_used = db.Column(db.Integer, nullable=True)
    characters_processed = db.Column(db.Integer, nullable=True)
    
    # Cost tracking
    cost_usd = db.Column(db.Float, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    def to_dict(self):
        """Convert usage log to dictionary."""
        return {
            'id': self.id,
            'service': self.service,
            'endpoint': self.endpoint,
            'audio_duration_seconds': self.audio_duration_seconds,
            'tokens_used': self.tokens_used,
            'characters_processed': self.characters_processed,
            'cost_usd': self.cost_usd,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ip_address': self.ip_address
        }