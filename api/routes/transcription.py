"""Transcription related routes."""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from api.controllers.transcription_controller import (
    transcribe_with_assemblyai,
    transcribe_with_deepgram,
    transcribe_with_whisper,
)
from utils.auth import require_api_key
from utils.exceptions import TranscriptionError

transcription_bp = Blueprint("transcription", __name__)
_logger = logging.getLogger(__name__)


@transcription_bp.post("/transcriptions/deepgram")
@require_api_key
def deepgram_transcription():
    audio_file = request.files.get("audio")
    language = request.form.get("language", "en")
    model = request.form.get("model")
    if not audio_file:
        return jsonify({"error": "No audio file uploaded"}), 400

    try:
        result = transcribe_with_deepgram(audio_file, language, model)
    except TranscriptionError as exc:
        _logger.exception("Deepgram transcription failed")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result), 200


@transcription_bp.post("/transcriptions/whisper")
@require_api_key
def whisper_transcription():
    audio_file = request.files.get("audio")
    language = request.form.get("language")
    if not audio_file:
        return jsonify({"error": "No audio file uploaded"}), 400

    try:
        result = transcribe_with_whisper(audio_file, language)
    except TranscriptionError as exc:
        _logger.exception("Whisper transcription failed")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result), 200


@transcription_bp.post("/transcriptions/assemblyai")
@require_api_key
def assemblyai_transcription():
    audio_file = request.files.get("audio")
    language = request.form.get("language", "en")
    if not audio_file:
        return jsonify({"error": "No audio file uploaded"}), 400

    try:
        result = transcribe_with_assemblyai(audio_file, language)
    except TranscriptionError as exc:
        _logger.exception("AssemblyAI transcription failed")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result), 200
