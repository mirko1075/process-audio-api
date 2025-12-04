"""Flask application factory following Flask best practices."""
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
from typing import Optional, Tuple

from utils.config import get_app_config
from utils.logging import configure_logging


def create_app(config_override: Optional[dict] = None) -> Tuple[Flask, SocketIO]:
    """Create and configure Flask application using application factory pattern.

    Args:
        config_override: Optional configuration overrides for testing

    Returns:
        Tuple of (Flask app instance, SocketIO instance)
    """
    app = Flask(__name__)

    # Load configuration
    config = get_app_config()

    # Apply any configuration overrides (useful for testing)
    if config_override:
        for key, value in config_override.items():
            setattr(config, key, value)

    # Store config in app for easy access
    app.config['APP_CONFIG'] = config

    # Configure CORS
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"],
         supports_credentials=True)

    # Setup logging
    configure_logging()

    # Initialize SocketIO with CORS support
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Allow all origins for WebSocket
        async_mode='threading',
        logger=True,
        engineio_logger=False
    )

    # Register blueprints
    register_blueprints(app)

    # Register WebSocket handlers
    register_socketio_handlers(socketio)

    # Register error handlers
    register_error_handlers(app)

    return app, socketio


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    # Import blueprints here to avoid circular imports
    from flask_app.api.health import bp as health_bp
    from flask_app.api.transcription import bp as transcription_bp
    from flask_app.api.translation import bp as translation_bp
    from flask_app.api.postprocessing import bp as postprocessing_bp
    from flask_app.api.utilities import bp as utilities_bp
    from flask_app.api.auth import bp as auth_bp

    # Register blueprints with appropriate URL prefixes
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(transcription_bp, url_prefix='/transcriptions')
    app.register_blueprint(translation_bp, url_prefix='/translations')
    app.register_blueprint(postprocessing_bp)
    app.register_blueprint(utilities_bp, url_prefix='/utilities')


def register_socketio_handlers(socketio: SocketIO) -> None:
    """Register WebSocket event handlers."""
    from flask_app.sockets.audio_stream import init_audio_stream_handlers
    init_audio_stream_handlers(socketio)


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from flask import jsonify
    from werkzeug.exceptions import HTTPException
    from utils.exceptions import TranslationError, TranscriptionError
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized - Invalid or missing API key'}), 401
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(TranscriptionError)
    def handle_transcription_error(error):
        app.logger.error(f"Transcription error: {error}")
        return jsonify({'error': str(error)}), 400
    
    @app.errorhandler(TranslationError)
    def handle_translation_error(error):
        app.logger.error(f"Translation error: {error}")
        return jsonify({'error': str(error)}), 400
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({'error': error.description}), error.code


# For backward compatibility with existing app.py
def get_app() -> Tuple[Flask, SocketIO]:
    """Get configured Flask application and SocketIO instances."""
    return create_app()