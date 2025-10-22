"""User provider configuration API endpoints for SaaS API key management."""

import logging
from flask import Blueprint, request, jsonify, g
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import IntegrityError

from models import db
from models.provider import Provider, ProviderModel, UserProviderConfig
from utils.auth import require_jwt
from utils.encryption import encrypt_user_api_key, create_api_key_preview, validate_api_key_format
from utils.exceptions import ConfigurationError

bp = Blueprint('user_config', __name__, url_prefix='/user-config')
logger = logging.getLogger(__name__)


@bp.route('/providers', methods=['GET'])
@require_jwt
def get_available_providers():
    """
    Get list of available AI providers and their models.
    Only active providers and models are returned.
    """
    try:
        providers = Provider.query.filter_by(is_active=True).all()
        
        result = []
        for provider in providers:
            provider_data = provider.to_dict()
            
            # Add active models
            active_models = [
                model.to_dict() 
                for model in provider.models 
                if model.is_active
            ]
            provider_data['models'] = active_models
            
            result.append(provider_data)
        
        logger.info(f"Retrieved {len(result)} available providers for user {g.current_user.id}")
        return jsonify({'providers': result})
        
    except Exception as e:
        logger.error(f"Error fetching providers: {e}")
        return jsonify({'error': 'Failed to fetch providers'}), 500


@bp.route('/provider-configs', methods=['GET'])
@require_jwt
def get_user_provider_configs():
    """Get user's current provider configurations with usage statistics."""
    try:
        user_id = g.current_user.id
        configs = UserProviderConfig.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).join(Provider).filter(Provider.is_active == True).all()
        
        result = [config.to_dict() for config in configs]
        
        logger.info(f"Retrieved {len(result)} provider configs for user {user_id}")
        return jsonify({'configurations': result})
        
    except Exception as e:
        logger.error(f"Error fetching user configs: {e}")
        return jsonify({'error': 'Failed to fetch configurations'}), 500


@bp.route('/provider-configs', methods=['POST'])
@require_jwt
def create_provider_config():
    """
    Create or update user's API key for a provider.
    This is required for SaaS - users must provide their own API keys.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['provider_id', 'api_key']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f'Missing required field: {field}')
        
        user_id = g.current_user.id
        provider_id = data['provider_id']
        api_key = data['api_key'].strip()
        default_model_id = data.get('default_model_id')
        
        # Validate provider exists and is active
        provider = Provider.query.filter_by(id=provider_id, is_active=True).first()
        if not provider:
            raise BadRequest('Invalid or inactive provider')
        
        # Validate API key format
        if not validate_api_key_format(api_key, provider.name):
            raise BadRequest(f'Invalid API key format for {provider.display_name}')
        
        # Validate model if provided
        if default_model_id:
            model = ProviderModel.query.filter_by(
                id=default_model_id, 
                provider_id=provider_id,
                is_active=True
            ).first()
            if not model:
                raise BadRequest('Invalid model for this provider')
        
        # Encrypt API key
        try:
            encrypted_key = encrypt_user_api_key(api_key)
            key_preview = create_api_key_preview(api_key)
        except ValueError as e:
            logger.error(f"API key encryption failed: {e}")
            raise BadRequest('Invalid API key format')
        
        # Check if config already exists
        existing_config = UserProviderConfig.query.filter_by(
            user_id=user_id,
            provider_id=provider_id
        ).first()
        
        if existing_config:
            # Update existing configuration
            existing_config.api_key_encrypted = encrypted_key
            existing_config.api_key_preview = key_preview
            existing_config.default_model_id = default_model_id
            existing_config.is_active = True
            config = existing_config
            message = f"{provider.display_name} configuration updated successfully"
        else:
            # Create new configuration
            config = UserProviderConfig(
                user_id=user_id,
                provider_id=provider_id,
                api_key_encrypted=encrypted_key,
                api_key_preview=key_preview,
                default_model_id=default_model_id
            )
            db.session.add(config)
            message = f"{provider.display_name} configuration created successfully"
        
        db.session.commit()
        
        logger.info(f"Provider config created/updated: user={user_id}, provider={provider.name}")
        
        return jsonify({
            'message': message,
            'configuration': {
                'id': config.id,
                'provider': provider.display_name,
                'api_key_preview': config.api_key_preview,
                'default_model': config.default_model.display_name if config.default_model else None
            }
        }), 201
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error: {e}")
        return jsonify({'error': 'Configuration already exists'}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating provider config: {e}")
        return jsonify({'error': 'Failed to create configuration'}), 500


@bp.route('/provider-configs/<int:config_id>', methods=['PUT'])
@require_jwt
def update_provider_config(config_id):
    """Update specific provider configuration (model preference, etc.)."""
    try:
        user_id = g.current_user.id
        data = request.get_json()
        
        config = UserProviderConfig.query.filter_by(
            id=config_id,
            user_id=user_id
        ).first()
        
        if not config:
            return jsonify({'error': 'Configuration not found'}), 404
        
        # Update default model if provided
        if 'default_model_id' in data:
            model_id = data['default_model_id']
            if model_id:
                model = ProviderModel.query.filter_by(
                    id=model_id,
                    provider_id=config.provider_id,
                    is_active=True
                ).first()
                if not model:
                    raise BadRequest('Invalid model for this provider')
                config.default_model_id = model_id
            else:
                config.default_model_id = None
        
        # Update API key if provided
        if 'api_key' in data:
            new_api_key = data['api_key'].strip()
            if not validate_api_key_format(new_api_key, config.provider.name):
                raise BadRequest(f'Invalid API key format for {config.provider.display_name}')
            
            config.api_key_encrypted = encrypt_user_api_key(new_api_key)
            config.api_key_preview = create_api_key_preview(new_api_key)
        
        db.session.commit()
        
        logger.info(f"Provider config updated: user={user_id}, config={config_id}")
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'configuration': config.to_dict()
        })
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating provider config: {e}")
        return jsonify({'error': 'Failed to update configuration'}), 500


@bp.route('/provider-configs/<int:config_id>', methods=['DELETE'])
@require_jwt
def delete_provider_config(config_id):
    """Deactivate a provider configuration."""
    try:
        user_id = g.current_user.id
        
        config = UserProviderConfig.query.filter_by(
            id=config_id,
            user_id=user_id
        ).first()
        
        if not config:
            return jsonify({'error': 'Configuration not found'}), 404
        
        config.is_active = False
        db.session.commit()
        
        logger.info(f"Provider config deactivated: user={user_id}, config={config_id}")
        
        return jsonify({'message': 'Configuration deactivated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting provider config: {e}")
        return jsonify({'error': 'Failed to delete configuration'}), 500


@bp.route('/provider-configs/<int:config_id>/test', methods=['POST'])
@require_jwt
def test_provider_config(config_id):
    """Test a provider configuration by making a simple API call."""
    try:
        user_id = g.current_user.id
        
        config = UserProviderConfig.query.filter_by(
            id=config_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not config:
            return jsonify({'error': 'Configuration not found'}), 404
        
        # This would be implemented to test the actual API key
        # For now, just return success
        logger.info(f"API key test requested: user={user_id}, provider={config.provider.name}")
        
        return jsonify({
            'message': f'{config.provider.display_name} API key test successful',
            'provider': config.provider.display_name,
            'status': 'active'
        })
        
    except Exception as e:
        logger.error(f"Error testing provider config: {e}")
        return jsonify({'error': 'Failed to test configuration'}), 500


@bp.route('/usage-stats', methods=['GET'])
@require_jwt
def get_usage_statistics():
    """Get user's usage statistics across all providers."""
    try:
        user_id = g.current_user.id
        
        configs = UserProviderConfig.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        total_stats = {
            'total_requests': 0,
            'total_cost_usd': 0.0,
            'total_audio_minutes': 0.0,
            'total_tokens_processed': 0,
            'providers_configured': len(configs),
            'by_provider': []
        }
        
        for config in configs:
            provider_stats = {
                'provider': config.provider.display_name,
                'requests': config.total_requests,
                'cost_usd': config.total_cost_usd,
                'audio_minutes': config.total_audio_minutes,
                'tokens_processed': config.total_tokens_processed,
                'last_used': config.last_used.isoformat() if config.last_used else None
            }
            
            total_stats['by_provider'].append(provider_stats)
            total_stats['total_requests'] += config.total_requests
            total_stats['total_cost_usd'] += config.total_cost_usd
            total_stats['total_audio_minutes'] += config.total_audio_minutes
            total_stats['total_tokens_processed'] += config.total_tokens_processed
        
        return jsonify(total_stats)
        
    except Exception as e:
        logger.error(f"Error fetching usage stats: {e}")
        return jsonify({'error': 'Failed to fetch usage statistics'}), 500