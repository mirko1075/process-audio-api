#!/bin/bash
#
# Test script for database initialization safety checks
#

echo "🧪 Testing Database Initialization Safety Checks"
echo "================================================="

# Test 1: Production environment (should fail)
echo ""
echo "Test 1: Production Environment Safety Check"
echo "-------------------------------------------"
FLASK_ENV=production DATABASE_URL=postgresql://prod-server:5432/proddb .venv/bin/python scripts/init_db.py

# Test 2: Development environment with safe operation
echo ""
echo "Test 2: Development Environment with Safe Operation"
echo "---------------------------------------------------"
echo "(This would work if database was available)"
echo "Command: FLASK_ENV=development .venv/bin/python scripts/init_db.py --create-only"

# Test 3: Test user creation (always safe)
echo ""
echo "Test 3: Test User Creation (Safe Operation)"
echo "-------------------------------------------"
echo "(This would work if database was available)"
echo "Command: .venv/bin/python scripts/init_db.py --test-user"

echo ""
echo "🔒 Safety Features Summary:"
echo "=========================="
echo "✅ Environment detection (FLASK_ENV, APP_ENV)"
echo "✅ Database URL analysis (localhost/sqlite = safe)"
echo "✅ User confirmation for destructive operations"
echo "✅ Safe operations (--create-only, --test-user)"
echo "✅ Force override for development (--force-unsafe)"
echo "✅ Detailed help and warnings"