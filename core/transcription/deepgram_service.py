"""Deepgram transcription service wrapper."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict

import httpx
from deepgram import DeepgramClient, FileSource, PrerecordedOptions

from utils.config import get_app_config
from utils.exceptions import TranscriptionError


class DeepgramTranscriber:
    def __init__(self) -> None:
        config = get_app_config()
        self._client = DeepgramClient(config.deepgram.api_key)
        self._default_model = config.deepgram.model
        self._default_language = config.deepgram.language
        self._logger = logging.getLogger(self.__class__.__name__)

    def transcribe(self, file_bytes: bytes, language: str | None = None, model: str | None = None) -> Dict[str, Any]:
        options = PrerecordedOptions(
            model=model or self._default_model,
            language=language or self._default_language,
            smart_format=True,
            utterances=True,
            punctuate=True,
            paragraphs=True,
        )
        payload: FileSource = {"buffer": file_bytes}

        timeout = httpx.Timeout(connect=60.0, read=1800.0, write=600.0, pool=60.0)
        self._logger.info("Submitting audio to Deepgram (model=%s, language=%s)", options.model, options.language)
        try:
            response = self._client.listen.prerecorded.v("1").transcribe_file(
                payload, options, timeout=timeout
            )
        except Exception as exc:
            raise TranscriptionError("Deepgram transcription failed") from exc

        return self._format_transcript(response)

    def _format_transcript(self, response: Dict[str, Any]) -> Dict[str, Any]:
        results = response.get("results", {})
        utterances = results.get("utterances", [])

        formatted_lines: list[str] = []
        for utterance in utterances:
            speaker = utterance.get("speaker", "unknown")
            text = utterance.get("transcript", "").strip()
            if text:
                formatted_lines.append(f"Speaker {speaker}: {text}")

        transcript_text = "\n".join(formatted_lines)
        return {
            "raw_response": response,
            "formatted_transcript_array": formatted_lines,
            "transcript": transcript_text,
        }


@lru_cache(maxsize=1)
def get_deepgram_transcriber() -> DeepgramTranscriber:
    return DeepgramTranscriber()
