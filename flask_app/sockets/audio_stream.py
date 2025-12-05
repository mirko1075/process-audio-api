"""WebSocket handler for real-time audio streaming and transcription."""
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
from flask_app.api.auth import is_valid_session, get_session_info

logger = logging.getLogger(__name__)

# Store active connections
active_connections = {}


def init_audio_stream_handlers(socketio):
    """Initialize WebSocket event handlers for audio streaming.

    Args:
        socketio: Flask-SocketIO instance
    """

    @socketio.on('connect', namespace='/audio-stream')
    def handle_connect(auth):
        """Handle new WebSocket connection with authentication."""
        try:
            # Extract token from auth parameter
            if not auth or 'token' not in auth:
                logger.warning("Connection rejected: No authentication token provided")
                return False

            token = auth['token']

            # Validate session token
            if not is_valid_session(token):
                logger.warning(f"Connection rejected: Invalid or expired token")
                return False

            session_info = get_session_info(token)
            user_id = session_info['user_id']

            logger.info(f"WebSocket connected: user_id={user_id}")

            # Initialize Deepgram streaming connection
            try:
                config = get_app_config()
                dg_client = DeepgramClient(config.deepgram.api_key)
                dg_connection = dg_client.listen.live.v("1")

                # Store connection info
                from flask import request
                active_connections[request.sid] = {
                    'user_id': user_id,
                    'token': token,
                    'dg_connection': dg_connection,
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

                        # Send transcription back to client
                        emit('transcription', {
                            'transcript': sentence,
                            'is_final': is_final,
                            'timestamp': datetime.utcnow().isoformat(),
                            'confidence': result.channel.alternatives[0].confidence
                        }, namespace='/audio-stream')

                        logger.debug(f"Transcription sent: {sentence[:50]}... (final={is_final})")

                    except Exception as e:
                        logger.error(f"Error processing Deepgram message: {e}")

                def on_metadata(self, metadata, **kwargs):
                    """Handle metadata from Deepgram."""
                    logger.debug(f"Deepgram metadata received: {metadata}")

                def on_error(self, error, **kwargs):
                    """Handle errors from Deepgram."""
                    logger.error(f"Deepgram error: {error}")
                    emit('error', {
                        'message': 'Transcription service error',
                        'timestamp': datetime.utcnow().isoformat()
                    }, namespace='/audio-stream')

                def on_open(self, open, **kwargs):
                    """Handle Deepgram connection open."""
                    logger.info("Deepgram connection opened")
                    from flask import request
                    if request.sid in active_connections:
                        active_connections[request.sid]['is_deepgram_open'] = True

                def on_close(self, close, **kwargs):
                    """Handle Deepgram connection close."""
                    logger.info("Deepgram connection closed")
                    from flask import request
                    if request.sid in active_connections:
                        active_connections[request.sid]['is_deepgram_open'] = False

                # Register Deepgram event handlers
                dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
                dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
                dg_connection.on(LiveTranscriptionEvents.Error, on_error)
                dg_connection.on(LiveTranscriptionEvents.Open, on_open)
                dg_connection.on(LiveTranscriptionEvents.Close, on_close)

                # Start Deepgram connection with options
                options = LiveOptions(
                    model="nova-2",
                    language="it",  # Italian language
                    smart_format=True,
                    punctuate=True,
                    interim_results=True,
                    encoding="linear16",
                    sample_rate=16000
                )

                if dg_connection.start(options) is False:
                    logger.error("Failed to start Deepgram connection")
                    return False

                # Send connection success message
                emit('connected', {
                    'message': 'Successfully connected to audio streaming service',
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, namespace='/audio-stream')

                return True

            except Exception as e:
                logger.error(f"Failed to initialize Deepgram: {e}")
                emit('error', {
                    'message': 'Failed to initialize transcription service',
                    'timestamp': datetime.utcnow().isoformat()
                }, namespace='/audio-stream')
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False


    @socketio.on('audio_chunk', namespace='/audio-stream')
    def handle_audio_chunk(data):
        """Handle incoming audio chunk from client.

        Expected data format:
        {
            "audio_chunk": "base64_encoded_audio_data",
            "timestamp": "ISO8601_timestamp"
        }
        """
        from flask import request

        if request.sid not in active_connections:
            logger.warning(f"Audio chunk received from unknown connection: {request.sid}")
            emit('error', {
                'message': 'Connection not initialized',
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/audio-stream')
            return

        try:
            # Extract audio data
            audio_base64 = data.get('audio_chunk')
            if not audio_base64:
                logger.warning("Received empty audio chunk")
                return

            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_base64)

            # Get Deepgram connection
            connection_info = active_connections[request.sid]
            dg_connection = connection_info['dg_connection']

            # Check if Deepgram connection is open
            if not connection_info.get('is_deepgram_open'):
                logger.warning("Deepgram connection not open, buffering audio")
                return

            # Send audio to Deepgram
            dg_connection.send(audio_bytes)

            logger.debug(f"Audio chunk sent to Deepgram: {len(audio_bytes)} bytes")

        except base64.binascii.Error as e:
            logger.error(f"Invalid base64 audio data: {e}")
            emit('error', {
                'message': 'Invalid audio data format',
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
        """Handle stop streaming request from client."""
        from flask import request

        if request.sid not in active_connections:
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
            logger.error(f"Error stopping stream: {e}")


    @socketio.on('disconnect', namespace='/audio-stream')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        from flask import request

        if request.sid in active_connections:
            try:
                connection_info = active_connections[request.sid]
                user_id = connection_info['user_id']

                # Close Deepgram connection
                dg_connection = connection_info['dg_connection']
                dg_connection.finish()

                # Remove from active connections
                del active_connections[request.sid]

                logger.info(f"WebSocket disconnected: user_id={user_id}")

            except Exception as e:
                logger.error(f"Error during disconnect cleanup: {e}")
                # Still remove the connection even if cleanup fails
                if request.sid in active_connections:
                    del active_connections[request.sid]
        else:
            logger.warning(f"Disconnect from unknown connection: {request.sid}")
