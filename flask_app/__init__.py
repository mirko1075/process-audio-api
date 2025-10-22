"""Flask application factory following Flask best practices."""
import os
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
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Setup logging
    configure_logging()
    
    # Initialize database
    init_database(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

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
    from api.auth import bp as auth_bp  # Authentication endpoints
    from api.user_config import bp as user_config_bp  # User provider configuration
    
    # Register blueprints with appropriate URL prefixes
    app.register_blueprint(health_bp)
    app.register_blueprint(transcription_bp, url_prefix='/transcriptions')
    app.register_blueprint(translation_bp, url_prefix='/translations')
    app.register_blueprint(postprocessing_bp)
    app.register_blueprint(utilities_bp, url_prefix='/utilities')
    app.register_blueprint(auth_bp, url_prefix='/auth')  # Auth endpoints
    app.register_blueprint(user_config_bp)  # User config endpoints (already has /user-config prefix)


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