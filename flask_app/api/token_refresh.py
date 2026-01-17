"""JWT token refresh and revocation endpoints."""
from flask import Blueprint, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from models import db
from models.token_blacklist import TokenBlacklist
from datetime import datetime, timezone

bp = Blueprint('token_refresh', __name__)


@bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Generate new access token from refresh token.

    Returns:
        JSON response with new access token
    """
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200


@bp.route('/auth/logout', methods=['POST'])
@jwt_required(verify_type=False)
def logout():
    """Revoke current token (access or refresh).

    Returns:
        JSON response confirming token revocation
    """
    token = get_jwt()
    jti = token['jti']
    token_type = token['type']
    user_id = token.get('sub', 'unknown')
    exp_timestamp = token['exp']

    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    blacklisted_token = TokenBlacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires_at=expires_at
    )

    db.session.add(blacklisted_token)
    db.session.commit()

    return jsonify(msg=f"{token_type.capitalize()} token revoked successfully"), 200
