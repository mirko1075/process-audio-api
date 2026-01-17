"""Database models initialization."""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()

def init_db(app):
    """Initialize database extensions."""
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

# Import models after db initialization to avoid circular imports
from models.user import User, ApiKey, UsageLog
from models.token_blacklist import TokenBlacklist
from models.job import Job
from models.artifact import Artifact

__all__ = ['db', 'bcrypt', 'jwt', 'migrate', 'init_db', 'User', 'ApiKey', 'UsageLog', 'TokenBlacklist', 'Job', 'Artifact']