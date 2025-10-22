#!/bin/bash

echo "🧪 Testing Database Safety Features"
echo "=================================="
echo

# Set the Python path
PYTHON_CMD="/home/msiddi/Documents/personal/python/render-audio-transcription/.venv/bin/python"

# Test 1: Help functionality
echo "📖 Test 1: Help functionality"
$PYTHON_CMD scripts/init_db.py --help
echo

# Test 2: Production environment detection
echo "🚨 Test 2: Production environment detection"
FLASK_ENV=production $PYTHON_CMD scripts/init_db.py 2>/dev/null | head -10
echo

# Test 3: Safe mode
echo "🔒 Test 3: Safe mode (no data loss)"
$PYTHON_CMD scripts/init_db.py --safe 2>/dev/null | head -5
echo

# Test 4: Development environment (should allow dropping)
echo "🔧 Test 4: Development environment detection"
FLASK_ENV=development $PYTHON_CMD scripts/init_db.py 2>/dev/null | head -10
echo

echo "✅ All safety tests completed!"