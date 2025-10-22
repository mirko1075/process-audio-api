"""Encryption utilities for user API keys in SaaS environment."""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

logger = logging.getLogger(__name__)

class APIKeyEncryption:
    """Encrypt/decrypt user API keys for secure storage."""
    
    def __init__(self):
        # Use Flask's SECRET_KEY for encryption
        secret = os.environ.get('SECRET_KEY')
        if not secret:
            raise ValueError("SECRET_KEY environment variable is required for API key encryption")
        self.master_key = secret.encode()
    
    def _derive_key_from_salt(self, salt: bytes) -> bytes:
        """Derive encryption key from master key and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.master_key)
        return key
    
    def encrypt_api_key(self, api_key: str) -> str:

        """
        Encrypt API key for database storage.
        
        Args:
            api_key: Plain text API key from user
            
        Returns:
            Base64 encoded encrypted API key with salt
            
        Raises:
            ValueError: If api_key is empty or invalid
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")
        
        try:
            # Generate random salt for this key
            salt = os.urandom(16)
            key = self._derive_key_from_salt(salt)
            cipher = ChaCha20Poly1305(key)
            nonce = os.urandom(12)
        
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise ValueError("Failed to encrypt API key") from e
            
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key for use in API calls.
        
        Args:
            encrypted_key: Base64 encoded encrypted API key from database
            
        Returns:
            Plain text API key
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_key:
            raise ValueError("Encrypted key cannot be empty")
        
        try:
            combined_data = base64.urlsafe_b64decode(encrypted_key.encode())
            
            # Extract salt (first 16 bytes), nonce (next 12 bytes), and encrypted data
            if len(combined_data) < 28:  # 16 + 12 minimum
                raise ValueError("Invalid encrypted key format")
            
            salt = combined_data[:16]
            nonce = combined_data[16:28]
            encrypted_data = combined_data[28:]
            
            key = self._derive_key_from_salt(salt)
            cipher = ChaCha20Poly1305(key)
            
            decrypted = cipher.decrypt(nonce, encrypted_data, None)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise ValueError("Failed to decrypt API key - key may be corrupted")
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise ValueError("Failed to decrypt API key - key may be corrupted")
    
    def create_preview(self, api_key: str) -> str:
        """
        Create safe preview of API key for UI display.
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Masked API key showing only first and last few characters
        """
        if not api_key:
            return "****"
        
        api_key = api_key.strip()
        
        if len(api_key) < 8:
            return "****"
        
        # For most API keys: show first 4 and last 4 characters
        if len(api_key) <= 16:
            return f"{api_key[:3]}****{api_key[-3:]}"
        
        # For longer keys: show more characters
        return f"{api_key[:6]}****{api_key[-6:]}"
    
    def validate_api_key_format(self, api_key: str, provider_name: str) -> bool:
        """
        Basic validation of API key format for known providers.
        
        Args:
            api_key: API key to validate
            provider_name: Provider name (openai, deepgram, etc.)
            
        Returns:
            True if format looks valid, False otherwise
        """
        if not api_key or not api_key.strip():
            return False
        
        api_key = api_key.strip()
        
        # Provider-specific validations
        if provider_name == 'openai':
            return api_key.startswith('sk-') and len(api_key) > 20
        elif provider_name == 'deepgram':
            return len(api_key) >= 32  # Deepgram keys are typically long hex strings
        elif provider_name == 'assemblyai':
            return len(api_key) >= 32  # AssemblyAI keys are long strings
        else:
            # Generic validation: at least 16 characters
            return len(api_key) >= 16


# Global encryption instance
encryption = APIKeyEncryption()


def encrypt_user_api_key(api_key: str) -> str:
    """Convenience function to encrypt API key."""
    return encryption.encrypt_api_key(api_key)


def decrypt_user_api_key(encrypted_key: str) -> str:
    """Convenience function to decrypt API key."""
    return encryption.decrypt_api_key(encrypted_key)


def create_api_key_preview(api_key: str) -> str:
    """Convenience function to create API key preview."""
    return encryption.create_preview(api_key)


def validate_api_key_format(api_key: str, provider_name: str) -> bool:
    """Convenience function to validate API key format."""
    return encryption.validate_api_key_format(api_key, provider_name)