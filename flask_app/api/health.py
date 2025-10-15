"""Health check API blueprint."""
from flask import Blueprint, jsonify
import logging

bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)


@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service is running."""
    logger.info("Health check requested")
    
    return jsonify({
        "status": "healthy",
        "service": "Audio Transcription API",
        "version": "1.0.0"
    })


@bp.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "service": "Audio Transcription API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "transcription": {
                "deepgram": "/transcriptions/deepgram",
                "whisper": "/transcriptions/whisper",
                "assemblyai": "/transcriptions/assemblyai"
            },
            "translation": {
                "openai": "/translations/openai",
                "google": "/translations/google"
            },
            "postprocessing": {
                "sentiment": "/sentiment",
                "documents": "/documents/{format}",
                "reports": "/reports/{format}"
            }
        }
    })