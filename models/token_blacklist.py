"""Token blacklist model for JWT revocation."""
from models import db
from datetime import datetime


class TokenBlacklist(db.Model):
    """Model for tracking revoked JWT tokens."""

    __tablename__ = 'token_blacklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)  # 'access' or 'refresh'
    user_id = db.Column(db.String(255), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<TokenBlacklist {self.jti}>'
