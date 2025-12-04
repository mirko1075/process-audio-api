#!/bin/bash

echo "🧪 Testing Python Detection Logic"
echo "================================="
echo

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Script directory: $SCRIPT_DIR"
echo "📁 Project root: $PROJECT_ROOT"
echo

# Test 1: Check if .venv exists
if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    echo "✅ Found project virtual environment: $PROJECT_ROOT/.venv/bin/python"
else
    echo "❌ No project virtual environment found at: $PROJECT_ROOT/.venv/bin/python"
fi

# Test 2: Check VIRTUAL_ENV
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "✅ Active virtual environment: $VIRTUAL_ENV"
else
    echo "ℹ️  No active virtual environment (VIRTUAL_ENV not set)"
fi

# Test 3: Check python3 availability
if command -v python3 &> /dev/null; then
    echo "✅ python3 available: $(which python3)"
else
    echo "❌ python3 not found in PATH"
fi

# Test 4: Check python availability
if command -v python &> /dev/null; then
    echo "✅ python available: $(which python)"
else
    echo "❌ python not found in PATH"
fi

echo
echo "🐍 Python Detection Priority:"
echo "   1. Project .venv/bin/python (if exists)"
echo "   2. python (if VIRTUAL_ENV is set)"
echo "   3. python3 (if available)"
echo "   4. python (fallback)"
echo

# Final selection logic
if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
    echo "🎯 Selected: Project virtual environment"
elif [[ -n "$VIRTUAL_ENV" ]]; then
    PYTHON_CMD="python"
    echo "🎯 Selected: Active virtual environment"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "🎯 Selected: System python3"
else
    PYTHON_CMD="python"
    echo "🎯 Selected: System python (fallback)"
fi

echo "🐍 Final Python command: $PYTHON_CMD"
echo "📍 Python version: $($PYTHON_CMD --version 2>&1)"