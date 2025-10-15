"""AssemblyAI transcription integration."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict

import assemblyai as aai

from utils.config import get_app_config
from utils.exceptions import TranscriptionError


class AssemblyAITranscriber:
    def __init__(self) -> None:
        config = get_app_config()
        self._logger = logging.getLogger(self.__class__.__name__)
        self.enabled = config.assemblyai is not None
        if config.assemblyai:
            aai.settings.api_key = config.assemblyai.api_key

    def transcribe(self, file_path: str, language: str) -> Dict[str, str]:
        if not self.enabled:
            raise TranscriptionError("AssemblyAI integration is not configured")

        config = aai.TranscriptionConfig(
            language_code=language,
            speech_model=aai.SpeechModel.best,
            speaker_labels=True,
        )
        try:
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(file_path, config)
        except Exception as exc:
            raise TranscriptionError("AssemblyAI transcription failed") from exc

        if transcript.status == aai.TranscriptStatus.error:
            raise TranscriptionError(transcript.error or "AssemblyAI reported an error")

        utterances = getattr(transcript, "utterances", [])
        formatted = [f"speaker{utt.speaker}: {utt.text}" for utt in utterances]
        return {
            "formatted_transcript_array": formatted,
            "transcript": "\n".join(formatted) if formatted else transcript.text,
        }


@lru_cache(maxsize=1)
def get_assemblyai_transcriber() -> AssemblyAITranscriber:
    return AssemblyAITranscriber()
