"""Updated transcription services using user's API keys - SaaS model."""

import logging
import tempfile
import os
from typing import Dict, Any
from werkzeug.datastructures import FileStorage
from flask import g

from flask_app.clients.deepgram import DeepgramClient
from flask_app.clients.openai import OpenAIClient
from services.user_provider import user_provider_service
from utils.exceptions import TranscriptionError, ConfigurationError

logger = logging.getLogger(__name__)


class BaseTranscriptionService:
    """Base class for transcription services in SaaS environment."""
    
    def save_temp_file(self, audio_file: FileStorage) -> str:
        """Save uploaded file to temporary location."""
        temp_fd, temp_path = tempfile.mkstemp(suffix=f".{audio_file.filename.split('.')[-1]}")
        try:
            with os.fdopen(temp_fd, 'wb') as temp_file:
                audio_file.save(temp_file)
            return temp_path
        except Exception:
            os.close(temp_fd)
            raise
    
    def cleanup_temp_file(self, temp_path: str):
        """Clean up temporary file."""
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")


class DeepgramService(BaseTranscriptionService):
    """Deepgram transcription service using user's API key - SaaS model."""
    
    def __init__(self):
        logger.info("Deepgram transcription service initialized for SaaS")
    
    def transcribe(self, audio_file: FileStorage, language: str = 'en', 
                  model: str = 'nova-2', diarize: bool = False, 
                  punctuate: bool = True, paragraphs: bool = False) -> Dict[str, Any]:
        """
        Transcribe using user's Deepgram API key.
        
        Args:
            audio_file: Uploaded audio file
            language: Language code
            model: Deepgram model to use
            diarize: Enable speaker diarization
            punctuate: Enable punctuation
            paragraphs: Enable paragraph detection
            
        Returns:
            Transcription result
            
        Raises:
            ConfigurationError: If user hasn't configured Deepgram API key
            TranscriptionError: If transcription fails
        """
        # Get user's API key - REQUIRED in SaaS mode
        user_api_key = user_provider_service.require_user_api_key(
            g.current_user.id, 'deepgram'
        )
        
        # Get user's preferred model if not specified
        if model == 'nova-2':  # default
            user_model = user_provider_service.get_user_model_preference(
                g.current_user.id, 'deepgram'
            )
            if user_model:
                model = user_model
        
        temp_path = None
        try:
            temp_path = self.save_temp_file(audio_file)
            
            # Read audio data
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Initialize client with user's API key
            client = DeepgramClient(api_key=user_api_key)
            result = client.transcribe(
                audio_data, 
                language=language,
                model=model,
                diarize=diarize,
                punctuate=punctuate,
                paragraphs=paragraphs
            )
            
            # Update usage statistics
            duration_minutes = result.get('duration_seconds', 0) / 60.0
            cost_usd = self._calculate_cost(duration_minutes, model)
            
            user_provider_service.update_usage_stats(
                g.current_user.id, 'deepgram',
                cost_usd=cost_usd,
                audio_minutes=duration_minutes
            )
            
            logger.info(f"Deepgram transcription completed for user {g.current_user.id}, "
                       f"duration: {duration_minutes:.1f}min, cost: ${cost_usd:.4f}")
            return result
            
        finally:
            if temp_path:
                self.cleanup_temp_file(temp_path)
    
    def _calculate_cost(self, duration_minutes: float, model: str) -> float:
        """Calculate estimated cost for Deepgram transcription."""
        # Deepgram Nova-2 pricing: $0.0043 per minute
        base_rate = 0.0043
        if 'medical' in model.lower():
            base_rate = 0.0059
        
        return duration_minutes * base_rate


class WhisperService(BaseTranscriptionService):
    """OpenAI Whisper transcription service using user's API key - SaaS model."""
    
    def __init__(self):
        logger.info("Whisper transcription service initialized for SaaS")
    
    def transcribe(self, audio_file: FileStorage, language: str = 'en') -> Dict[str, Any]:
        """
        Transcribe using user's OpenAI API key.
        
        Args:
            audio_file: Uploaded audio file
            language: Language code
            
        Returns:
            Transcription result
            
        Raises:
            ConfigurationError: If user hasn't configured OpenAI API key
            TranscriptionError: If transcription fails
        """
        # Get user's API key - REQUIRED in SaaS mode
        user_api_key = user_provider_service.require_user_api_key(
            g.current_user.id, 'openai'
        )
        
        temp_path = None
        try:
            temp_path = self.save_temp_file(audio_file)
            
            # Initialize client with user's API key
            client = OpenAIClient(api_key=user_api_key)
            result = client.transcribe_with_chunking(temp_path, language=language)
            
            # Update usage statistics
            duration_minutes = result.get('duration', 0) / 60.0 if 'duration' in result else 0
            cost_usd = self._calculate_cost(duration_minutes)
            
            user_provider_service.update_usage_stats(
                g.current_user.id, 'openai',
                cost_usd=cost_usd,
                audio_minutes=duration_minutes
            )
            
            logger.info(f"Whisper transcription completed for user {g.current_user.id}, "
                       f"duration: {duration_minutes:.1f}min, cost: ${cost_usd:.4f}")
            return result
            
        finally:
            if temp_path:
                self.cleanup_temp_file(temp_path)
    
    def _calculate_cost(self, duration_minutes: float) -> float:
        """Calculate estimated cost for Whisper transcription."""
        # OpenAI Whisper pricing: $0.006 per minute
        return duration_minutes * 0.006


class AssemblyAIService(BaseTranscriptionService):
    """AssemblyAI transcription service using user's API key - SaaS model."""
    
    def __init__(self):
        logger.info("AssemblyAI transcription service initialized for SaaS")
    
    def transcribe(self, audio_file: FileStorage, language: str = 'en') -> Dict[str, Any]:
        """
        Transcribe using user's AssemblyAI API key.
        
        Args:
            audio_file: Uploaded audio file
            language: Language code
            
        Returns:
            Transcription result
            
        Raises:
            ConfigurationError: If user hasn't configured AssemblyAI API key
            TranscriptionError: If transcription fails
        """
        # Get user's API key - REQUIRED in SaaS mode
        user_api_key = user_provider_service.require_user_api_key(
            g.current_user.id, 'assemblyai'
        )
        
        # For now, return a placeholder implementation
        # You would implement the actual AssemblyAI client similar to Deepgram
        raise TranscriptionError("AssemblyAI service implementation pending")
    
    def _calculate_cost(self, duration_seconds: float) -> float:
        """Calculate estimated cost for AssemblyAI transcription."""
        # AssemblyAI pricing: $0.00037 per second
        return duration_seconds * 0.00037


class TranslationService:
    """Translation service using user's API keys - SaaS model."""
    
    def translate_openai(self, text: str, source_language: str = 'auto', 
                        target_language: str = 'en') -> Dict[str, Any]:
        """
        Translate text using user's OpenAI API key.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Translation result
            
        Raises:
            ConfigurationError: If user hasn't configured OpenAI API key
        """
        # Get user's API key - REQUIRED in SaaS mode
        user_api_key = user_provider_service.require_user_api_key(
            g.current_user.id, 'openai'
        )
        
        # Get user's preferred model
        model = user_provider_service.get_user_model_preference(
            g.current_user.id, 'openai'
        ) or 'gpt-4o-mini'
        
        try:
            client = OpenAIClient(api_key=user_api_key, model=model)
            result = client.translate_text(text, source_language, target_language)
            
            # Update usage statistics (approximate token count)
            estimated_tokens = len(text) // 4  # Rough estimate
            cost_usd = self._calculate_translation_cost(estimated_tokens, model)
            
            user_provider_service.update_usage_stats(
                g.current_user.id, 'openai',
                cost_usd=cost_usd,
                tokens=estimated_tokens
            )
            
            logger.info(f"OpenAI translation completed for user {g.current_user.id}, "
                       f"tokens: {estimated_tokens}, cost: ${cost_usd:.4f}")
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise TranscriptionError(f"Translation failed: {str(e)}")
    
    def _calculate_translation_cost(self, tokens: int, model: str) -> float:
        """Calculate estimated cost for translation."""
        # Pricing per 1000 tokens
        if model == 'gpt-4o':
            rate = 0.005
        elif model == 'gpt-4o-mini':
            rate = 0.00015
        else:
            rate = 0.001  # default
        
        return (tokens / 1000) * rate