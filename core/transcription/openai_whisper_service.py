"""OpenAI Whisper transcription utilities."""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict

import openai

from utils.config import get_app_config
from utils.exceptions import TranscriptionError


class WhisperTranscriber:
    def __init__(self) -> None:
        config = get_app_config()
        self._client = openai.OpenAI(api_key=config.openai.api_key)
        self._logger = logging.getLogger(self.__class__.__name__)

    def transcribe_file(self, file_path: Path, language: str | None = None) -> Dict[str, str]:
        try:
            with file_path.open("rb") as audio_fp:
                response = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_fp,
                    language=language,
                )
        except Exception as exc:
            raise TranscriptionError("Whisper transcription failed") from exc

        text = response.text if hasattr(response, "text") else response["text"]
        self._logger.debug("Whisper transcription completed for %s", file_path)
        return {"transcript": text}


@lru_cache(maxsize=1)
def get_whisper_transcriber() -> WhisperTranscriber:
    return WhisperTranscriber()
