"""Application factory for the AI transcription backend."""
from __future__ import annotations

from flask import Flask

from api.routes import register_blueprints
from utils.config import get_app_config
from utils.logging import configure_logging


def create_app() -> Flask:
    configure_logging()
    app = Flask(__name__)
    register_blueprints(app)
    config = get_app_config()

    @app.after_request
    def _apply_cors_headers(response):  # type: ignore[override]
        origin = config.allowed_origins[0]
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Access-Control-Allow-Headers", "*")
        response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        return response

    return app
