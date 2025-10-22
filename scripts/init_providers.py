"""Initialize providers and models in database for SaaS."""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app import create_app
from models import db
from models.provider import Provider, ProviderModel


def init_providers():
    """Initialize default providers and models for SaaS."""
    print("🚀 Initializing providers and models...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # OpenAI Provider
            print("📝 Setting up OpenAI provider...")
            openai_provider = Provider.query.filter_by(name='openai').first()
            if not openai_provider:
                openai_provider = Provider(
                    name='openai',
                    display_name='OpenAI',
                    description='OpenAI API services for transcription and translation',
                    website_url='https://openai.com',
                    documentation_url='https://platform.openai.com/docs'
                )
                db.session.add(openai_provider)
                db.session.flush()  # Get ID
                
                # OpenAI Models
                openai_models = [
                    {
                        'name': 'whisper-1',
                        'display_name': 'Whisper v1',
                        'model_type': 'transcription',
                        'cost_per_unit': 0.006,
                        'cost_unit': 'minute',
                        'max_file_size_mb': 25,
                        'supported_formats': '["mp3", "mp4", "wav", "m4a", "webm"]'
                    },
                    {
                        'name': 'gpt-4o-mini',
                        'display_name': 'GPT-4o Mini',
                        'model_type': 'translation',
                        'cost_per_unit': 0.00015,
                        'cost_unit': 'token'
                    },
                    {
                        'name': 'gpt-4o',
                        'display_name': 'GPT-4o',
                        'model_type': 'translation',
                        'cost_per_unit': 0.005,
                        'cost_unit': 'token'
                    },
                    {
                        'name': 'gpt-3.5-turbo',
                        'display_name': 'GPT-3.5 Turbo',
                        'model_type': 'translation',
                        'cost_per_unit': 0.0015,
                        'cost_unit': 'token'
                    }
                ]
                
                for model_data in openai_models:
                    model = ProviderModel(
                        provider_id=openai_provider.id,
                        **model_data
                    )
                    db.session.add(model)
                
                print("  ✅ OpenAI provider and models created")
            else:
                print("  ℹ️  OpenAI provider already exists")
            
            # Deepgram Provider
            print("📝 Setting up Deepgram provider...")
            deepgram_provider = Provider.query.filter_by(name='deepgram').first()
            if not deepgram_provider:
                deepgram_provider = Provider(
                    name='deepgram',
                    display_name='Deepgram',
                    description='Deepgram Nova-2 transcription with speaker diarization',
                    website_url='https://deepgram.com',
                    documentation_url='https://developers.deepgram.com'
                )
                db.session.add(deepgram_provider)
                db.session.flush()
                
                # Deepgram Models
                deepgram_models = [
                    {
                        'name': 'nova-2',
                        'display_name': 'Nova-2',
                        'model_type': 'transcription',
                        'cost_per_unit': 0.0043,
                        'cost_unit': 'minute',
                        'supported_formats': '["mp3", "mp4", "wav", "flac", "ogg", "m4a", "webm"]'
                    },
                    {
                        'name': 'nova-2-medical',
                        'display_name': 'Nova-2 Medical',
                        'model_type': 'transcription',
                        'cost_per_unit': 0.0059,
                        'cost_unit': 'minute',
                        'supported_formats': '["mp3", "mp4", "wav", "flac", "ogg", "m4a", "webm"]'
                    },
                    {
                        'name': 'nova-2-phonecall',
                        'display_name': 'Nova-2 Phone Call',
                        'model_type': 'transcription',
                        'cost_per_unit': 0.0043,
                        'cost_unit': 'minute',
                        'supported_formats': '["mp3", "wav"]'
                    }
                ]
                
                for model_data in deepgram_models:
                    model = ProviderModel(
                        provider_id=deepgram_provider.id,
                        **model_data
                    )
                    db.session.add(model)
                
                print("  ✅ Deepgram provider and models created")
            else:
                print("  ℹ️  Deepgram provider already exists")
            
            # AssemblyAI Provider
            print("📝 Setting up AssemblyAI provider...")
            assemblyai_provider = Provider.query.filter_by(name='assemblyai').first()
            if not assemblyai_provider:
                assemblyai_provider = Provider(
                    name='assemblyai',
                    display_name='AssemblyAI',
                    description='AssemblyAI transcription with advanced features',
                    website_url='https://www.assemblyai.com',
                    documentation_url='https://www.assemblyai.com/docs'
                )
                db.session.add(assemblyai_provider)
                db.session.flush()
                
                assemblyai_model = ProviderModel(
                    provider_id=assemblyai_provider.id,
                    name='best',
                    display_name='Best Model',
                    model_type='transcription',
                    cost_per_unit=0.00037,
                    cost_unit='second',
                    supported_formats='["mp3", "mp4", "wav", "flac", "ogg", "m4a", "webm"]'
                )
                db.session.add(assemblyai_model)
                
                print("  ✅ AssemblyAI provider and models created")
            else:
                print("  ℹ️  AssemblyAI provider already exists")
            
            # DeepSeek Provider
            print("📝 Setting up DeepSeek provider...")
            deepseek_provider = Provider.query.filter_by(name='deepseek').first()
            if not deepseek_provider:
                deepseek_provider = Provider(
                    name='deepseek',
                    display_name='DeepSeek',
                    description='DeepSeek AI for medical translation (Asian languages)',
                    website_url='https://www.deepseek.com',
                    documentation_url='https://platform.deepseek.com/api-docs'
                )
                db.session.add(deepseek_provider)
                db.session.flush()
                
                deepseek_model = ProviderModel(
                    provider_id=deepseek_provider.id,
                    name='deepseek-chat',
                    display_name='DeepSeek Chat',
                    model_type='translation',
                    cost_per_unit=0.00014,
                    cost_unit='token'
                )
                db.session.add(deepseek_model)
                
                print("  ✅ DeepSeek provider and models created")
            else:
                print("  ℹ️  DeepSeek provider already exists")
            
            # Google Translate Provider (if needed)
            print("📝 Setting up Google Translate provider...")
            google_provider = Provider.query.filter_by(name='google').first()
            if not google_provider:
                google_provider = Provider(
                    name='google',
                    display_name='Google Translate',
                    description='Google Cloud Translation API',
                    website_url='https://cloud.google.com/translate',
                    documentation_url='https://cloud.google.com/translate/docs'
                )
                db.session.add(google_provider)
                db.session.flush()
                
                google_model = ProviderModel(
                    provider_id=google_provider.id,
                    name='translate-v3',
                    display_name='Translation v3',
                    model_type='translation',
                    cost_per_unit=20.0,
                    cost_unit='million_chars'
                )
                db.session.add(google_model)
                
                print("  ✅ Google Translate provider and models created")
            else:
                print("  ℹ️  Google Translate provider already exists")
            
            # Commit all changes
            db.session.commit()
            
            # Print summary
            print("\n📊 Summary:")
            total_providers = Provider.query.filter_by(is_active=True).count()
            total_models = ProviderModel.query.filter_by(is_active=True).count()
            
            print(f"  • Total active providers: {total_providers}")
            print(f"  • Total active models: {total_models}")
            
            print("\n✅ Providers and models initialized successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error initializing providers: {e}")
            raise


if __name__ == '__main__':
    init_providers()