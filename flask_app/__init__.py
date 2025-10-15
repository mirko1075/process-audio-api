"""Flask application factory following Flask best practices."""
from flask import Flask
from flask_cors import CORS
import logging
from typing import Optional

from utils.config import get_app_config
from utils.logging import configure_logging


def create_app(config_override: Optional[dict] = None) -> Flask:
    """Create and configure Flask application using application factory pattern.
    
    Args:
        config_override: Optional configuration overrides for testing
        
    Returns:
        Configured Flask application instance
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
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Setup logging
    configure_logging()
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    # Import blueprints here to avoid circular imports
    from flask_app.api.health import bp as health_bp
    from flask_app.api.transcription import bp as transcription_bp
    from flask_app.api.translation import bp as translation_bp
    from flask_app.api.postprocessing import bp as postprocessing_bp
    
    # Register blueprints with appropriate URL prefixes
    app.register_blueprint(health_bp)
    app.register_blueprint(transcription_bp, url_prefix='/transcriptions')
    app.register_blueprint(translation_bp, url_prefix='/translations')
    app.register_blueprint(postprocessing_bp)


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
def get_app() -> Flask:
    """Get configured Flask application instance."""
    return create_app()