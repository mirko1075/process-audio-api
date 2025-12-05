"""WebSocket handler for real-time audio streaming with Auth0 authentication.

This module provides WebSocket handlers that support BOTH:
1. Auth0 JWT tokens (primary)
2. Session tokens (fallback for mobile app compatibility)

Features:
- Dynamic language selection via query parameter
- Deepgram Nova-2 real-time transcription
- Multi-language support (30+ languages)
"""
import logging
import base64
from flask_socketio import emit
from datetime import datetime

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions
)
from utils.config import get_app_config
from flask_app.auth.auth0 import verify_websocket_token, Auth0Error, ALLOW_INSECURE_SESSION_AUTH
from flask_app.api.auth import is_valid_session, get_session_info

logger = logging.getLogger(__name__)

# Supported languages for Deepgram Nova-2 transcription
# Complete list of languages supported by Deepgram's Nova-2 model
SUPPORTED_LANGUAGES = [
    "en",  # English
    "es",  # Spanish
    "fr",  # French
    "it",  # Italian
    "de",  # German
    "pt",  # Portuguese
    "nl",  # Dutch
    "hi",  # Hindi
    "ja",  # Japanese
    "ko",  # Korean
    "zh",  # Chinese
    "sv",  # Swedish
    "no",  # Norwegian
    "da",  # Danish
    "fi",  # Finnish
    "pl",  # Polish
    "ru",  # Russian
    "tr",  # Turkish
    "ar",  # Arabic
    "el",  # Greek
    "he",  # Hebrew
    "cs",  # Czech
    "uk",  # Ukrainian
    "ro",  # Romanian
    "hu",  # Hungarian
    "id",  # Indonesian
    "ms",  # Malay
    "th",  # Thai
    "vi",  # Vietnamese
]

# Default language if not specified or invalid
DEFAULT_LANGUAGE = "en"

# Store active connections
active_connections = {}


def authenticate_websocket(auth: dict) -> dict:
    """Authenticate WebSocket connection with Auth0 JWT (required in production).

    In production, ONLY Auth0 JWT tokens are accepted for security.
    Session token fallback is available ONLY when ALLOW_INSECURE_SESSION_AUTH=true
    (development/testing only).

    Args:
        auth: Authentication dict from SocketIO connection

    Returns:
        dict with user_id and auth_type

    Raises:
        Exception if authentication fails
    """
    if not auth or 'token' not in auth:
        raise Exception("No authentication token provided")

    token = auth['token']

    # Try Auth0 JWT first (REQUIRED in production)
    try:
        payload = verify_websocket_token(token)
        return {
            'user_id': payload.get('sub'),
            'email': payload.get('email'),
            'auth_type': 'auth0',
            'payload': payload
        }
    except Auth0Error as e:
        logger.debug(f"Auth0 JWT verification failed: {e.message}")

    # Fallback to session token ONLY if explicitly enabled (DEV ONLY)
    if ALLOW_INSECURE_SESSION_AUTH:
        logger.warning(
            "⚠️  Using insecure session token fallback - this should NOT be enabled in production!"
        )
        try:
            if is_valid_session(token):
                session_info = get_session_info(token)
                return {
                    'user_id': session_info['user_id'],
                    'username': session_info.get('username'),
                    'auth_type': 'session',
                    'payload': session_info
                }
        except Exception as e:
            logger.debug(f"Session token verification failed: {e}")
    else:
        logger.info(
            "Session token fallback disabled (secure mode). "
            "Only Auth0 JWT tokens are accepted."
        )

    # Authentication failed
    raise Exception(
        "Invalid or expired authentication token. "
        "Please provide a valid Auth0 JWT token."
    )


def init_audio_stream_handlers(socketio):
    """Initialize WebSocket event handlers for audio streaming with Auth0.

    Args:
        socketio: Flask-SocketIO instance
    """

    @socketio.on('connect', namespace='/audio-stream')
    def handle_connect(auth):
        """Handle new WebSocket connection with Auth0 or session authentication.
        
        Supports dynamic language selection via query parameter:
        - wss://.../audio-stream?lang=it
        - Defaults to 'en' if not provided or invalid
        """
        try:
            # Authenticate connection
            user_info = authenticate_websocket(auth)
            user_id = user_info['user_id']
            auth_type = user_info['auth_type']

            logger.info(f"WebSocket connected: user_id={user_id}, auth_type={auth_type}")

            # Initialize Deepgram streaming connection
            try:
                config = get_app_config()
                dg_client = DeepgramClient(config.deepgram.api_key)
                dg_connection = dg_client.listen.live.v("1")

                # Extract and validate language from query parameters
                from flask import request
                requested_lang = request.args.get('lang', DEFAULT_LANGUAGE)
                
                # Validate language - default to English if invalid
                if requested_lang not in SUPPORTED_LANGUAGES:
                    logger.warning(
                        f"Invalid language '{requested_lang}' requested by user {user_id}. "
                        f"Defaulting to '{DEFAULT_LANGUAGE}'"
                    )
                    language = DEFAULT_LANGUAGE
                else:
                    language = requested_lang
                
                logger.info(f"Language set to '{language}' for user {user_id}")

                # Store connection info
                active_connections[request.sid] = {
                    'user_id': user_id,
                    'auth_type': auth_type,
                    'user_info': user_info,
                    # token validated but not stored for security
                    'dg_connection': dg_connection,
                    'language': language,  # Store selected language
                    'connected_at': datetime.utcnow().isoformat(),
                    'is_deepgram_open': False
                }

                # Setup Deepgram event handlers
                def on_message(self, result, **kwargs):
                    """Handle transcription results from Deepgram."""
                    try:
                        sentence = result.channel.alternatives[0].transcript

                        if len(sentence) == 0:
                            return

                        # Check if this is a final result
                        is_final = result.is_final

                        # Get confidence score
                        confidence = result.channel.alternatives[0].confidence if hasattr(
                            result.channel.alternatives[0], 'confidence'
                        ) else 0.0

                        # Send transcription back to client
                        emit('transcription', {
                            'transcript': sentence,
                            'is_final': is_final,
                            'confidence': confidence,
                            'timestamp': datetime.utcnow().isoformat()
                        }, namespace='/audio-stream')

                        logger.debug(f"Transcription sent: {sentence[:50]}... (is_final={is_final})")

                    except Exception as e:
                        logger.error(f"Error processing transcription result: {e}")
                        emit('error', {
                            'message': 'Error processing transcription',
                            'timestamp': datetime.utcnow().isoformat()
                        }, namespace='/audio-stream')

                def on_error(self, error, **kwargs):
                    """Handle errors from Deepgram."""
                    logger.error(f"Deepgram error: {error}")
                    emit('error', {
                        'message': 'Transcription service error',
                        'timestamp': datetime.utcnow().isoformat()
                    }, namespace='/audio-stream')

                # Register event handlers
                dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
                dg_connection.on(LiveTranscriptionEvents.Error, on_error)

                # Configure Deepgram options with dynamic language
                options = LiveOptions(
                    model="nova-2",
                    language=language,  # Use dynamically selected language
                    smart_format=True,
                    punctuate=True,
                    interim_results=True,
                    encoding="linear16",
                    sample_rate=16000
                )

                # Start Deepgram connection
                if dg_connection.start(options):
                    active_connections[request.sid]['is_deepgram_open'] = True
                    logger.info(f"Deepgram connection started for user: {user_id} with language: {language}")
                else:
                    logger.error("Failed to start Deepgram connection")
                    return False

                # Emit success message with language confirmation
                emit('connected', {
                    'message': 'Successfully connected to audio streaming service',
                    'user_id': user_id,
                    'auth_type': auth_type,
                    'language': language,  # Confirm language to client
                    'timestamp': datetime.utcnow().isoformat()
                }, namespace='/audio-stream')

                return True

            except Exception as e:
                logger.error(f"Error initializing Deepgram connection: {e}")
                emit('error', {
                    'message': f'Failed to initialize transcription service: {str(e)}',
                    'timestamp': datetime.utcnow().isoformat()
                }, namespace='/audio-stream')
                return False

        except Exception as e:
            logger.warning(f"Connection rejected: {str(e)}")
            emit('error', {
                'message': f'Connection rejected: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/audio-stream')
            return False

    @socketio.on('audio_chunk', namespace='/audio-stream')
    def handle_audio_chunk(data):
        """Handle incoming audio chunk for transcription."""
        from flask import request

        if request.sid not in active_connections:
            logger.warning("Audio chunk received from unknown connection")
            emit('error', {
                'message': 'Connection not initialized',
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/audio-stream')
            return

        try:
            connection_info = active_connections[request.sid]
            dg_connection = connection_info['dg_connection']

            # Extract audio data
            audio_chunk = data.get('audio_chunk')
            if not audio_chunk:
                logger.warning("Empty audio chunk received")
                return

            # Decode Base64 audio data
            try:
                audio_bytes = base64.b64decode(audio_chunk)
            except Exception as e:
                logger.error(f"Failed to decode audio data: {e}")
                emit('error', {
                    'message': 'Invalid audio data format',
                    'timestamp': datetime.utcnow().isoformat()
                }, namespace='/audio-stream')
                return

            # Send to Deepgram
            if connection_info.get('is_deepgram_open'):
                dg_connection.send(audio_bytes)
                logger.debug(f"Sent {len(audio_bytes)} bytes to Deepgram")
            else:
                logger.warning("Deepgram connection not open, cannot send audio")
                emit('error', {
                    'message': 'Transcription service not ready',
                    'timestamp': datetime.utcnow().isoformat()
                }, namespace='/audio-stream')

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            emit('error', {
                'message': 'Error processing audio data',
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/audio-stream')

    @socketio.on('stop_streaming', namespace='/audio-stream')
    def handle_stop_streaming():
        """Stop audio streaming and close Deepgram connection."""
        from flask import request

        if request.sid not in active_connections:
            logger.warning("Stop streaming called for unknown connection")
            return

        try:
            connection_info = active_connections[request.sid]
            user_id = connection_info['user_id']

            # Close Deepgram connection
            dg_connection = connection_info['dg_connection']
            if connection_info.get('is_deepgram_open'):
                dg_connection.finish()
                connection_info['is_deepgram_open'] = False

            logger.info(f"Streaming stopped for user: {user_id}")

            emit('streaming_stopped', {
                'message': 'Streaming stopped successfully',
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/audio-stream')

        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")

    @socketio.on('disconnect', namespace='/audio-stream')
    def handle_disconnect():
        """Handle WebSocket disconnection and cleanup."""
        from flask import request

        if request.sid in active_connections:
            connection_info = active_connections[request.sid]
            user_id = connection_info['user_id']
            try:
                # Close Deepgram connection
                dg_connection = connection_info['dg_connection']
                if connection_info.get('is_deepgram_open'):
                    dg_connection.finish()
                    connection_info['is_deepgram_open'] = False
                logger.info(f"WebSocket disconnected: user_id={user_id}")
            except Exception as e:
                logger.error(f"Error during disconnect cleanup: {e}")
            finally:
                # Always remove from active connections to prevent memory leaks
                del active_connections[request.sid]
