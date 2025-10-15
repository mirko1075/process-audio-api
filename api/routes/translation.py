"""Translation routes."""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from api.controllers.translation_controller import (
    translate_with_google,
    translate_with_openai,
)
from utils.auth import require_api_key
from utils.exceptions import TranslationError

translation_bp = Blueprint("translation", __name__)
_logger = logging.getLogger(__name__)


@translation_bp.post("/translations/openai")
@require_api_key
def openai_translation():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text") or request.form.get("text", "")
    source_language = payload.get("source_language") or request.form.get("source_language", "auto")
    target_language = payload.get("target_language") or request.form.get("target_language", "en")

    try:
        result = translate_with_openai(text, source_language, target_language)
    except TranslationError as exc:
        _logger.exception("OpenAI translation failed")
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200


@translation_bp.post("/translations/google")
@require_api_key
def google_translation():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text") or request.form.get("text", "")
    target_language = payload.get("target_language") or request.form.get("target_language", "en")

    try:
        result = translate_with_google(text, target_language)
    except TranslationError as exc:
        _logger.exception("Google translation failed")
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200
