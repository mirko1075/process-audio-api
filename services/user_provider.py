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
    
    def update_usage_stats(self, provider_name, cost_usd=0.0, audio_minutes=0.0, tokens=0):
        """
        Update usage statistics for a provider.
        
        Args:
            provider_name (str): Provider name
            cost_usd (float): Cost in USD for this operation
            audio_minutes (float): Minutes of audio processed
            tokens (int): Number of tokens processed
        """
        config = self.get_provider_config(provider_name)
        if config:
            try:
                config.update_usage(cost_usd=cost_usd, audio_minutes=audio_minutes, tokens=tokens)
                logger.debug(f"Updated usage for provider {provider_name}: ${cost_usd}, {audio_minutes}min, {tokens} tokens")
            except Exception as e:
                logger.error(f"Failed to update usage stats for {provider_name}: {e}")
    
    def test_provider_config(self, provider_name):
        """
        Test a provider configuration by attempting to retrieve the API key.
        
        Args:
            provider_name (str): Provider name to test
            
        Returns:
            dict: Test result with status and message
        """
        try:
            api_key = self.get_user_api_key(provider_name)
            
            # Basic validation - check key format
            if provider_name == 'openai' and not api_key.startswith('sk-'):
                return {
                    'status': 'error',
                    'message': 'Invalid OpenAI API key format (should start with sk-)'
                }
            elif provider_name == 'deepgram' and len(api_key) < 32:
                return {
                    'status': 'error', 
                    'message': 'Invalid Deepgram API key format (too short)'
                }
            
            return {
                'status': 'success',
                'message': f'{provider_name.title()} API key is configured and appears valid'
            }
            
        except ConfigurationError as e:
            return {
                'status': 'error',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error testing provider {provider_name}: {e}")
            return {
                'status': 'error',
                'message': f'Error testing {provider_name} configuration'
            }
    
    def get_user_configured_providers(self):
        """
        Get list of providers configured by the current user.
        
        Returns:
            list: List of configured provider names
        """
        user = self.get_current_user()
        if not user:
            return []
        
        configs = UserProviderConfig.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        return [config.provider.name for config in configs if config.provider.is_active]
    
    def get_user_usage_summary(self):
        """
        Get usage summary for current user across all providers.
        
        Returns:
            dict: Usage summary with totals and by-provider breakdown
        """
        user = self.get_current_user()
        if not user:
            return {}
        
        configs = UserProviderConfig.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        total_requests = sum(config.total_requests for config in configs)
        total_cost = sum(config.total_cost_usd for config in configs)
        total_audio_minutes = sum(config.total_audio_minutes for config in configs)
        total_tokens = sum(config.total_tokens_processed for config in configs)
        
        by_provider = []
        for config in configs:
            if config.provider.is_active:
                by_provider.append({
                    'provider': config.provider.name,
                    'display_name': config.provider.display_name,
                    'requests': config.total_requests,
                    'cost_usd': config.total_cost_usd,
                    'audio_minutes': config.total_audio_minutes,
                    'tokens_processed': config.total_tokens_processed,
                    'last_used': config.last_used.isoformat() if config.last_used else None
                })
        
        return {
            'total_requests': total_requests,
            'total_cost_usd': total_cost,
            'total_audio_minutes': total_audio_minutes,
            'total_tokens_processed': total_tokens,
            'providers_configured': len(configs),
            'by_provider': by_provider
        }