# WebSocket Dynamic Language Support

## Overview

The WebSocket audio streaming endpoint now supports **dynamic language selection** for real-time transcription using Deepgram's Nova-2 model.

## Usage

### Connection URL with Language Parameter

```javascript
// Connect with specific language
const socket = io('wss://your-api.com/audio-stream', {
  auth: {
    token: 'your-auth-token'
  },
  query: {
    lang: 'it'  // Italian transcription
  }
});
```

### Default Behavior

If no language is specified or an invalid language code is provided, the system defaults to **English (`en`)**.

```javascript
// These will all default to English
const socket1 = io('wss://your-api.com/audio-stream', {
  auth: { token: 'token' }
  // No lang parameter → defaults to 'en'
});

const socket2 = io('wss://your-api.com/audio-stream', {
  auth: { token: 'token' },
  query: { lang: 'invalid-code' }  // Invalid → defaults to 'en'
});
```

## Supported Languages

The system supports **29 languages** via Deepgram's Nova-2 model:

| Code | Language | Code | Language |
|------|----------|------|----------|
| `en` | English | `es` | Spanish |
| `fr` | French | `it` | Italian |
| `de` | German | `pt` | Portuguese |
| `nl` | Dutch | `hi` | Hindi |
| `ja` | Japanese | `ko` | Korean |
| `zh` | Chinese | `sv` | Swedish |
| `no` | Norwegian | `da` | Danish |
| `fi` | Finnish | `pl` | Polish |
| `ru` | Russian | `tr` | Turkish |
| `ar` | Arabic | `el` | Greek |
| `he` | Hebrew | `cs` | Czech |
| `uk` | Ukrainian | `ro` | Romanian |
| `hu` | Hungarian | `id` | Indonesian |
| `ms` | Malay | `th` | Thai |
| `vi` | Vietnamese | | |

## Connection Response

Upon successful connection, the server confirms the selected language:

```json
{
  "message": "Successfully connected to audio streaming service",
  "user_id": "user123",
  "auth_type": "auth0",
  "language": "it",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Examples

### JavaScript/TypeScript (Browser/Node.js)

```javascript
import io from 'socket.io-client';

// Italian transcription
const italianSocket = io('wss://api.example.com/audio-stream', {
  auth: {
    token: authToken
  },
  query: {
    lang: 'it'
  }
});

italianSocket.on('connected', (data) => {
  console.log(`Connected with language: ${data.language}`);
  // Output: "Connected with language: it"
});

// Spanish transcription
const spanishSocket = io('wss://api.example.com/audio-stream', {
  auth: {
    token: authToken
  },
  query: {
    lang: 'es'
  }
});

// Send audio for transcription
italianSocket.emit('audio_data', audioBuffer);
```

### Python Client

```python
import socketio

sio = socketio.Client()

# Connect with French transcription
@sio.event
def connect():
    print('Connection established')

@sio.on('connected')
def on_connected(data):
    print(f"Connected with language: {data['language']}")
    # Output: "Connected with language: fr"

@sio.on('transcription')
def on_transcription(data):
    print(f"Transcript: {data['transcript']}")
    print(f"Is final: {data['is_final']}")

# Connect with language parameter
sio.connect(
    'wss://api.example.com',
    namespaces=['/audio-stream'],
    auth={'token': 'your-auth-token'},
    headers={'lang': 'fr'}
)

# Send audio data
sio.emit('audio_data', audio_bytes, namespace='/audio-stream')
```

### React Native (Mobile App)

```typescript
import io from 'socket.io-client';

const connectAudioStream = (language: string = 'en') => {
  const socket = io('wss://api.example.com/audio-stream', {
    auth: {
      token: userAuthToken
    },
    query: {
      lang: language
    },
    transports: ['websocket']
  });

  socket.on('connected', (data) => {
    console.log('Connected:', data);
    Alert.alert('Success', `Transcription started in ${data.language}`);
  });

  socket.on('transcription', (data) => {
    if (data.is_final) {
      console.log('Final transcript:', data.transcript);
    }
  });

  return socket;
};

// Usage
const italianSocket = connectAudioStream('it');
const englishSocket = connectAudioStream('en');
```

## Server Logs

The server logs language selection for debugging:

```
INFO - WebSocket connected: user_id=auth0|123, auth_type=auth0
INFO - Language set to 'it' for user auth0|123
INFO - Deepgram connection started for user: auth0|123 with language: it
```

If an invalid language is requested:

```
WARNING - Invalid language 'xyz' requested by user auth0|123. Defaulting to 'en'
INFO - Language set to 'en' for user auth0|123
```

## Architecture

### Code Structure

```python
# In flask_app/sockets/audio_stream_auth0.py

# Constants
SUPPORTED_LANGUAGES = ["en", "es", "fr", "it", "de", ...]
DEFAULT_LANGUAGE = "en"

# Connection handler
@socketio.on('connect', namespace='/audio-stream')
def handle_connect(auth):
    # Extract language from query parameters
    requested_lang = request.args.get('lang', DEFAULT_LANGUAGE)
    
    # Validate
    if requested_lang not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    else:
        language = requested_lang
    
    # Store in session
    active_connections[request.sid]['language'] = language
    
    # Configure Deepgram with selected language
    options = LiveOptions(
        model="nova-2",
        language=language,  # Dynamic language
        ...
    )
```

### Session Storage

Each WebSocket connection stores:

```python
active_connections[session_id] = {
    'user_id': 'auth0|123',
    'auth_type': 'auth0',
    'user_info': {...},
    'dg_connection': deepgram_connection,
    'language': 'it',  # ← Stored language
    'connected_at': '2024-01-15T10:30:00Z',
    'is_deepgram_open': True
}
```

## Security

- **Authentication Required**: All connections must provide a valid Auth0 JWT or session token
- **Token Not Stored**: Authentication tokens are validated at connection time but not stored in session
- **Language Validation**: Only whitelisted languages are accepted to prevent injection attacks

## Error Handling

### Invalid Language Code

```json
// Server logs warning and defaults to English
{
  "message": "Successfully connected to audio streaming service",
  "language": "en",  // Defaulted from invalid "xyz"
  ...
}
```

### Authentication Failure

```json
{
  "message": "Connection rejected: Invalid or expired authentication token",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Testing

### Manual Testing with wscat

```bash
# Install wscat
npm install -g wscat

# Connect with language parameter
wscat -c "wss://api.example.com/audio-stream?lang=it" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Server responds with:
# {"message": "Successfully connected...", "language": "it"}
```

### Automated Testing

```python
# In tests/test_websocket_language.py
import pytest
from socketio import SimpleClient

def test_italian_language_selection():
    client = SimpleClient()
    client.connect(
        'http://localhost:5000',
        namespace='/audio-stream',
        auth={'token': valid_token},
        headers={'lang': 'it'}
    )
    
    response = client.receive()
    assert response['language'] == 'it'
```

## Future Enhancements

- [ ] Add language auto-detection based on audio content
- [ ] Support language switching mid-session
- [ ] Add language-specific formatting rules
- [ ] Implement dialect support (e.g., `en-US`, `en-GB`)
- [ ] Add translation alongside transcription

## References

- [Deepgram Nova-2 Language Support](https://developers.deepgram.com/docs/languages)
- [Socket.IO Query Parameters](https://socket.io/docs/v4/client-api/#socketquery)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
