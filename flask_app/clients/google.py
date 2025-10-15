"""Google Cloud API client for translation services."""
import logging
from typing import Dict, Any
from functools import lru_cache

from google.api_core import exceptions as gcp_exceptions
from google.cloud import translate_v2 as translate

from utils.config import get_app_config
from utils.exceptions import TranslationError


logger = logging.getLogger(__name__)


class GoogleClient:
    """Client for Google Cloud Translation API."""
    
    def __init__(self):
        config = get_app_config()
        if not config.google_cloud:
            raise TranslationError("Google Cloud credentials not configured")
            
        try:
            self._client = translate.Client()
            logger.info("Google Cloud Translation client initialized successfully")
        except Exception as exc:
            logger.error(f"Failed to initialize Google Cloud Translation client: {exc}")
            raise TranslationError("Failed to initialize Google Cloud Translation client") from exc
    
    def translate_text(self, text: str, target_language: str) -> Dict[str, Any]:
        """Translate text using Google Cloud Translation API.
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            Formatted translation result
        """
        logger.info(f"Starting Google Cloud translation to {target_language} (text length: {len(text)})")
        
        try:
            result = self._client.translate(text, target_language=target_language)
            
            if not result or "translatedText" not in result:
                raise TranslationError("Google Cloud returned invalid response")
                
            translated_text = result["translatedText"]
            
            logger.info(f"Google translation completed successfully (output length: {len(translated_text)})")
            
            return {
                "translated_text": translated_text,
                "source_language": result.get("detectedSourceLanguage", "auto"),
                "target_language": target_language,
                "service": "google_cloud"
            }
            
        except gcp_exceptions.Forbidden as exc:
            logger.error(f"Google Cloud Translation API access forbidden: {exc}")
            if "SERVICE_DISABLED" in str(exc):
                raise TranslationError(
                    "Google Cloud Translation API is not enabled for this project. "
                    "Please enable it in the Google Cloud Console and try again."
                ) from exc
            else:
                raise TranslationError(
                    "Access denied to Google Cloud Translation API. "
                    "Please check your credentials and permissions."
                ) from exc
                
        except gcp_exceptions.Unauthenticated as exc:
            logger.error(f"Google Cloud authentication failed: {exc}")
            raise TranslationError(
                "Google Cloud authentication failed. "
                "Please check your service account credentials."
            ) from exc
            
        except gcp_exceptions.BadRequest as exc:
            logger.error(f"Google Cloud Translation bad request: {exc}")
            raise TranslationError(f"Invalid translation request: {str(exc)}") from exc
            
        except gcp_exceptions.QuotaExceeded as exc:
            logger.error(f"Google Cloud Translation quota exceeded: {exc}")
            raise TranslationError(
                "Google Cloud Translation quota exceeded. "
                "Please check your usage limits."
            ) from exc
            
        except Exception as exc:
            logger.error(f"Unexpected error during Google translation: {exc}")
            raise TranslationError(f"Google translation failed: {str(exc)}") from exc


@lru_cache(maxsize=1)
def get_google_client() -> GoogleClient:
    """Get cached Google client instance."""
    return GoogleClient()