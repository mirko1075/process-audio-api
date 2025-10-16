#!/usr/bin/env python3
"""Database initialization script."""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def init_database():
    """Initialize database and create admin user."""
    try:
        from flask_app import create_app
        from models import db
        from models.user import User
        
        # Create app with database support
        app = create_app()
        
        with app.app_context():
            print("🗄️  Dropping existing tables...")
            db.drop_all()
            
            print("🗄️  Creating database tables...")
            db.create_all()
            
            print("👤 Creating admin user...")
            admin_user = User(
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                company='System',
                plan='enterprise',
                email_verified=True
            )
            admin_user.set_password('admin123')
            
            db.session.add(admin_user)
            db.session.commit()
            
            # Generate admin API key
            admin_api_key = admin_user.generate_api_key("Admin API Key")
            
            print("✅ Database initialized successfully!")
            print()
            print("🔑 Admin Credentials:")
            print(f"   Email: admin@example.com")
            print(f"   Password: admin123")
            print(f"   API Key: {admin_api_key}")
            print()
            print("📋 Next Steps:")
            print("   1. Start the application: docker-compose up")
            print("   2. Test auth endpoint: POST /auth/login")
            print("   3. Create new users via: POST /auth/register")
            print("   4. Use JWT or API keys for authentication")
            
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        return False
    
    return True

def create_test_user():
    """Create a test user for development."""
    try:
        from flask_app import create_app
        from models import db
        from models.user import User
        
        app = create_app()
        
        with app.app_context():
            # Check if test user exists
            test_user = User.query.filter_by(email='test@example.com').first()
            if test_user:
                print("⚠️  Test user already exists")
                return
            
            print("👤 Creating test user...")
            test_user = User(
                email='test@example.com',
                first_name='Test',
                last_name='User',
                company='Development',
                plan='pro',
                email_verified=True
            )
            test_user.set_password('test123')
            
            db.session.add(test_user)
            db.session.commit()
            
            # Generate test API key
            test_api_key = test_user.generate_api_key("Development API Key")
            
            print("✅ Test user created!")
            print(f"   Email: test@example.com")
            print(f"   Password: test123")
            print(f"   API Key: {test_api_key}")
            
    except Exception as e:
        print(f"❌ Error creating test user: {str(e)}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test-user':
        create_test_user()
    else:
        init_database()