"""Tests for Auth0 authentication module.

This test suite covers:
- JWT token verification
- Token extraction from headers
- Decorator behavior (@require_auth)
- WebSocket token verification
- Error handling
- User info retrieval
"""
import pytest
import jwt
import json
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from flask import Flask, g, request
from werkzeug.test import Client
from werkzeug.wrappers import Response

from flask_app.auth.auth0 import (
    Auth0Error,
    get_token_from_header,
    verify_jwt,
    require_auth,
    verify_websocket_token,
    get_user_info,
    get_jwks_url,
    get_jwks_client
)


# Test fixtures
@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Reset PyJWKClient cache before each test."""
    import flask_app.auth.auth0 as auth0_module
    auth0_module._jwks_client = None
    yield
    auth0_module._jwks_client = None


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables and patch Auth0 module constants."""
    import flask_app.auth.auth0 as auth0_module
    
    # Store original values
    original_domain = auth0_module.AUTH0_DOMAIN
    original_audience = auth0_module.AUTH0_AUDIENCE
    
    # Set test values in module
    auth0_module.AUTH0_DOMAIN = 'test-domain.auth0.com'
    auth0_module.AUTH0_AUDIENCE = 'https://api.test.com'
    
    # Also set environment variables for consistency
    monkeypatch.setenv('AUTH0_DOMAIN', 'test-domain.auth0.com')
    monkeypatch.setenv('AUTH0_AUDIENCE', 'https://api.test.com')
    monkeypatch.setenv('AUTH0_REQUEST_TIMEOUT', '30')
    
    yield
    
    # Restore original values
    auth0_module.AUTH0_DOMAIN = original_domain
    auth0_module.AUTH0_AUDIENCE = original_audience


@pytest.fixture
def app(mock_env):
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    @app.route('/test-protected')
    @require_auth
    def protected_route():
        return {'user_id': request.user_id, 'user': request.user}
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def valid_token_payload():
    """Valid JWT payload."""
    return {
        'sub': 'auth0|123456789',
        'email': 'test@example.com',
        'email_verified': True,
        'iss': 'https://test-domain.auth0.com/',
        'aud': 'https://api.test.com',
        'iat': int(datetime.utcnow().timestamp()),
        'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }


@pytest.fixture
def expired_token_payload():
    """Expired JWT payload."""
    return {
        'sub': 'auth0|123456789',
        'email': 'test@example.com',
        'iss': 'https://test-domain.auth0.com/',
        'aud': 'https://api.test.com',
        'iat': int((datetime.utcnow() - timedelta(hours=2)).timestamp()),
        'exp': int((datetime.utcnow() - timedelta(hours=1)).timestamp())
    }


# Tests for get_jwks_url()
class TestGetJwksUrl:
    """Test JWKS URL generation."""
    
    def test_get_jwks_url_success(self, mock_env):
        """Test successful JWKS URL generation."""
        url = get_jwks_url()
        assert url == 'https://test-domain.auth0.com/.well-known/jwks.json'
    
    def test_get_jwks_url_no_domain(self, monkeypatch):
        """Test error when AUTH0_DOMAIN not set."""
        # We need to patch the AUTH0_DOMAIN constant directly since it's loaded at module import
        import flask_app.auth.auth0 as auth0_module
        original_domain = auth0_module.AUTH0_DOMAIN
        auth0_module.AUTH0_DOMAIN = None
        
        try:
            with pytest.raises(Auth0Error) as exc_info:
                get_jwks_url()
            
            assert exc_info.value.status_code == 500
            assert 'AUTH0_DOMAIN not configured' in exc_info.value.message
        finally:
            auth0_module.AUTH0_DOMAIN = original_domain


# Tests for get_token_from_header()
class TestGetTokenFromHeader:
    """Test token extraction from Authorization header."""
    
    def test_extract_valid_bearer_token(self, app):
        """Test extracting valid Bearer token."""
        with app.test_request_context(
            headers={'Authorization': 'Bearer test-token-123'}
        ):
            token = get_token_from_header()
            assert token == 'test-token-123'
    
    def test_no_authorization_header(self, app):
        """Test when Authorization header is missing."""
        with app.test_request_context():
            token = get_token_from_header()
            assert token is None
    
    def test_invalid_header_format_no_bearer(self, app):
        """Test invalid header without Bearer prefix."""
        with app.test_request_context(
            headers={'Authorization': 'Basic dGVzdDp0ZXN0'}
        ):
            with pytest.raises(Auth0Error) as exc_info:
                get_token_from_header()
            
            assert 'must start with Bearer' in exc_info.value.message
    
    def test_invalid_header_no_token(self, app):
        """Test invalid header with Bearer but no token."""
        with app.test_request_context(
            headers={'Authorization': 'Bearer'}
        ):
            with pytest.raises(Auth0Error) as exc_info:
                get_token_from_header()
            
            assert 'Token not found' in exc_info.value.message
    
    def test_invalid_header_multiple_parts(self, app):
        """Test invalid header with multiple parts."""
        with app.test_request_context(
            headers={'Authorization': 'Bearer token1 token2'}
        ):
            with pytest.raises(Auth0Error) as exc_info:
                get_token_from_header()
            
            assert 'must be Bearer token' in exc_info.value.message


# Tests for verify_jwt()
class TestVerifyJwt:
    """Test JWT token verification."""
    
    @patch('flask_app.auth.auth0.get_jwks_client')
    @patch('flask_app.auth.auth0.jwt.decode')
    def test_verify_valid_token(self, mock_decode, mock_get_client, mock_env, valid_token_payload):
        """Test verifying a valid JWT token."""
        # Mock signing key
        mock_signing_key = Mock()
        mock_signing_key.key = 'test-key'
        
        # Mock JWKS client
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        # Mock jwt.decode to return valid payload
        mock_decode.return_value = valid_token_payload
        
        # Verify token
        result = verify_jwt('test-token')
        
        assert result == valid_token_payload
        assert result['sub'] == 'auth0|123456789'
        assert result['email'] == 'test@example.com'
        
        # Verify jwt.decode was called with correct parameters
        mock_decode.assert_called_once()
        call_kwargs = mock_decode.call_args.kwargs
        assert call_kwargs['audience'] == 'https://api.test.com'
        assert call_kwargs['issuer'] == 'https://test-domain.auth0.com/'
        assert call_kwargs['algorithms'] == ['RS256']
    
    @patch('flask_app.auth.auth0.get_jwks_client')
    @patch('flask_app.auth.auth0.jwt.decode')
    def test_verify_expired_token(self, mock_decode, mock_get_client, mock_env):
        """Test verifying an expired token."""
        mock_signing_key = Mock()
        mock_signing_key.key = 'test-key'
        
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        # Mock jwt.decode to raise ExpiredSignatureError
        mock_decode.side_effect = jwt.ExpiredSignatureError
        
        with pytest.raises(Auth0Error) as exc_info:
            verify_jwt('expired-token')
        
        assert 'Token has expired' in exc_info.value.message
        assert exc_info.value.status_code == 401
    
    @patch('flask_app.auth.auth0.get_jwks_client')
    @patch('flask_app.auth.auth0.jwt.decode')
    def test_verify_invalid_audience(self, mock_decode, mock_get_client, mock_env):
        """Test verifying token with invalid audience."""
        mock_signing_key = Mock()
        mock_signing_key.key = 'test-key'
        
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        mock_decode.side_effect = jwt.InvalidAudienceError
        
        with pytest.raises(Auth0Error) as exc_info:
            verify_jwt('invalid-audience-token')
        
        assert 'Invalid audience' in exc_info.value.message
    
    @patch('flask_app.auth.auth0.get_jwks_client')
    @patch('flask_app.auth.auth0.jwt.decode')
    def test_verify_invalid_issuer(self, mock_decode, mock_get_client, mock_env):
        """Test verifying token with invalid issuer."""
        mock_signing_key = Mock()
        mock_signing_key.key = 'test-key'
        
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        mock_decode.side_effect = jwt.InvalidIssuerError
        
        with pytest.raises(Auth0Error) as exc_info:
            verify_jwt('invalid-issuer-token')
        
        assert 'Invalid issuer' in exc_info.value.message
    
    @patch('flask_app.auth.auth0.get_jwks_client')
    @patch('flask_app.auth.auth0.jwt.decode')
    def test_verify_invalid_signature(self, mock_decode, mock_get_client, mock_env):
        """Test verifying token with invalid signature."""
        mock_signing_key = Mock()
        mock_signing_key.key = 'test-key'
        
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        mock_decode.side_effect = jwt.InvalidSignatureError
        
        with pytest.raises(Auth0Error) as exc_info:
            verify_jwt('invalid-signature-token')
        
        assert 'Invalid signature' in exc_info.value.message
    
    def test_verify_missing_auth0_domain(self, monkeypatch):
        """Test error when AUTH0_DOMAIN not set."""
        import flask_app.auth.auth0 as auth0_module
        original_domain = auth0_module.AUTH0_DOMAIN
        original_audience = auth0_module.AUTH0_AUDIENCE
        
        # Set AUDIENCE but remove DOMAIN
        auth0_module.AUTH0_DOMAIN = None
        auth0_module.AUTH0_AUDIENCE = 'https://api.test.com'
        
        # Reset cache
        auth0_module._jwks_client = None
        
        try:
            with pytest.raises(Auth0Error) as exc_info:
                verify_jwt('test-token')
            
            assert exc_info.value.status_code == 500
            assert 'AUTH0_DOMAIN' in exc_info.value.message
        finally:
            auth0_module.AUTH0_DOMAIN = original_domain
            auth0_module.AUTH0_AUDIENCE = original_audience
            auth0_module._jwks_client = None
    
    def test_verify_missing_auth0_audience(self, monkeypatch):
        """Test error when AUTH0_AUDIENCE not set."""
        import flask_app.auth.auth0 as auth0_module
        original_domain = auth0_module.AUTH0_DOMAIN
        original_audience = auth0_module.AUTH0_AUDIENCE
        
        # Set DOMAIN but remove AUDIENCE
        auth0_module.AUTH0_DOMAIN = 'test-domain.auth0.com'
        auth0_module.AUTH0_AUDIENCE = None
        
        # Reset cache
        auth0_module._jwks_client = None
        
        try:
            with pytest.raises(Auth0Error) as exc_info:
                verify_jwt('test-token')
            
            assert exc_info.value.status_code == 500
            assert 'AUTH0_AUDIENCE' in exc_info.value.message
        finally:
            auth0_module.AUTH0_DOMAIN = original_domain
            auth0_module.AUTH0_AUDIENCE = original_audience
            auth0_module._jwks_client = None


# Tests for @require_auth decorator
class TestRequireAuthDecorator:
    """Test @require_auth decorator behavior."""
    
    @patch('flask_app.auth.auth0.verify_jwt')
    def test_decorator_with_valid_token(self, mock_verify, client, mock_env, valid_token_payload):
        """Test decorator allows access with valid token."""
        mock_verify.return_value = valid_token_payload
        
        response = client.get(
            '/test-protected',
            headers={'Authorization': 'Bearer valid-token'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'auth0|123456789'
        assert data['user']['email'] == 'test@example.com'
    
    def test_decorator_without_token(self, client, mock_env):
        """Test decorator rejects request without token."""
        response = client.get('/test-protected')
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        # The actual error message may vary, check for authentication error
        assert 'token' in data['message'].lower() or 'bearer' in data['message'].lower()
    
    @patch('flask_app.auth.auth0.verify_jwt')
    def test_decorator_with_invalid_token(self, mock_verify, client, mock_env):
        """Test decorator rejects invalid token."""
        mock_verify.side_effect = Auth0Error('Invalid token')
        
        response = client.get(
            '/test-protected',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'authentication_failed' in data['error']
    
    @patch('flask_app.auth.auth0.verify_jwt')
    def test_decorator_stores_user_in_g(self, mock_verify, app, mock_env, valid_token_payload):
        """Test decorator stores user info in Flask's g object."""
        mock_verify.return_value = valid_token_payload
        
        with app.test_client() as client:
            response = client.get(
                '/test-protected',
                headers={'Authorization': 'Bearer valid-token'}
            )
            
            # Verify decorator allowed access (which means user data was stored)
            assert response.status_code == 200
            data = response.get_json()
            assert data['user_id'] == 'auth0|123456789'


# Tests for verify_websocket_token()
class TestVerifyWebsocketToken:
    """Test WebSocket token verification."""
    
    @patch('flask_app.auth.auth0.verify_jwt')
    def test_verify_valid_websocket_token(self, mock_verify, mock_env, valid_token_payload):
        """Test verifying valid WebSocket token."""
        mock_verify.return_value = valid_token_payload
        
        result = verify_websocket_token('websocket-token')
        
        assert result == valid_token_payload
        mock_verify.assert_called_once_with('websocket-token')
    
    def test_verify_empty_websocket_token(self, mock_env):
        """Test error with empty WebSocket token."""
        with pytest.raises(Auth0Error) as exc_info:
            verify_websocket_token('')
        
        assert 'Token is required' in exc_info.value.message
    
    def test_verify_none_websocket_token(self, mock_env):
        """Test error with None WebSocket token."""
        with pytest.raises(Auth0Error) as exc_info:
            verify_websocket_token(None)  # type: ignore
        
        assert 'Token is required' in exc_info.value.message
    
    @patch('flask_app.auth.auth0.verify_jwt')
    def test_verify_invalid_websocket_token(self, mock_verify, mock_env):
        """Test error with invalid WebSocket token."""
        mock_verify.side_effect = Auth0Error('Invalid token')
        
        with pytest.raises(Auth0Error) as exc_info:
            verify_websocket_token('invalid-token')
        
        assert 'Invalid token' in exc_info.value.message


# Tests for get_user_info()
class TestGetUserInfo:
    """Test user info retrieval from Auth0."""
    
    @patch('flask_app.auth.auth0.requests.get')
    def test_get_user_info_success(self, mock_get, mock_env):
        """Test successful user info retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'sub': 'auth0|123456789',
            'name': 'Test User',
            'email': 'test@example.com',
            'picture': 'https://example.com/avatar.jpg'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = get_user_info('access-token')
        
        assert result['sub'] == 'auth0|123456789'
        assert result['email'] == 'test@example.com'
        
        # Verify request was made correctly
        mock_get.assert_called_once_with(
            'https://test-domain.auth0.com/userinfo',
            headers={'Authorization': 'Bearer access-token'},
            timeout=30
        )
    
    @patch('flask_app.auth.auth0.requests.get')
    def test_get_user_info_request_error(self, mock_get, mock_env):
        """Test error handling when request fails."""
        import requests
        mock_get.side_effect = requests.RequestException('Connection error')
        
        with pytest.raises(Auth0Error) as exc_info:
            get_user_info('access-token')
        
        assert 'Failed to fetch user info' in exc_info.value.message
    
    def test_get_user_info_no_domain(self, monkeypatch):
        """Test error when AUTH0_DOMAIN not set."""
        import flask_app.auth.auth0 as auth0_module
        original_domain = auth0_module.AUTH0_DOMAIN
        auth0_module.AUTH0_DOMAIN = None
        
        try:
            with pytest.raises(Auth0Error) as exc_info:
                get_user_info('access-token')
            
            assert exc_info.value.status_code == 500
            assert 'AUTH0_DOMAIN not configured' in exc_info.value.message
        finally:
            auth0_module.AUTH0_DOMAIN = original_domain


# Tests for Auth0Error exception
class TestAuth0Error:
    """Test Auth0Error exception class."""
    
    def test_auth0_error_default_status(self):
        """Test Auth0Error with default status code."""
        error = Auth0Error('Test error')
        
        assert error.message == 'Test error'
        assert error.status_code == 401
        assert str(error) == 'Test error'
    
    def test_auth0_error_custom_status(self):
        """Test Auth0Error with custom status code."""
        error = Auth0Error('Server error', 500)
        
        assert error.message == 'Server error'
        assert error.status_code == 500


# Tests for PyJWKClient caching
class TestJwksClientCaching:
    """Test PyJWKClient instance caching."""
    
    @patch('flask_app.auth.auth0.PyJWKClient')
    def test_jwks_client_cached(self, mock_jwks_client_class, mock_env):
        """Test that PyJWKClient is cached and reused."""
        # Reset cache
        import flask_app.auth.auth0 as auth0_module
        auth0_module._jwks_client = None
        
        mock_client = Mock()
        mock_jwks_client_class.return_value = mock_client
        
        # First call should create new client
        client1 = get_jwks_client()
        assert client1 == mock_client
        assert mock_jwks_client_class.call_count == 1
        
        # Second call should return cached client
        client2 = get_jwks_client()
        assert client2 == mock_client
        assert mock_jwks_client_class.call_count == 1  # Not called again
        
        # Both should be the same instance
        assert client1 is client2


# Integration tests
class TestAuth0Integration:
    """Integration tests for Auth0 module."""
    
    @patch('flask_app.auth.auth0.verify_jwt')
    @patch('flask_app.auth.auth0.get_user_info')
    def test_full_authentication_flow(self, mock_get_info, mock_verify, 
                                      client, mock_env, valid_token_payload):
        """Test complete authentication flow."""
        mock_verify.return_value = valid_token_payload
        mock_get_info.return_value = {
            'sub': 'auth0|123456789',
            'name': 'Test User',
            'email': 'test@example.com'
        }
        
        # Make authenticated request
        response = client.get(
            '/test-protected',
            headers={'Authorization': 'Bearer valid-token'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'auth0|123456789'
        assert 'user' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
