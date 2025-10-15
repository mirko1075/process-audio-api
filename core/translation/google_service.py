"""Google Cloud translation wrapper."""
from __future__ import annotations

from typing import Dict

from google.cloud import translate_v2 as translate

from utils.config import get_app_config
from utils.exceptions import TranslationError


class GoogleTranslator:
    def __init__(self) -> None:
        config = get_app_config()
        if config.google_cloud is None:
            raise TranslationError("Google Cloud credentials not configured")
        self._client = translate.Client()

    def translate(self, text: str, target_language: str) -> Dict[str, str]:
        try:
            result = self._client.translate(text, target_language=target_language)
        except Exception as exc:  # pragma: no cover - upstream errors
            raise TranslationError("Google translation failed") from exc

        return {"translated_text": result["translatedText"]}
