"""Translation controller functions."""
from __future__ import annotations

from typing import Dict

from core.translation.openai_service import get_openai_translator
from utils.exceptions import TranslationError

try:
    from core.translation.google_service import GoogleTranslator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    GoogleTranslator = None


def translate_with_openai(text: str, source_language: str, target_language: str) -> Dict[str, str]:
    if not text:
        raise TranslationError("Text cannot be empty")
    return get_openai_translator().translate(text, source_language, target_language)


def translate_with_google(text: str, target_language: str) -> Dict[str, str]:
    if GoogleTranslator is None:
        raise TranslationError("Google translation is not available")
    translator = GoogleTranslator()
    return translator.translate(text, target_language)
