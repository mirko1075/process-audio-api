import os
import logging
import time
from flask import Flask, g, request
from dotenv import load_dotenv

def create_app():
    load_dotenv()
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    # Configure AssemblyAI client
    import assemblyai as aai
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
    aai.settings.api_key = ASSEMBLYAI_API_KEY

    # Register blueprints
    from .auth import require_api_key
    from .blueprints.health import health_bp
    from .blueprints.transcription import transcription_bp
    from .blueprints.translation import translation_bp
    from .blueprints.documents import documents_bp
    from .blueprints.reporting import reporting_bp
    from .blueprints.sentiment import sentiment_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(transcription_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(reporting_bp)
    app.register_blueprint(sentiment_bp)

    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_execution_time(response):
        if hasattr(g, 'start_time'):
            execution_time = time.time() - g.start_time
            print(f"Endpoint: {request.path} | Method: {request.method} | Time: {execution_time:.4f} sec")
            response.headers["X-Execution-Time"] = str(execution_time)
        return response

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)