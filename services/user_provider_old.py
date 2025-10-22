"""Service for managing user provider configurations in SaaS environment."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from flask import g

from models import db
from models.provider import Provider, UserProviderConfig
from utils.encryption import APIKeyEncryption
from utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class UserProviderService:
    """Service to handle user provider configurations for SaaS model."""
    
    def __init__(self):
        self.encryption = APIKeyEncryption()
    
    def get_current_user(self):
        """Get current user from Flask g context (set by auth middleware)."""
        return getattr(g, 'current_user', None)
    
    def get_provider_config(self, provider_name):
        """Get user's provider configuration, return None if not found."""
        user = self.get_current_user()
        if not user:
            return None
        
        provider = Provider.query.filter_by(name=provider_name, is_active=True).first()
        if not provider:
            return None
        
        config = UserProviderConfig.query.filter_by(
            user_id=user.id,
            provider_id=provider.id,
            is_active=True
        ).first()
        
        return config
    
    
    def get_user_api_key(self, provider_name):
        """
        Get decrypted API key for a provider for the current user.
        
        Args:
            provider_name (str): Provider name ('openai', 'deepgram', etc.)
            
        Returns:
            str: Decrypted API key
            
        Raises:
            ConfigurationError: If user hasn't configured this provider
        """
        user = self.get_current_user()
        if not user:
            raise ConfigurationError("No authenticated user found")
        
        config = self.get_provider_config(provider_name)
        if not config:
            raise ConfigurationError(
                f"Provider '{provider_name}' not configured. "
                f"Please add your {provider_name.title()} API key in user configuration."
            )
        
        try:
            # Decrypt the API key
            api_key = self.encryption.decrypt(config.api_key_encrypted)
            logger.debug(f"Retrieved API key for user {user.email} and provider {provider_name}")
            return api_key
        except Exception as e:
            logger.error(f"Failed to decrypt API key for user {user.email}, provider {provider_name}: {e}")
            raise ConfigurationError(f"Failed to retrieve API key for {provider_name}")
    
    def require_user_api_key(self, provider_name):
        """
        Get user API key and raise clear error if not configured.
        
        Args:
            provider_name (str): Provider name
            
        Returns:
            str: Decrypted API key
            
        Raises:
            ConfigurationError: If provider not configured with clear SaaS message
        """
        try:
            return self.get_user_api_key(provider_name)
        except ConfigurationError:
            # Re-raise with SaaS-specific messaging
            user = self.get_current_user()
            user_info = f" for user {user.email}" if user else ""
            raise ConfigurationError(
                f"🔑 SaaS Mode: {provider_name.title()} API key required{user_info}. "
                f"This service requires users to provide their own API keys. "
                f"Please configure your {provider_name.title()} API key in your user settings."
            )
            
        except Exception as e:
            logger.error(f"Error getting user API key: {e}")
            return None
    
    def has_provider_configured(self, user_id: int, provider_name: str) -> bool:
        """
        Check if user has configured a specific provider.
        
        Args:
            user_id: User ID
            provider_name: Provider name
            
        Returns:
            True if provider is configured and active
        """
        return self.get_user_api_key(user_id, provider_name) is not None
    
    def get_user_model_preference(self, user_id: int, provider_name: str) -> Optional[str]:
        """
        Get user's preferred model for a provider.
        
        Args:
            user_id: User ID
            provider_name: Provider name
            
        Returns:
            Model name or None if not configured
        """
        try:
            config = UserProviderConfig.query.join(Provider).filter(
                UserProviderConfig.user_id == user_id,
                Provider.name == provider_name,
                UserProviderConfig.is_active == True,
                Provider.is_active == True
            ).first()
            
            if config and config.default_model:
                return config.default_model.name
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user model preference: {e}")
            return None
    
    def get_user_config(self, user_id: int, provider_name: str) -> Optional[UserProviderConfig]:
        """
        Get complete user provider configuration.
        
        Args:
            user_id: User ID
            provider_name: Provider name
            
        Returns:
            UserProviderConfig object or None
        """
        try:
            return UserProviderConfig.query.join(Provider).filter(
                UserProviderConfig.user_id == user_id,
                Provider.name == provider_name,
                UserProviderConfig.is_active == True,
                Provider.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"Error getting user config: {e}")
            return None
    
    def update_usage_stats(self, user_id: int, provider_name: str, 
                          cost_usd: float = 0.0, audio_minutes: float = 0.0, 
                          tokens: int = 0) -> bool:
        """
        Update usage statistics for user's provider.
        
        Args:
            user_id: User ID
            provider_name: Provider name
            cost_usd: Cost in USD for this operation
            audio_minutes: Audio minutes processed
            tokens: Tokens processed
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            config = self.get_user_config(user_id, provider_name)
            if not config:
                logger.warning(f"Cannot update usage - no config for user {user_id}, provider {provider_name}")
                return False
            
            config.update_usage(cost_usd, audio_minutes, tokens)
            logger.info(f"Updated usage stats for user {user_id}, provider {provider_name}: "
                       f"cost=${cost_usd}, audio={audio_minutes}min, tokens={tokens}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            return False
    
    def get_configured_providers(self, user_id: int) -> Dict[str, Any]:
        """
        Get all configured providers for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with provider information
        """
        try:
            configs = UserProviderConfig.query.join(Provider).filter(
                UserProviderConfig.user_id == user_id,
                UserProviderConfig.is_active == True,
                Provider.is_active == True
            ).all()
            
            result = {
                'total_providers': len(configs),
                'providers': {}
            }
            
            for config in configs:
                result['providers'][config.provider.name] = {
                    'display_name': config.provider.display_name,
                    'configured_at': config.created_at.isoformat(),
                    'last_used': config.last_used.isoformat() if config.last_used else None,
                    'default_model': config.default_model.name if config.default_model else None,
                    'total_requests': config.total_requests,
                    'total_cost_usd': config.total_cost_usd
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting configured providers: {e}")
            return {'total_providers': 0, 'providers': {}}
    
    def require_user_api_key(self, user_id: int, provider_name: str) -> str:
        """
        Get user API key or raise exception if not configured.
        Used in SaaS mode where user MUST provide their own keys.
        
        Args:
            user_id: User ID
            provider_name: Provider name
            
        Returns:
            Decrypted API key
            
        Raises:
            ConfigurationError: If API key is not configured
        """
        from utils.exceptions import ConfigurationError
        
        api_key = self.get_user_api_key(user_id, provider_name)
        if not api_key:
            provider_display = Provider.query.filter_by(name=provider_name).first()
            display_name = provider_display.display_name if provider_display else provider_name.title()
            
            raise ConfigurationError(
                f"{display_name} API key not configured. "
                f"Please add your {display_name} API key in your account settings to use this service."
            )
        
        return api_key


# Global service instance
user_provider_service = UserProviderService()