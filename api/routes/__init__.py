"""Blueprint registration helpers."""
from __future__ import annotations

from flask import Flask

from api.routes.health import health_bp
from api.routes.transcription import transcription_bp
from api.routes.translation import translation_bp
from api.routes.postprocessing import postprocessing_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(transcription_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(postprocessing_bp)
