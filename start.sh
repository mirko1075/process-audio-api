#!/bin/bash
# Start the application
gunicorn -w 2 -b 0.0.0.0:$PORT --preload app:app --timeout 900