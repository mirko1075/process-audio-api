"""Google Cloud translation wrapper with enhanced error handling."""
from __future__ import annotations

import logging
from typing import Dict

from google.api_core import exceptions as gcp_exceptions
from google.cloud import translate_v2 as translate

from utils.config import get_app_config
from utils.exceptions import TranslationError


class GoogleTranslator:
    def __init__(self) -> None:
        config = get_app_config()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        if config.google_cloud is None:
            raise TranslationError("Google Cloud credentials not configured")
            
        try:
            self._client = translate.Client()
            self._logger.info("Google Cloud Translation client initialized successfully")
        except Exception as exc:
            self._logger.error("Failed to initialize Google Cloud Translation client: %s", exc)
            raise TranslationError("Failed to initialize Google Cloud Translation client") from exc

    def translate(self, text: str, target_language: str) -> Dict[str, str]:
        if not text.strip():
            raise TranslationError("Text cannot be empty")
            
        self._logger.info("Starting Google Cloud translation to %s (text length: %d)", 
                         target_language, len(text))
        
        try:
            result = self._client.translate(text, target_language=target_language)
            
            if not result or "translatedText" not in result:
                raise TranslationError("Google Cloud returned invalid response")
                
            translated_text = result["translatedText"]
            self._logger.info("Google translation completed successfully (output length: %d)", 
                            len(translated_text))
            
            return {
                "translated_text": translated_text,
                "source_language": result.get("detectedSourceLanguage", "auto"),
                "target_language": target_language,
                "service": "google_cloud"
            }
            
        except gcp_exceptions.Forbidden as exc:
            self._logger.error("Google Cloud Translation API access forbidden: %s", exc)
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
            self._logger.error("Google Cloud authentication failed: %s", exc)
            raise TranslationError(
                "Google Cloud authentication failed. "
                "Please check your service account credentials."
            ) from exc
            
        except gcp_exceptions.BadRequest as exc:
            self._logger.error("Google Cloud Translation bad request: %s", exc)
            raise TranslationError(
                f"Invalid translation request: {str(exc)}"
            ) from exc
            
        except gcp_exceptions.QuotaExceeded as exc:
            self._logger.error("Google Cloud Translation quota exceeded: %s", exc)
            raise TranslationError(
                "Google Cloud Translation quota exceeded. "
                "Please check your usage limits."
            ) from exc
            
        except Exception as exc:
            self._logger.error("Unexpected error during Google translation: %s", exc, exc_info=True)
            raise TranslationError(f"Google translation failed: {str(exc)}") from exc
