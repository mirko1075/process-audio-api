"""Pytest configuration and fixtures."""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables for all tests."""
    test_env_vars = {
        "SECRET_KEY": "test-secret-key-for-testing",
        "API_KEY": "test-api-key",
        "DEEPGRAM_API_KEY": "test-deepgram-key",
        "OPENAI_API_KEY": "test-openai-key",
        "ASSEMBLYAI_API_KEY": "test-assemblyai-key",
        "DEEPSEEK_API_KEY": "test-deepseek-key",
        "FLASK_ENV": "testing",
        "DATABASE_URL": "sqlite:///:memory:",  # Use in-memory SQLite for tests
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Clean up environment variables after tests
    for key in test_env_vars:
        os.environ.pop(key, None)


@pytest.fixture(scope="session")
def mock_database():
    """Mock database for tests that don't need real database connections."""
    # This fixture can be expanded if needed for database-dependent tests
    pass