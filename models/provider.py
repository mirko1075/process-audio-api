"""Provider and user configuration models for SaaS API key management."""

from datetime import datetime
from models import db


class Provider(db.Model):
    """AI Service Providers (OpenAI, Deepgram, etc.)"""
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 'openai', 'deepgram'
    display_name = db.Column(db.String(100), nullable=False)  # 'OpenAI', 'Deepgram Nova-2'
    description = db.Column(db.Text, nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    documentation_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    models = db.relationship('ProviderModel', back_populates='provider', cascade='all, delete-orphan')
    user_configs = db.relationship('UserProviderConfig', back_populates='provider', cascade='all, delete-orphan')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Provider {self.name}>'

    def to_dict(self):
        """Convert provider to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'website_url': self.website_url,
            'documentation_url': self.documentation_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ProviderModel(db.Model):
    """Models available for each provider"""
    __tablename__ = 'provider_models'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)  # 'whisper-1', 'gpt-4o-mini'
    display_name = db.Column(db.String(150), nullable=False)  # 'Whisper v1', 'GPT-4o Mini'
    model_type = db.Column(db.String(50), nullable=False, index=True)  # 'transcription', 'translation', 'chat'
    
    # Pricing info
    cost_per_unit = db.Column(db.Float, nullable=True)  # Per minute, per token, etc.
    cost_unit = db.Column(db.String(20), nullable=True)  # 'minute', 'token', 'request'
    
    # Model specifications
    max_file_size_mb = db.Column(db.Integer, nullable=True)  # Max file size supported
    supported_formats = db.Column(db.Text, nullable=True)  # JSON array of supported formats
    
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    provider = db.relationship('Provider', back_populates='models')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one model name per provider
    __table_args__ = (db.UniqueConstraint('provider_id', 'name'),)

    def __repr__(self):
        return f'<ProviderModel {self.provider.name}:{self.name}>'

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'type': self.model_type,
            'cost_per_unit': self.cost_per_unit,
            'cost_unit': self.cost_unit,
            'max_file_size_mb': self.max_file_size_mb,
            'supported_formats': self.supported_formats,
            'is_active': self.is_active
        }


class UserProviderConfig(db.Model):
    """User's API keys and configuration for each provider - SaaS model"""
    __tablename__ = 'user_provider_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False, index=True)
    
    # Encrypted API key for this provider - USER MUST PROVIDE THEIR OWN
    api_key_encrypted = db.Column(db.Text, nullable=False)  # AES encrypted
    api_key_preview = db.Column(db.String(50), nullable=False)  # sk-****...****1234
    
    # Configuration
    is_active = db.Column(db.Boolean, default=True, index=True)
    default_model_id = db.Column(db.Integer, db.ForeignKey('provider_models.id'), nullable=True)
    
    # Usage tracking for billing and analytics
    total_requests = db.Column(db.Integer, default=0)
    total_cost_usd = db.Column(db.Float, default=0.0)
    total_audio_minutes = db.Column(db.Float, default=0.0)
    total_tokens_processed = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', back_populates='provider_configs')
    provider = db.relationship('Provider', back_populates='user_configs')
    default_model = db.relationship('ProviderModel', foreign_keys=[default_model_id])
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one config per user-provider
    __table_args__ = (db.UniqueConstraint('user_id', 'provider_id'),)

    def __repr__(self):
        return f'<UserProviderConfig user={self.user_id} provider={self.provider.name}>'

    def to_dict(self, include_sensitive=False):
        """Convert config to dictionary for API responses."""
        result = {
            'id': self.id,
            'provider': self.provider.to_dict() if self.provider else None,
            'api_key_preview': self.api_key_preview,
            'is_active': self.is_active,
            'default_model': self.default_model.to_dict() if self.default_model else None,
            'total_requests': self.total_requests,
            'total_cost_usd': self.total_cost_usd,
            'total_audio_minutes': self.total_audio_minutes,
            'total_tokens_processed': self.total_tokens_processed,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Only include encrypted key for internal use
        if include_sensitive:
            result['api_key_encrypted'] = self.api_key_encrypted
        
        return result

    def update_usage(self, cost_usd=0.0, audio_minutes=0.0, tokens=0):
        """Update usage statistics."""
        self.total_requests += 1
        self.total_cost_usd += cost_usd
        self.total_audio_minutes += audio_minutes
        self.total_tokens_processed += tokens
        self.last_used = datetime.utcnow()
        db.session.commit()