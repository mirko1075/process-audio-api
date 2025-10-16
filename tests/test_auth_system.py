"""Tests for authentication system."""

import pytest
import json
from unittest.mock import patch, MagicMock

# Test fixtures
@pytest.fixture
def mock_db():
    """Mock database for testing."""
    with patch('models.db') as mock:
        yield mock

@pytest.fixture
def mock_user():
    """Mock user instance."""
    user = MagicMock()
    user.id = 1
    user.email = 'test@example.com'
    user.is_active = True
    user.check_password.return_value = True
    user.to_dict.return_value = {
        'id': 1,
        'email': 'test@example.com',
        'plan': 'pro'
    }
    return user

@pytest.fixture
def mock_api_key():
    """Mock API key instance."""
    api_key = MagicMock()
    api_key.user_id = 1
    api_key.is_active = True
    return api_key

class TestUserRegistration:
    """Test user registration endpoint."""
    
    def test_register_success(self, client, mock_db, mock_user):
        """Test successful user registration."""
        with patch('api.auth.User') as MockUser, \
             patch('api.auth.create_access_token') as mock_jwt:
            
            # Setup mocks
            MockUser.query.filter_by.return_value.first.return_value = None
            MockUser.return_value = mock_user
            mock_user.generate_api_key.return_value = "usr_1_test_api_key"
            mock_jwt.return_value = "test_jwt_token"
            
            response = client.post('/auth/register', 
                json={
                    'email': 'test@example.com',
                    'password': 'password123',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['message'] == 'User registered successfully'
            assert 'access_token' in data
            assert 'api_key' in data
            assert data['api_key'] == "usr_1_test_api_key"
    
    def test_register_existing_email(self, client, mock_user):
        """Test registration with existing email."""
        with patch('api.auth.User') as MockUser:
            MockUser.query.filter_by.return_value.first.return_value = mock_user
            
            response = client.post('/auth/register',
                json={
                    'email': 'test@example.com',
                    'password': 'password123'
                }
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'already registered' in data['error']
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post('/auth/register',
            json={'email': 'test@example.com'}  # Missing password
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing required field' in data['error']

class TestUserLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client, mock_user):
        """Test successful login."""
        with patch('api.auth.User') as MockUser, \
             patch('api.auth.create_access_token') as mock_jwt:
            
            MockUser.query.filter_by.return_value.first.return_value = mock_user
            mock_jwt.return_value = "test_jwt_token"
            
            response = client.post('/auth/login',
                json={
                    'email': 'test@example.com',
                    'password': 'password123'
                }
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['message'] == 'Login successful'
            assert 'access_token' in data
            assert data['access_token'] == "test_jwt_token"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch('api.auth.User') as MockUser:
            MockUser.query.filter_by.return_value.first.return_value = None
            
            response = client.post('/auth/login',
                json={
                    'email': 'test@example.com',
                    'password': 'wrongpassword'
                }
            )
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'Invalid email or password' in data['error']
    
    def test_login_inactive_user(self, client, mock_user):
        """Test login with inactive user."""
        mock_user.is_active = False
        
        with patch('api.auth.User') as MockUser:
            MockUser.query.filter_by.return_value.first.return_value = mock_user
            
            response = client.post('/auth/login',
                json={
                    'email': 'test@example.com',
                    'password': 'password123'
                }
            )
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'Account deactivated' in data['error']

class TestAPIKeyAuthentication:
    """Test API key authentication."""
    
    def test_api_key_auth_success(self, client, mock_user):
        """Test successful API key authentication."""
        with patch('utils.auth.ApiKey') as MockApiKey:
            MockApiKey.verify_key.return_value = mock_user
            
            response = client.post('/transcriptions/deepgram',
                headers={'x-api-key': 'usr_1_test_api_key'},
                data={'audio': (b'fake audio data', 'test.wav')}
            )
            
            # Should not return 401 (authentication successful)
            assert response.status_code != 401
    
    def test_api_key_auth_invalid(self, client):
        """Test authentication with invalid API key."""
        with patch('utils.auth.ApiKey') as MockApiKey:
            MockApiKey.verify_key.return_value = None
            
            response = client.post('/transcriptions/deepgram',
                headers={'x-api-key': 'invalid_key'},
                data={'audio': (b'fake audio data', 'test.wav')}
            )
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'Authentication required' in data['error']
    
    def test_legacy_api_key_auth(self, client):
        """Test legacy API key authentication."""
        with patch('utils.config.get_app_config') as mock_config:
            mock_config.return_value.api_key = 'legacy_api_key'
            
            response = client.post('/transcriptions/deepgram',
                headers={'x-api-key': 'legacy_api_key'},
                data={'audio': (b'fake audio data', 'test.wav')}
            )
            
            # Should not return 401 (legacy auth successful)
            assert response.status_code != 401

class TestJWTAuthentication:
    """Test JWT authentication."""
    
    def test_jwt_auth_success(self, client, mock_user):
        """Test successful JWT authentication."""
        with patch('utils.auth.verify_jwt_in_request') as mock_verify, \
             patch('utils.auth.get_jwt_identity') as mock_identity, \
             patch('utils.auth.User') as MockUser:
            
            mock_identity.return_value = 1
            MockUser.query.get.return_value = mock_user
            
            response = client.post('/transcriptions/deepgram',
                headers={'Authorization': 'Bearer valid_jwt_token'},
                data={'audio': (b'fake audio data', 'test.wav')}
            )
            
            # Should not return 401 (authentication successful)
            assert response.status_code != 401
    
    def test_jwt_auth_invalid(self, client):
        """Test authentication with invalid JWT."""
        with patch('utils.auth.verify_jwt_in_request') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")
            
            response = client.post('/transcriptions/deepgram',
                headers={'Authorization': 'Bearer invalid_token'},
                data={'audio': (b'fake audio data', 'test.wav')}
            )
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'Authentication required' in data['error']

class TestAPIKeyManagement:
    """Test API key management endpoints."""
    
    def test_create_api_key(self, client, mock_user):
        """Test creating new API key."""
        with patch('api.auth.verify_jwt_in_request'), \
             patch('api.auth.get_jwt_identity') as mock_identity, \
             patch('api.auth.User') as MockUser:
            
            mock_identity.return_value = 1
            MockUser.query.get.return_value = mock_user
            mock_user.generate_api_key.return_value = "usr_1_new_api_key"
            
            response = client.post('/auth/api-keys',
                headers={'Authorization': 'Bearer valid_jwt_token'},
                json={'name': 'Test API Key'}
            )
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['message'] == 'API key created successfully'
            assert data['api_key'] == "usr_1_new_api_key"
    
    def test_delete_api_key(self, client, mock_api_key):
        """Test deactivating API key."""
        with patch('api.auth.verify_jwt_in_request'), \
             patch('api.auth.get_jwt_identity') as mock_identity, \
             patch('api.auth.ApiKey') as MockApiKey:
            
            mock_identity.return_value = 1
            MockApiKey.query.filter_by.return_value.first.return_value = mock_api_key
            
            response = client.delete('/auth/api-keys/1',
                headers={'Authorization': 'Bearer valid_jwt_token'}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['message'] == 'API key deactivated'
            assert mock_api_key.is_active == False

class TestBackwardCompatibility:
    """Test backward compatibility with existing API."""
    
    def test_existing_endpoints_work(self, client):
        """Test that existing endpoints still work with legacy auth."""
        with patch('utils.config.get_app_config') as mock_config:
            mock_config.return_value.api_key = 'legacy_key'
            
            # Test all transcription endpoints
            endpoints = [
                '/transcriptions/deepgram',
                '/transcriptions/whisper', 
                '/transcriptions/assemblyai',
                '/transcriptions/video'
            ]
            
            for endpoint in endpoints:
                response = client.post(endpoint,
                    headers={'x-api-key': 'legacy_key'},
                    data={'audio': (b'fake audio data', 'test.wav')}
                )
                
                # Should not return 401 (authentication should work)
                assert response.status_code != 401, f"Authentication failed for {endpoint}"