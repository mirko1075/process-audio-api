#!/usr/bin/env python3
"""Add jobs and artifacts tables for SaaS job persistence."""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask_app import create_app
from models import db

def migrate():
    """Create jobs and artifacts tables."""
    app, socketio = create_app()
    with app.app_context():
        print("Creating jobs and artifacts tables...")
        db.create_all()
        print("✅ Migration complete - jobs and artifacts tables created")

if __name__ == '__main__':
    migrate()
