#!/bin/bash
# Start the application
export PYTHONPATH=src:$PYTHONPATH
gunicorn -w 2 -b 0.0.0.0:$PORT --preload 'audio_api.application.factory:create_app()' --timeout 900