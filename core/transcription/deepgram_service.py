"""Deepgram transcription service wrapper."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Union

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
            self._logger.info("Deepgram response received, type: %s", type(response).__name__)
            return self._format_transcript(response)
        except Exception as exc:
            self._logger.error("Deepgram transcription failed: %s", str(exc))
            raise TranscriptionError("Deepgram transcription failed") from exc

    def _format_transcript(self, response: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        self._logger.debug("Formatting response of type: %s", type(response).__name__)
        
        # Handle both PrerecordedResponse object and dict formats
        if hasattr(response, 'results'):
            # New SDK format - response is a PrerecordedResponse object
            self._logger.debug("Using new SDK format (PrerecordedResponse)")
            results = response.results
            utterances = getattr(results, 'utterances', []) if results else []
            
            # Convert response to dict for raw_response
            try:
                raw_response = response.to_dict() if hasattr(response, 'to_dict') else str(response)
            except Exception as e:
                self._logger.warning("Could not convert response to dict: %s", e)
                raw_response = {"error": "Could not serialize response"}
        else:
            # Legacy format - response is already a dict
            self._logger.debug("Using legacy format (dict)")
            results = response.get("results", {})
            utterances = results.get("utterances", [])
            raw_response = response

        formatted_lines: list[str] = []
        
        if utterances:
            self._logger.debug("Processing %d utterances", len(utterances))
            # Handle utterances format
            for utterance in utterances:
                if hasattr(utterance, 'speaker'):
                    speaker = utterance.speaker
                    text = utterance.transcript.strip() if hasattr(utterance, 'transcript') else ""
                else:
                    # Dict format
                    speaker = utterance.get("speaker", "unknown")
                    text = utterance.get("transcript", "").strip()
                    
                if text:
                    formatted_lines.append(f"Speaker {speaker}: {text}")
        else:
            # Fallback to channels format if no utterances
            self._logger.debug("No utterances found, trying channels format")
            channels = getattr(results, 'channels', []) if hasattr(results, 'channels') else results.get("channels", [])
            
            for channel in channels:
                alternatives = getattr(channel, 'alternatives', []) if hasattr(channel, 'alternatives') else channel.get("alternatives", [])
                for alternative in alternatives:
                    transcript = getattr(alternative, 'transcript', '') if hasattr(alternative, 'transcript') else alternative.get("transcript", "")
                    if transcript.strip():
                        formatted_lines.append(transcript.strip())

        transcript_text = "\n".join(formatted_lines)
        self._logger.debug("Generated transcript with %d lines", len(formatted_lines))
        
        return {
            "raw_response": raw_response,
            "formatted_transcript_array": formatted_lines,
            "transcript": transcript_text,
        }


@lru_cache(maxsize=1)
def get_deepgram_transcriber() -> DeepgramTranscriber:
    return DeepgramTranscriber()
