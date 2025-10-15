"""Translation services for various AI providers."""
import logging
from typing import Dict, Any

from flask_app.clients.openai import OpenAIClient
from flask_app.clients.google import GoogleClient
from utils.exceptions import TranslationError


logger = logging.getLogger(__name__)


class TranslationService:
    """Base translation service with common functionality."""
    pass


class OpenAITranslationService(TranslationService):
    """Service for OpenAI GPT-based translation with automatic text chunking."""
    
    def __init__(self):
        self.client = OpenAIClient()
        logger.info("OpenAI translation service initialized")
    
    def translate(self, text: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Translate text using OpenAI GPT with automatic chunking for long texts.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Translation result with chunking metadata if applicable
        """
        logger.info(f"Starting OpenAI translation: {source_language} -> {target_language}")
        
        if not text.strip():
            raise TranslationError("Text cannot be empty")
        
        try:
            result = self.client.translate_text(text, source_language, target_language)
            logger.info("OpenAI translation completed successfully")
            return result
            
        except Exception as exc:
            logger.error(f"OpenAI translation failed: {exc}")
            raise TranslationError(f"OpenAI translation failed: {str(exc)}") from exc


class GoogleTranslationService(TranslationService):
    """Service for Google Cloud Translation API."""
    
    def __init__(self):
        self.client = GoogleClient()
        logger.info("Google translation service initialized")
    
    def translate(self, text: str, target_language: str) -> Dict[str, Any]:
        """Translate text using Google Cloud Translation API.
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            Translation result
        """
        logger.info(f"Starting Google translation to {target_language}")
        
        if not text.strip():
            raise TranslationError("Text cannot be empty")
        
        try:
            result = self.client.translate_text(text, target_language)
            logger.info("Google translation completed successfully")
            return result
            
        except Exception as exc:
            logger.error(f"Google translation failed: {exc}")
            raise TranslationError(f"Google translation failed: {str(exc)}") from exc