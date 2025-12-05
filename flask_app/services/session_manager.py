"""Session management service for mobile app authentication.

This module provides an abstraction layer for session storage and validation,
allowing easy migration from in-memory storage to Redis or database in the future.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions for mobile app authentication.
    
    Currently uses in-memory storage (suitable for single-worker deployments).
    For production with multiple workers, implement Redis or database backend.
    """
    
    def __init__(self):
        """Initialize session manager with in-memory storage."""
        self._sessions: Dict[str, Dict] = {}
    
    def create_session(self, username: str, expires_hours: int = 24) -> Dict[str, str]:
        """Create a new session for a user.
        
        Args:
            username: User identifier
            expires_hours: Session duration in hours (default: 24)
            
        Returns:
            Dict containing auth_token, user_id, and expires_at
        """
        auth_token = f"session_{secrets.token_urlsafe(32)}"
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        user_id = username.lower().replace(' ', '_')
        
        self._sessions[auth_token] = {
            'username': username,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        logger.info(f"Session created for user: {username}")
        
        return {
            'auth_token': auth_token,
            'user_id': user_id,
            'expires_at': expires_at.isoformat()
        }
    
    def validate_session(self, auth_token: str) -> bool:
        """Validate if a session token is valid and not expired.
        
        Args:
            auth_token: Session token to validate
            
        Returns:
            True if valid and not expired, False otherwise
        """
        if not auth_token or auth_token not in self._sessions:
            return False
        
        session = self._sessions[auth_token]
        expires_at = datetime.fromisoformat(session['expires_at'])
        
        # Check if token is expired
        if datetime.utcnow() > expires_at:
            self.invalidate_session(auth_token)
            return False
        
        return True
    
    def get_session_info(self, auth_token: str) -> Optional[Dict]:
        """Get session information for a valid token.
        
        Args:
            auth_token: Session token
            
        Returns:
            Session info dict or None if invalid
        """
        if not self.validate_session(auth_token):
            return None
        
        return self._sessions.get(auth_token)
    
    def invalidate_session(self, auth_token: str) -> bool:
        """Invalidate (delete) a session.
        
        Args:
            auth_token: Session token to invalidate
            
        Returns:
            True if session was found and deleted, False otherwise
        """
        if auth_token in self._sessions:
            username = self._sessions[auth_token].get('username', 'unknown')
            del self._sessions[auth_token]
            logger.info(f"Session invalidated for user: {username}")
            return True
        return False
    
    def get_session_count(self) -> int:
        """Get count of active sessions (for monitoring/debugging).
        
        Returns:
            Number of active sessions
        """
        return len(self._sessions)
    
    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions from storage.
        
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired_tokens = []
        
        for token, session in self._sessions.items():
            expires_at = datetime.fromisoformat(session['expires_at'])
            if now > expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self._sessions[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
        
        return len(expired_tokens)


# Global session manager instance (singleton pattern)
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance.
    
    Returns:
        SessionManager instance
    """
    return _session_manager
