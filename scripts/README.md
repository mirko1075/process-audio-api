# Database Scripts

This directory contains scripts for database management and testing.

## Scripts

### `init_db.py`
Database initialization script with comprehensive safety features.

**Usage:**
```bash
# Interactive initialization with safety checks
python scripts/init_db.py

# Create tables only (safe mode - no data loss)
python scripts/init_db.py --safe

# Force initialization (bypass safety checks)
python scripts/init_db.py --force

# Create test user only
python scripts/init_db.py test-user

# Show help
python scripts/init_db.py --help
```

**Environment Variables:**
- `FLASK_ENV=development` - Marks environment as safe for table dropping
- `ENVIRONMENT=development` - Alternative environment marker

### `test_db_safety.sh`
Test script to verify database safety features work correctly.

**Usage:**
```bash
# Run from project root
./scripts/test_db_safety.sh

# Or from any directory
/path/to/project/scripts/test_db_safety.sh
```

### `test_python_detection.sh`
Debug script to test Python environment detection logic.

**Usage:**
```bash
./scripts/test_python_detection.sh
```

## Python Environment Detection

All scripts automatically detect and use the appropriate Python interpreter:

1. **Project virtual environment**: `.venv/bin/python` (preferred)
2. **Active virtual environment**: `python` command (if `VIRTUAL_ENV` is set)
3. **System Python 3**: `python3` command (if available)
4. **System Python**: `python` command (fallback)

## Safety Features

The database initialization script includes multiple safety layers:

- **Environment detection**: Automatically detects production vs development
- **User confirmation**: Requires explicit confirmation for destructive operations
- **Safe mode**: Option to create tables without dropping existing data
- **Force override**: Available for legitimate use cases with `--force` flag

## Development Setup

1. Ensure you have a Python virtual environment activated or use the project's `.venv`
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables for development: `FLASK_ENV=development`
4. Run database initialization: `python scripts/init_db.py`

## Troubleshooting

**Script can't find Python:**
- Make sure you have Python installed
- Activate your virtual environment
- Use the full path to the script if needed

**Permission denied:**
- Make scripts executable: `chmod +x scripts/*.sh`

**Database connection errors:**
- Ensure database is running (Docker: `docker-compose up -d db`)
- Check environment variables are set correctly
- Verify database credentials in your configuration