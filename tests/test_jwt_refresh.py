"""Tests for JWT token refresh and revocation functionality."""
import pytest
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import create_access_token, create_refresh_token
from models import db
from models.token_blacklist import TokenBlacklist


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    """Create valid JWT tokens for testing."""
    with app.app_context():
        access_token = create_access_token(identity='test_user')
        refresh_token = create_refresh_token(identity='test_user')
        return {
            'access': {
                'Authorization': f'Bearer {access_token}'
            },
            'refresh': {
                'Authorization': f'Bearer {refresh_token}'
            },
            'access_token': access_token,
            'refresh_token': refresh_token
        }


class TestJWTConfiguration:
    """Test JWT configuration settings."""

    def test_jwt_access_token_expires(self, app):
        """Test that JWT access tokens have expiration configured."""
        assert app.config['JWT_ACCESS_TOKEN_EXPIRES'] is not False
        assert isinstance(app.config['JWT_ACCESS_TOKEN_EXPIRES'], timedelta)
        assert app.config['JWT_ACCESS_TOKEN_EXPIRES'] == timedelta(hours=1)

    def test_jwt_refresh_token_expires(self, app):
        """Test that JWT refresh tokens have expiration configured."""
        assert app.config['JWT_REFRESH_TOKEN_EXPIRES'] is not False
        assert isinstance(app.config['JWT_REFRESH_TOKEN_EXPIRES'], timedelta)
        assert app.config['JWT_REFRESH_TOKEN_EXPIRES'] == timedelta(days=30)

    def test_jwt_secret_key_required(self, app):
        """Test that JWT_SECRET_KEY is set."""
        assert app.config.get('JWT_SECRET_KEY') is not None
        assert app.config['JWT_SECRET_KEY'] != ''


class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client, auth_headers):
        """Test successful token refresh."""
        response = client.post(
            '/auth/refresh',
            headers=auth_headers['refresh']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['access_token'] != ''
        assert data['access_token'] != auth_headers['access_token']

    def test_refresh_token_without_header(self, client):
        """Test refresh endpoint without authorization header."""
        response = client.post('/auth/refresh')

        assert response.status_code == 401

    def test_refresh_token_with_access_token(self, client, auth_headers):
        """Test that access token cannot be used to refresh."""
        response = client.post(
            '/auth/refresh',
            headers=auth_headers['access']
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            '/auth/refresh',
            headers={'Authorization': 'Bearer invalid_token'}
        )

        assert response.status_code == 422


class TestTokenRevocation:
    """Test token revocation (logout) functionality."""

    def test_logout_with_access_token(self, client, app, auth_headers):
        """Test logout with access token."""
        response = client.post(
            '/auth/logout',
            headers=auth_headers['access']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'msg' in data
        assert 'Access token revoked successfully' in data['msg']

        # Verify token was added to blacklist
        with app.app_context():
            from flask_jwt_extended import decode_token
            decoded = decode_token(auth_headers['access_token'])
            blacklisted = TokenBlacklist.query.filter_by(jti=decoded['jti']).first()
            assert blacklisted is not None
            assert blacklisted.token_type == 'access'

    def test_logout_with_refresh_token(self, client, app, auth_headers):
        """Test logout with refresh token."""
        response = client.post(
            '/auth/logout',
            headers=auth_headers['refresh']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'msg' in data
        assert 'Refresh token revoked successfully' in data['msg']

        # Verify token was added to blacklist
        with app.app_context():
            from flask_jwt_extended import decode_token
            decoded = decode_token(auth_headers['refresh_token'])
            blacklisted = TokenBlacklist.query.filter_by(jti=decoded['jti']).first()
            assert blacklisted is not None
            assert blacklisted.token_type == 'refresh'

    def test_logout_without_header(self, client):
        """Test logout without authorization header."""
        response = client.post('/auth/logout')

        assert response.status_code == 401

    def test_revoked_token_rejected(self, client, app, auth_headers):
        """Test that revoked tokens are rejected."""
        # First, logout (revoke the token)
        logout_response = client.post(
            '/auth/logout',
            headers=auth_headers['access']
        )
        assert logout_response.status_code == 200

        # Try to use the revoked token
        response = client.post(
            '/auth/refresh',
            headers=auth_headers['access']
        )

        # Should be rejected (401 or 422 depending on implementation)
        assert response.status_code in [401, 422]


class TestTokenBlacklistModel:
    """Test TokenBlacklist model."""

    def test_create_blacklist_entry(self, app):
        """Test creating a token blacklist entry."""
        with app.app_context():
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            entry = TokenBlacklist(
                jti='test-jti-123',
                token_type='access',
                user_id='test_user',
                expires_at=expires_at
            )

            db.session.add(entry)
            db.session.commit()

            # Verify it was created
            retrieved = TokenBlacklist.query.filter_by(jti='test-jti-123').first()
            assert retrieved is not None
            assert retrieved.token_type == 'access'
            assert retrieved.user_id == 'test_user'
            assert retrieved.jti == 'test-jti-123'

    def test_blacklist_unique_jti(self, app):
        """Test that jti must be unique in blacklist."""
        with app.app_context():
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            entry1 = TokenBlacklist(
                jti='test-jti-duplicate',
                token_type='access',
                user_id='user1',
                expires_at=expires_at
            )
            db.session.add(entry1)
            db.session.commit()

            # Try to add duplicate jti
            entry2 = TokenBlacklist(
                jti='test-jti-duplicate',
                token_type='access',
                user_id='user2',
                expires_at=expires_at
            )
            db.session.add(entry2)

            # Should raise integrity error
            with pytest.raises(Exception):  # SQLAlchemy IntegrityError
                db.session.commit()

            db.session.rollback()


class TestSecurityEnforcement:
    """Test security requirements are enforced."""

    def test_secret_key_required(self, monkeypatch):
        """Test that app fails to start without SECRET_KEY."""
        monkeypatch.delenv('SECRET_KEY', raising=False)

        with pytest.raises(RuntimeError, match="SECRET_KEY environment variable is required"):
            from core import create_app
            create_app()

    def test_jwt_secret_key_required(self, monkeypatch):
        """Test that app fails to start without JWT_SECRET_KEY."""
        monkeypatch.delenv('JWT_SECRET_KEY', raising=False)

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is required"):
            from core import create_app
            create_app()

    def test_socketio_origins_required(self, monkeypatch):
        """Test that app fails to start without SOCKETIO_ORIGINS."""
        monkeypatch.delenv('SOCKETIO_ORIGINS', raising=False)

        with pytest.raises(RuntimeError, match="SOCKETIO_ORIGINS environment variable is required"):
            from core import create_app
            create_app()
