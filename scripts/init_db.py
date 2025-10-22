#!/usr/bin/env python3
"""Database initialization script."""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def is_safe_environment():
    """Check if it's safe to perform destructive database operations."""
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    app_env = os.environ.get('APP_ENV', '').lower()
    database_url = os.environ.get('DATABASE_URL', '')
    
    # Safe environments
    safe_envs = ['development', 'dev', 'testing', 'test', 'local']
    
    # Check environment variables
    if flask_env in safe_envs or app_env in safe_envs:
        return True
    
    # Check if using local development database
    if any(indicator in database_url.lower() for indicator in ['localhost', '127.0.0.1', 'sqlite']):
        return True
    
    return False

def confirm_destructive_action():
    """Get user confirmation for destructive database operations."""
    print("⚠️  WARNING: This will DELETE ALL existing data in the database!")
    print("🗄️  Database URL:", os.environ.get('DATABASE_URL', 'Not set'))
    print("🔧 Environment:", os.environ.get('FLASK_ENV', 'Not set'))
    print()
    
    response = input("Type 'DELETE ALL DATA' to confirm (anything else to cancel): ")
    return response == 'DELETE ALL DATA'

def init_database(force_unsafe=False):
    """Initialize database and create admin user.
    
    Args:
        force_unsafe: If True, skip safety checks (use with extreme caution)
    """
    try:
        from flask_app import create_app
        from models import db
        from models.user import User
        
        # Safety checks
        if not force_unsafe:
            if not is_safe_environment():
                print("🚨 SAFETY CHECK FAILED!")
                print("   This appears to be a production environment.")
                print("   Set FLASK_ENV=development or APP_ENV=development to proceed.")
                print("   Or use --force-unsafe flag (NOT RECOMMENDED).")
                return False
            
            if not confirm_destructive_action():
                print("❌ Operation cancelled by user.")
                return False
        
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

def create_tables_only():
    """Create database tables without dropping existing data (safe operation)."""
    try:
        from flask_app import create_app
        from models import db
        
        app = create_app()
        
        with app.app_context():
            print("🗄️  Creating database tables (preserving existing data)...")
            db.create_all()
            
            print("✅ Database tables created successfully!")
            print("💡 Note: Existing data was preserved.")
            
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize database with safety checks')
    parser.add_argument('--test-user', action='store_true', 
                       help='Create test user only (safe operation)')
    parser.add_argument('--force-unsafe', action='store_true',
                       help='Skip all safety checks (DANGEROUS - use only for development)')
    parser.add_argument('--create-only', action='store_true',
                       help='Create tables without dropping (safe operation)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.test_user:
        create_test_user()
    elif args.create_only:
        create_tables_only()
    else:
        init_database(force_unsafe=args.force_unsafe)