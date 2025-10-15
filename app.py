"""Main application entry point using Flask application factory pattern."""

from flask_app import create_app

# Create Flask application using application factory
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
