#!/bin/bash

echo "🧪 Testing Database Safety Features"
echo "=================================="
echo

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check for virtual environment and use appropriate Python command
# Priority order:
# 1. Project's .venv/bin/python (if exists)
# 2. python (if VIRTUAL_ENV is active)
# 3. python3 (if available in PATH)
# 4. python (fallback)
if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
elif [[ -n "$VIRTUAL_ENV" ]]; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "🐍 Using Python: $PYTHON_CMD"
echo

# Change to project root to ensure relative paths work
cd "$PROJECT_ROOT"

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