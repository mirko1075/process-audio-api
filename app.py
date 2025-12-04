"""Main application entry point using Flask application factory pattern."""

import os
from flask_app import create_app

# Create Flask application and SocketIO using application factory
app, socketio = create_app()

if __name__ == '__main__':
    # Get port from environment variable (for Render deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Development server configuration
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') != 'production',
        allow_unsafe_werkzeug=os.environ.get('FLASK_ENV') != 'production'
    )
