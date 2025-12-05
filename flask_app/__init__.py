"""Flask application factory following Flask best practices."""
import os
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
    # Since config is frozen, we need to use app.config for Flask settings
    if config_override:
        for key, value in config_override.items():
            app.config[key] = value

    # Store config in app for easy access
    app.config['APP_CONFIG'] = config

    # Database configuration
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/mydb')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Tokens don't expire by default
    app.config['JWT_ALGORITHM'] = 'HS256'

    # Secret key for sessions
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

    # Configure CORS
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"],
         supports_credentials=True)

    # Setup logging
    configure_logging()

    # Initialize database
    init_database(app)

    # Initialize SocketIO with CORS support (for mobile streaming)
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Allow all origins for WebSocket
        async_mode='eventlet',  # Must match gunicorn worker class
        logger=True,
        engineio_logger=False
    )

    # Register blueprints
    register_blueprints(app)

    # Register WebSocket handlers (for mobile streaming)
    register_socketio_handlers(socketio)

    # Register error handlers
    register_error_handlers(app)

    return app, socketio


def init_database(app: Flask) -> None:
    """Initialize database extensions and create tables."""
    try:
        from models import init_db
        init_db(app)

        # Create tables if they don't exist
        with app.app_context():
            from models import db
            db.create_all()

        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
        # In development, continue without database
        if app.debug:
            logging.warning("Continuing without database in debug mode")


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    # Import blueprints here to avoid circular imports
    from flask_app.api.health import bp as health_bp
    from flask_app.api.transcription import bp as transcription_bp
    from flask_app.api.translation import bp as translation_bp
    from flask_app.api.postprocessing import bp as postprocessing_bp
    from flask_app.api.utilities import bp as utilities_bp

    # Try to import web auth blueprint (from main branch)
    try:
        from api.auth import bp as web_auth_bp
        app.register_blueprint(web_auth_bp, url_prefix='/auth', name='web_auth')
        logging.info("Web authentication blueprint registered")
    except ImportError:
        logging.warning("Web authentication blueprint not found, skipping")

    # Try to import mobile auth blueprint (our addition)
    try:
        from flask_app.api.auth import bp as mobile_auth_bp
        # Register with different prefix to avoid conflicts
        app.register_blueprint(mobile_auth_bp, url_prefix='/mobile-auth', name='mobile_auth')
        logging.info("Mobile authentication blueprint registered")
    except ImportError:
        logging.warning("Mobile authentication blueprint not found, skipping")

    # Try to import Auth0 protected routes blueprint
    try:
        from flask_app.api.protected import bp as protected_bp
        app.register_blueprint(protected_bp)
        logging.info("Auth0 protected routes blueprint registered")
    except ImportError:
        logging.warning("Auth0 protected routes blueprint not found, skipping")

    # Register other blueprints with appropriate URL prefixes
    app.register_blueprint(health_bp)
    app.register_blueprint(transcription_bp, url_prefix='/transcriptions')
    app.register_blueprint(translation_bp, url_prefix='/translations')
    app.register_blueprint(postprocessing_bp)
    app.register_blueprint(utilities_bp, url_prefix='/utilities')


def register_socketio_handlers(socketio: SocketIO) -> None:
    """Register WebSocket event handlers."""
    # Try Auth0-enabled WebSocket handlers first (preferred)
    try:
        from flask_app.sockets.audio_stream_auth0 import init_audio_stream_handlers
        init_audio_stream_handlers(socketio)
        logging.info("WebSocket handlers (Auth0-enabled) registered successfully")
        return
    except ImportError as e:
        logging.debug(f"Auth0 WebSocket handlers not found: {e}")

    # Fallback to session-based WebSocket handlers
    try:
        from flask_app.sockets.audio_stream import init_audio_stream_handlers
        init_audio_stream_handlers(socketio)
        logging.info("WebSocket handlers (session-based) registered successfully")
    except ImportError as e:
        logging.warning(f"WebSocket handlers not found: {e}")


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from flask import jsonify
    from werkzeug.exceptions import HTTPException
    from utils.exceptions import TranslationError, TranscriptionError

    # Register Auth0 error handlers
    try:
        from flask_app.auth.auth0 import register_auth_error_handlers
        register_auth_error_handlers(app)
        logging.info("Auth0 error handlers registered")
    except ImportError:
        logging.warning("Auth0 error handlers not found, skipping")

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
