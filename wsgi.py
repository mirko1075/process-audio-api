"""WSGI entry point for production deployment with gunicorn."""

from flask_app import create_app

# Create Flask app and SocketIO instance
app, socketio = create_app()

# Export app for gunicorn
# Gunicorn with eventlet worker will use this app instance
# and SocketIO will be properly initialized
application = app
