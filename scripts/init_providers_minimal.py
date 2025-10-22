#!/usr/bin/env python3
"""Initialize providers and models in SQLite database for testing - minimal version."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Simple logging setup
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

def create_test_app():
    """Create a minimal Flask app for testing with SQLite."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_saas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app

# Initialize db first
db = SQLAlchemy()

# Simple Provider model for testing
class Provider(db.Model):
    """AI Service Providers (OpenAI, Deepgram, etc.)"""
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    api_url = db.Column(db.String(255), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    documentation_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Provider {self.name}>'

class ProviderModel(db.Model):
    """Models available for each provider"""
    __tablename__ = 'provider_models'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False, index=True)  # 'transcription', 'translation', 'llm'
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    provider = db.relationship('Provider', backref='models')
    
    # Unique constraint: one model name per provider
    __table_args__ = (db.UniqueConstraint('provider_id', 'name'),)

    def __repr__(self):
        return f'<ProviderModel {self.name}>'

def init_providers():
    """Initialize providers and their models in the database."""
    try:
        print("🚀 Initializing providers and models in SQLite...")
        
        app = create_test_app()
        
        # Initialize db with app
        db.init_app(app)
        
        with app.app_context():
            # Create tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Provider definitions
            providers_data = [
                {
                    'name': 'OpenAI',
                    'description': 'OpenAI API for transcription and language models',
                    'api_url': 'https://api.openai.com/v1',
                    'documentation_url': 'https://platform.openai.com/docs/api-reference',
                    'website_url': 'https://openai.com/',
                    'models': [
                        {'name': 'whisper-1', 'type': 'transcription', 'description': 'OpenAI Whisper speech-to-text model'},
                        {'name': 'gpt-4o-mini', 'type': 'llm', 'description': 'GPT-4O Mini language model for text processing'},
                        {'name': 'gpt-4o', 'type': 'llm', 'description': 'GPT-4O advanced language model'},
                        {'name': 'gpt-3.5-turbo', 'type': 'llm', 'description': 'GPT-3.5 Turbo cost-effective language model'},
                    ]
                },
                {
                    'name': 'Deepgram',
                    'description': 'Deepgram speech recognition and audio intelligence platform',
                    'api_url': 'https://api.deepgram.com/v1',
                    'documentation_url': 'https://developers.deepgram.com/',
                    'website_url': 'https://deepgram.com/',
                    'models': [
                        {'name': 'nova-2', 'type': 'transcription', 'description': 'Deepgram Nova-2 speech-to-text model'},
                        {'name': 'whisper', 'type': 'transcription', 'description': 'Deepgram hosted Whisper model'},
                        {'name': 'enhanced', 'type': 'transcription', 'description': 'Deepgram Enhanced model for improved accuracy'},
                        {'name': 'base', 'type': 'transcription', 'description': 'Deepgram Base model for general transcription'},
                    ]
                },
                {
                    'name': 'AssemblyAI',
                    'description': 'AssemblyAI speech-to-text and audio intelligence API',
                    'api_url': 'https://api.assemblyai.com/v2',
                    'documentation_url': 'https://www.assemblyai.com/docs/',
                    'website_url': 'https://www.assemblyai.com/',
                    'models': [
                        {'name': 'default', 'type': 'transcription', 'description': 'AssemblyAI default transcription model'},
                        {'name': 'best', 'type': 'transcription', 'description': 'AssemblyAI best accuracy model (higher cost)'},
                    ]
                },
                {
                    'name': 'DeepSeek',
                    'description': 'DeepSeek AI language models for code and text generation',
                    'api_url': 'https://api.deepseek.com/v1',
                    'documentation_url': 'https://platform.deepseek.com/api-docs/',
                    'website_url': 'https://www.deepseek.com/',
                    'models': [
                        {'name': 'deepseek-chat', 'type': 'llm', 'description': 'DeepSeek Chat model for conversational AI'},
                        {'name': 'deepseek-coder', 'type': 'llm', 'description': 'DeepSeek Coder model specialized for programming'},
                    ]
                },
                {
                    'name': 'Google',
                    'description': 'Google Cloud AI and language services',
                    'api_url': 'https://translation.googleapis.com/language/translate/v2',
                    'documentation_url': 'https://cloud.google.com/translate/docs/',
                    'website_url': 'https://cloud.google.com/translate',
                    'models': [
                        {'name': 'translate-v2', 'type': 'translation', 'description': 'Google Translate API v2'},
                        {'name': 'translate-v3', 'type': 'translation', 'description': 'Google Translate API v3 with advanced features'},
                    ]
                },
            ]
            
            created_count = 0
            model_count = 0
            
            for provider_data in providers_data:
                # Check if provider already exists
                existing_provider = Provider.query.filter_by(name=provider_data['name']).first()
                if existing_provider:
                    logger.info(f"Provider {provider_data['name']} already exists, skipping...")
                    continue
                
                # Create provider
                provider = Provider(
                    name=provider_data['name'],
                    description=provider_data['description'],
                    api_url=provider_data['api_url'],
                    documentation_url=provider_data['documentation_url'],
                    website_url=provider_data['website_url'],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(provider)
                db.session.flush()  # Get the provider ID
                
                # Create models for this provider
                for model_data in provider_data['models']:
                    model = ProviderModel(
                        provider_id=provider.id,
                        name=model_data['name'],
                        type=model_data['type'],
                        description=model_data['description'],
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(model)
                    model_count += 1
                
                created_count += 1
                logger.info(f"✅ Created provider: {provider_data['name']} with {len(provider_data['models'])} models")
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n🎉 Successfully initialized {created_count} providers with {model_count} models!")
            print("📊 Summary:")
            for provider_data in providers_data:
                provider = Provider.query.filter_by(name=provider_data['name']).first()
                if provider:
                    models = ProviderModel.query.filter_by(provider_id=provider.id).all()
                    print(f"   • {provider.name}: {len(models)} models")
            
            print(f"\n💾 Database location: {os.path.abspath('test_saas.db')}")
            print("🔑 SaaS system ready! Users must configure their own API keys.")
            print("\n📝 Note: This is a minimal test database. For full functionality, implement:")
            print("   • User authentication system")
            print("   • UserProviderConfig table with encrypted API keys")
            print("   • Provider configuration endpoints")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Error initializing providers: {e}")
        raise

if __name__ == "__main__":
    init_providers()