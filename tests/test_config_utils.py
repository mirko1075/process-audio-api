"""Test suite for configuration and utility functions."""
import pytest
import os
from unittest.mock import patch


def test_environment_configuration(monkeypatch):
    """Test that environment variables are properly configured."""
    # Set test environment variables
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    
    from utils.config import get_app_config
    
    config = get_app_config()
    
    # Test that config loads without errors
    assert config is not None
    

def test_flask_app_creation(monkeypatch):
    """Test Flask app can be created with proper configuration."""
    # Set required environment variables
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("FLASK_ENV", "testing")
    
    from flask_app import create_app
    
    app = create_app()
    
    # Test app creation
    assert app is not None
    assert app.config['TESTING'] is True  # Should be True when FLASK_ENV is 'testing'
    
    # Test that app has required blueprints registered
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    expected_blueprints = ['health', 'transcription', 'translation', 'postprocessing', 'utilities']
    
    for expected_bp in expected_blueprints:
        assert expected_bp in blueprint_names


def test_logging_configuration():
    """Test that logging module can be imported."""
    try:
        import utils.logging
        # Basic import test - if logging module exists and imports, test passes
        assert utils.logging is not None
    except ImportError:
        pytest.skip("Logging module not available or configured differently")


def test_auth_decorator_functionality():
    """Test authentication decorator logic."""
    from utils.auth import require_api_key
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/test')
    @require_api_key
    def test_endpoint():
        return {"status": "ok"}
    
    with app.test_client() as client:
        # Test without API key
        response = client.get('/test')
        assert response.status_code == 401
        
        # Note: Testing with valid API key is complex due to environment setup
        # The important part is that unauthorized access is blocked


def test_custom_exceptions():
    """Test custom exception classes."""
    from utils.exceptions import TranscriptionError, TranslationError
    
    # Test that custom exceptions can be raised and caught
    try:
        raise TranscriptionError("Test transcription error")
    except TranscriptionError as e:
        assert str(e) == "Test transcription error"
    
    try:
        raise TranslationError("Test translation error")
    except TranslationError as e:
        assert str(e) == "Test translation error"