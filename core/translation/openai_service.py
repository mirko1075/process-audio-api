"""OpenAI based translation support."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict

import openai
from openai import AuthenticationError, APIError, RateLimitError

from utils.config import get_app_config
from utils.exceptions import TranslationError


PROMPT_TEMPLATE = (
    "You are an expert medical translator. Translate the following text from {source_language} to {target_language}. "
    "Preserve medical terminology, speaker intent, and maintain professional tone. "
    "Return only the translated text without any additional commentary."
)


class OpenAITranslator:
    def __init__(self) -> None:
        config = get_app_config()
        self._client = openai.OpenAI(api_key=config.openai.api_key)
        self._model = config.openai.model
        self._logger = logging.getLogger(self.__class__.__name__)

    def translate(self, text: str, source_language: str, target_language: str) -> Dict[str, str]:
        if not text.strip():
            raise TranslationError("Text cannot be empty")
        
        self._logger.info("Starting OpenAI translation: %s -> %s (text length: %d)", 
                         source_language, target_language, len(text))
        
        # Handle "auto" source language
        if source_language.lower() == "auto":
            source_language = "the detected language"
        
        prompt = PROMPT_TEMPLATE.format(
            source_language=source_language, 
            target_language=target_language
        )
        
        try:
            self._logger.debug("Sending translation request to OpenAI")
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,  # Low temperature for consistent translations
                max_tokens=4000,  # Sufficient for most translations
            )
            
            translated_text = completion.choices[0].message.content
            
            if not translated_text:
                raise TranslationError("OpenAI returned empty translation")
            
            self._logger.info("Translation completed successfully (output length: %d)", len(translated_text))
            
            return {
                "translated_text": translated_text.strip(),
                "source_language": source_language,
                "target_language": target_language,
                "model_used": self._model
            }
            
        except openai.AuthenticationError as exc:
            self._logger.error("OpenAI authentication error: %s", exc)
            raise TranslationError("OpenAI authentication failed - check API key") from exc
        except openai.RateLimitError as exc:
            self._logger.error("OpenAI rate limit error: %s", exc)
            raise TranslationError("OpenAI rate limit exceeded") from exc
        except openai.APIError as exc:
            self._logger.error("OpenAI API error: %s", exc)
            raise TranslationError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            self._logger.error("Unexpected error during OpenAI translation: %s", exc, exc_info=True)
            raise TranslationError(f"OpenAI translation failed: {str(exc)}") from exc


@lru_cache(maxsize=1)
def get_openai_translator() -> OpenAITranslator:
    return OpenAITranslator()
