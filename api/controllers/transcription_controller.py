"""Controller helpers for transcription endpoints."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict

from werkzeug.datastructures import FileStorage

from core.transcription.deepgram_service import get_deepgram_transcriber
from core.transcription.openai_whisper_service import get_whisper_transcriber
from core.transcription.assemblyai_service import get_assemblyai_transcriber
from utils.exceptions import TranscriptionError


def transcribe_with_deepgram(file: FileStorage, language: str, model: str | None = None) -> Dict[str, str]:
    file_bytes = file.read()
    if not file_bytes:
        raise TranscriptionError("Uploaded file is empty")
    return get_deepgram_transcriber().transcribe(file_bytes, language=language, model=model)


def transcribe_with_whisper(file: FileStorage, language: str | None = None) -> Dict[str, str]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "audio").suffix) as temp_file:
        file.save(temp_file.name)
        temp_path = Path(temp_file.name)
    try:
        return get_whisper_transcriber().transcribe_file(temp_path, language=language)
    finally:
        temp_path.unlink(missing_ok=True)


def transcribe_with_assemblyai(file: FileStorage, language: str) -> Dict[str, str]:
    transcriber = get_assemblyai_transcriber()
    if not transcriber.enabled:
        raise TranscriptionError("AssemblyAI is not configured")
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "audio").suffix) as temp_file:
        file.save(temp_file.name)
        temp_path = Path(temp_file.name)
    try:
        return transcriber.transcribe(str(temp_path), language)
    finally:
        temp_path.unlink(missing_ok=True)
