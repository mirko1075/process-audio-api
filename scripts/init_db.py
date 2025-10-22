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
    """Check if it's safe to drop tables (development environment)."""
    flask_env = os.getenv('FLASK_ENV', '').lower()
    environment = os.getenv('ENVIRONMENT', '').lower()
    
    # Consider safe if explicitly set to development
    safe_envs = ['development', 'dev', 'test', 'testing', 'local']
    
    return flask_env in safe_envs or environment in safe_envs

def confirm_destructive_action():
    """Ask user for confirmation before destructive database operations."""
    print("⚠️  WARNING: This will DELETE ALL existing data in the database!")
    print("   This action cannot be undone.")
    print()
    
    response = input("Are you sure you want to continue? Type 'yes' to confirm: ").strip().lower()
    return response == 'yes'

def create_tables_only():
    """Create tables without dropping existing ones (safe mode)."""
    try:
        from flask_app import create_app
        from models import db
        
        app = create_app()
        
        with app.app_context():
            print("🗄️  Creating database tables (safe mode - no data loss)...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False
    
    return True

def init_database(force_drop=False):
    """Initialize database and create admin user.
    
    Args:
        force_drop: If True, skip safety checks and force table dropping
    """
    try:
        from flask_app import create_app
        from models import db
        from models.user import User
        
        # Create app with database support
        app = create_app()
        
        with app.app_context():
            # Safety check for production environments
            if not force_drop:
                if not is_safe_environment():
                    print("🚨 PRODUCTION ENVIRONMENT DETECTED!")
                    print("   Environment variables suggest this is not a development environment.")
                    print("   Current FLASK_ENV:", os.getenv('FLASK_ENV', 'not set'))
                    print("   Current ENVIRONMENT:", os.getenv('ENVIRONMENT', 'not set'))
                    print()
                    print("   Options:")
                    print("   1. Run with --force to override safety checks")
                    print("   2. Run with --safe to create tables without dropping existing data")
                    print("   3. Set FLASK_ENV=development or ENVIRONMENT=development")
                    return False
                
                if not confirm_destructive_action():
                    print("❌ Operation cancelled by user.")
                    return False
            
            print("🗄️  Dropping existing tables...")
            db.drop_all()
            
            print("🗄️  Creating database tables...")
            db.create_all()
            
            print("👤 Creating admin user...")
            
            # Check if admin user already exists
            existing_admin = User.query.filter_by(email='admin@example.com').first()
            if existing_admin:
                print("⚠️  Admin user already exists, skipping creation...")
            else:
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
            test_user.set_password('test1234')
            
            db.session.add(test_user)
            db.session.commit()
            
            # Generate test API key
            test_api_key = test_user.generate_api_key("Development API Key")
            
            print("✅ Test user created!")
            print(f"   Email: test@example.com")
            print(f"   Password: test1234")
            print(f"   API Key: {test_api_key}")
            
    except Exception as e:
        print(f"❌ Error creating test user: {str(e)}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test-user':
            create_test_user()
        elif sys.argv[1] == '--safe':
            print("🔒 Running in safe mode (no data loss)")
            create_tables_only()
        elif sys.argv[1] == '--force':
            print("⚠️  Force mode: Bypassing safety checks")
            init_database(force_drop=True)
        elif sys.argv[1] == '--help':
            print("Database Initialization Script")
            print()
            print("Usage:")
            print("  python scripts/init_db.py            # Interactive initialization with safety checks")
            print("  python scripts/init_db.py --safe     # Create tables only (no data loss)")
            print("  python scripts/init_db.py --force    # Force initialization (bypass safety checks)")
            print("  python scripts/init_db.py test-user  # Create test user only")
            print("  python scripts/init_db.py --help     # Show this help message")
            print()
            print("Environment Variables:")
            print("  FLASK_ENV=development    # Marks environment as safe for table dropping")
            print("  ENVIRONMENT=development  # Alternative environment marker")
        else:
            print(f"❌ Unknown argument: {sys.argv[1]}")
            print("   Use --help to see available options")
    else:
        # Default behavior with safety checks
        init_database()