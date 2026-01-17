#!/usr/bin/env python3
"""Add token_blacklist table for JWT revocation."""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def migrate():
    """Create token_blacklist table."""
    from core import create_app
    from models import db

    print("🔄 Starting migration: Add token_blacklist table")

    app, _ = create_app()

    with app.app_context():
        print("📋 Creating token_blacklist table...")
        db.create_all()
        print("✅ Migration complete - token_blacklist table created")


if __name__ == '__main__':
    migrate()
