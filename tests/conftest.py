"""Pytest configuration and fixtures for tests."""
import pytest
import os


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment(monkeypatch_session):
    """Set up required environment variables for all tests."""
    # Use monkeypatch_session to set env vars for entire test session
    monkeypatch_session.setenv('JWT_SECRET_KEY', 'test-jwt-secret-key-for-testing-only')
    monkeypatch_session.setenv('SECRET_KEY', 'test-secret-key-for-testing-only')
    monkeypatch_session.setenv('SOCKETIO_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
    monkeypatch_session.setenv('AUTH0_DOMAIN', 'test.auth0.com')
    monkeypatch_session.setenv('AUTH0_AUDIENCE', 'https://test.api.com')
    monkeypatch_session.setenv('DEEPGRAM_API_KEY', 'test-deepgram-key')
    monkeypatch_session.setenv('OPENAI_API_KEY', 'test-openai-key')
    monkeypatch_session.setenv('DATABASE_URL', 'sqlite:///:memory:')


@pytest.fixture(scope='session')
def monkeypatch_session():
    """Session-scoped monkeypatch fixture."""
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    from core import create_app
    from models import db

    app, socketio = create_app()

    # Configure for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Create database tables
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()
