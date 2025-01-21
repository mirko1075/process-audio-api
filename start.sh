#!/bin/bash

# Start the application
gunicorn app:app --bind 0.0.0.0:$PORT  --timeout 120 --workers 2 --log-level debug