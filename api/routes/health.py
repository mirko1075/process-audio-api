"""Health check endpoint."""
from __future__ import annotations

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def healthcheck():
    """Return a simple health payload used by orchestrators."""
    return jsonify({"status": "ok"}), 200
