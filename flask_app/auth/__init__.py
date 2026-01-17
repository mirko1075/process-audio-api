"""Auth0 authentication module for Flask application."""
from .auth0 import (
    verify_jwt,
    require_auth,
    verify_websocket_token,
    get_user_info,
    Auth0Error,
    register_auth_error_handlers
)

__all__ = [
    'verify_jwt',
    'require_auth',
    'verify_websocket_token',
    'get_user_info',
    'Auth0Error',
    'register_auth_error_handlers'
]
