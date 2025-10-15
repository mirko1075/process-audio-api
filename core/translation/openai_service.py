"""OpenAI based translation support."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict

import openai

from utils.config import get_app_config
from utils.exceptions import TranslationError


PROMPT_TEMPLATE = (
    "You are an expert medical translator. Translate the text to {target_language} "
    "while preserving medical terminology and speaker intent. Input language is {source_language}."
)


class OpenAITranslator:
    def __init__(self) -> None:
        config = get_app_config()
        self._client = openai.OpenAI(api_key=config.openai.api_key)
        self._model = config.openai.model
        self._logger = logging.getLogger(self.__class__.__name__)

    def translate(self, text: str, source_language: str, target_language: str) -> Dict[str, str]:
        prompt = PROMPT_TEMPLATE.format(
            source_language=source_language, target_language=target_language
        )
        try:
            completion = self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
            )
        except Exception as exc:
            raise TranslationError("OpenAI translation failed") from exc

        output = completion.output_text if hasattr(completion, "output_text") else completion["output_text"]
        self._logger.debug("OpenAI translation completed (%s -> %s)", source_language, target_language)
        return {"translated_text": output}


@lru_cache(maxsize=1)
def get_openai_translator() -> OpenAITranslator:
    return OpenAITranslator()
