"""Post-processing routes (sentiment, reporting, documents)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file

from core.postprocessing.docx_generator import create_word_document
from core.postprocessing.excel_generator import build_workbook
from core.postprocessing.sentiment import run_sentiment_analysis
from utils.auth import require_api_key

postprocessing_bp = Blueprint("postprocessing", __name__)


@postprocessing_bp.post("/sentiment")
@require_api_key
def sentiment():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text") or request.form.get("text")
    if not text:
        return jsonify({"error": "Missing text"}), 400

    return jsonify(run_sentiment_analysis(text)), 200


@postprocessing_bp.post("/documents/word")
@require_api_key
def generate_word_document():
    content = request.form.get("text", "")
    filename = request.form.get("fileName", "report.docx")
    path = create_word_document(content, filename)
    return send_file(path, as_attachment=True)


@postprocessing_bp.post("/reports/excel")
@require_api_key
def generate_excel_report():
    payload = request.get_json(force=True, silent=True)
    if not payload or "sheets" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    workbook = build_workbook(payload["sheets"])
    return send_file(
        workbook,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="analysis.xlsx",
    )
