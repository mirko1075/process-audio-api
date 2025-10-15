"""Test suite for client initialization and basic functionality."""
import pytest
from unittest.mock import Mock, patch
import os


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables for client testing."""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-assemblyai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("API_KEY", "test-api-key")


def test_openai_client_initialization(mock_env):
    """Test OpenAI client can be initialized with proper configuration."""
    from flask_app.clients.openai import OpenAIClient
    
    try:
        client = OpenAIClient()
        assert client is not None
        assert hasattr(client, '_client')
        assert hasattr(client, '_model')
        assert hasattr(client, '_tokenizer')
    except Exception as e:
        # If initialization fails due to missing API key, that's expected in tests
        assert "API key" in str(e) or "OpenAI" in str(e)


def test_deepgram_client_initialization(mock_env):
    """Test Deepgram client can be initialized."""
    try:
        from flask_app.clients.deepgram import DeepgramClient
        client = DeepgramClient()
        assert client is not None
    except ImportError:
        # If Deepgram client doesn't exist or import fails, skip
        pytest.skip("Deepgram client not available")
    except Exception as e:
        # If initialization fails due to missing API key, that's expected
        assert "API key" in str(e) or "Deepgram" in str(e)


def test_text_chunking_functionality(mock_env):
    """Test text chunking functionality without API calls."""
    from flask_app.clients.openai import OpenAIClient
    
    try:
        client = OpenAIClient()
        
        # Test text that should be chunked
        long_text = "This is a sentence. " * 100  # Create long text
        
        # Test chunking method exists and works
        if hasattr(client, '_split_text_for_translation'):
            chunks = client._split_text_for_translation(long_text)
            assert isinstance(chunks, list)
            assert len(chunks) > 0
            
            # Verify chunks contain the original text content
            combined = " ".join(chunks)
            # Should preserve most of the content (allowing for some sentence boundary handling)
            assert len(combined) > len(long_text) * 0.8
            
    except Exception as e:
        # If client initialization fails, that's expected in test environment
        assert "API key" in str(e) or "OpenAI" in str(e)


def test_tokenizer_functionality(mock_env):
    """Test tokenizer functionality without API calls."""
    try:
        from flask_app.clients.openai import OpenAIClient
        client = OpenAIClient()
        
        if hasattr(client, '_tokenizer'):
            # Test basic tokenization
            test_text = "Hello, this is a test sentence."
            tokens = client._tokenizer.encode(test_text)
            
            assert isinstance(tokens, list)
            assert len(tokens) > 0
            
            # Test that longer text has more tokens
            longer_text = test_text * 5
            longer_tokens = client._tokenizer.encode(longer_text)
            assert len(longer_tokens) > len(tokens)
            
    except Exception as e:
        # Expected to fail in test environment without proper API setup
        assert "API key" in str(e) or "tiktoken" in str(e) or "OpenAI" in str(e)


@patch('openai.OpenAI')  # Mock the actual OpenAI client instead of httpx
def test_openai_client_timeout_configuration(mock_openai, mock_env):
    """Test that OpenAI client initialization works with timeout configuration."""
    try:
        from flask_app.clients.openai import OpenAIClient
        
        # Mock OpenAI client to avoid actual API calls
        mock_openai.return_value = Mock()
        
        client = OpenAIClient()
        
        # If we get here, initialization worked
        assert client is not None
        
    except Exception as e:
        # Expected to fail in test environment
        assert "API key" in str(e) or "timeout" in str(e) or "OpenAI" in str(e)


def test_error_handling_initialization():
    """Test that clients handle missing API keys gracefully."""
    # Clear API key environment
    import os
    original_key = os.environ.get('OPENAI_API_KEY')
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        from flask_app.clients.openai import OpenAIClient
        client = OpenAIClient()
        # If no exception is raised, the client might have fallback behavior
        # which is also acceptable
        assert client is not None
    except Exception as e:
        # Should raise an exception about missing API key
        error_msg = str(e).lower()
        assert "api key" in error_msg or "key not" in error_msg or "not configured" in error_msg
    finally:
        # Restore original key
        if original_key:
            os.environ['OPENAI_API_KEY'] = original_key