#!/bin/bash
cp /etc/secrets/google-credentials.json ./google/
# Start the application
gunicorn -w 1 -b 0.0.0.0:$PORT --preload app:app