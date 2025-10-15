"""Translation services using Flask best practices."""
import logging
import requests
from typing import Dict, Any, Optional

from flask_app.clients.openai import OpenAIClient
from flask_app.clients.google import GoogleClient
from flask_app.clients.deepseek import DeepSeekClient
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


class DeepSeekTranslationService:
    """Service for DeepSeek translation with external integration support."""
    
    def __init__(self):
        """Initialize the DeepSeek translation service."""
        self.client = DeepSeekClient()
    
    def translate(
        self,
        text: str,
        source_language: str = 'auto',
        target_language: str = 'en',
        file_name: Optional[str] = None,
        duration: Optional[str] = None,
        drive_id: Optional[str] = None,
        group_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        file_id: Optional[str] = None,
        project_name: Optional[str] = None,
        is_dev: str = 'false',
        is_local: str = 'false'
    ) -> Dict[str, Any]:
        """Translate text using DeepSeek with optional external integration.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            file_name: File name for external integrations
            duration: Duration for external integrations
            drive_id: Drive ID for external integrations
            group_id: Group ID for external integrations
            folder_id: Folder ID for external integrations
            file_id: File ID for external integrations
            project_name: Project name for external integrations
            is_dev: Development mode flag
            is_local: Local mode flag
            
        Returns:
            Translation result or external integration confirmation
        """
        try:
            logger.info(f"Starting DeepSeek translation: {source_language} -> {target_language}")
            
            # Perform translation using DeepSeek client
            translated_text = self.client.translate(text, source_language, target_language)
            
            logger.info("DeepSeek translation completed")
            
            # Handle external integration
            if is_local == "true":
                return {'translated_text': translated_text}
            
            # Send to external webhook if not local
            return self._send_to_external_webhook(
                translated_text=translated_text,
                transcription=text,
                file_name=file_name,
                duration=duration,
                drive_id=drive_id,
                group_id=group_id,
                folder_id=folder_id,
                file_id=file_id,
                project_name=project_name,
                is_dev=is_dev
            )
            
        except Exception as e:
            logger.error(f"DeepSeek translation failed: {e}")
            return {'error': f'Translation failed: {str(e)}'}
    
    def _send_to_external_webhook(
        self,
        translated_text: str,
        transcription: str,
        file_name: Optional[str],
        duration: Optional[str],
        drive_id: Optional[str],
        group_id: Optional[str],
        folder_id: Optional[str],
        file_id: Optional[str],
        project_name: Optional[str],
        is_dev: str
    ) -> Dict[str, Any]:
        """Send translation results to external webhook."""
        try:
            # Determine webhook URL based on environment
            if is_dev == "true":
                url = "https://hook.eu2.make.com/62p3xl6a7nnr14y89i6av1bxapyvxpxn"
            else:
                url = "https://hook.eu2.make.com/xjxlm9ehhdn16mhtfnp77sxpgidvagqe"
            
            logger.info(f"Sending DeepSeek translation to webhook: {url}")
            
            # Prepare data for webhook
            data = {
                "translation": translated_text,
                "transcription": transcription,
                "fileName": file_name,
                "duration": duration,
                "driveId": drive_id,
                "groupId": group_id,
                "folderId": folder_id,
                "fileId": file_id,
                "projectName": project_name
            }
            
            # Send to webhook
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Webhook request failed: {response.status_code} - {response.text}")
                return {'error': 'Failed to send request to external service'}
            
            logger.info("Successfully sent translation to external webhook")
            return {'message': 'Request sent to external service'}
            
        except requests.RequestException as e:
            logger.error(f"Webhook request error: {e}")
            return {'error': 'Failed to communicate with external service'}
        except Exception as e:
            logger.error(f"Unexpected error in webhook integration: {e}")
            return {'error': 'External integration failed'}