"""Main application entry point using Flask application factory pattern."""

from flask_app import create_app

# Create Flask application and SocketIO using application factory
app, socketio = create_app()

if __name__ == '__main__':
    # Development server configuration
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True  # For development only
    )
