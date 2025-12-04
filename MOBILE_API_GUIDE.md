# Meeting Minute Streamer - Backend API Guide

Guida completa per integrare l'app React Native con il backend Flask.

## Installazione Dipendenze

Prima di avviare il server, installa le nuove dipendenze:

```bash
pip install -r requirements.txt
```

## Avvio del Server

```bash
python app.py
```

Il server sarà disponibile su `http://localhost:5000`

## Endpoint Disponibili

### 1. Login - Autenticazione

**Endpoint:** `POST http://localhost:5000/auth/login`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "username": "mario_rossi",
  "password": "qualsiasi_password"
}
```

**Risposta di Successo (200):**
```json
{
  "auth_token": "session_abc123xyz...",
  "user_id": "mario_rossi",
  "expires_at": "2025-12-05T12:00:00",
  "message": "Login successful"
}
```

**Risposta di Errore (400):**
```json
{
  "error": "Username is required"
}
```

**Esempio cURL:**
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "mario", "password": "test123"}'
```

---

### 2. Verifica Token

**Endpoint:** `POST http://localhost:5000/auth/verify`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "auth_token": "session_abc123xyz..."
}
```

**Risposta di Successo (200):**
```json
{
  "valid": true,
  "user_id": "mario_rossi",
  "username": "Mario Rossi"
}
```

---

### 3. Logout

**Endpoint:** `POST http://localhost:5000/auth/logout`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "auth_token": "session_abc123xyz..."
}
```

**Risposta di Successo (200):**
```json
{
  "message": "Logout successful"
}
```

---

### 4. WebSocket - Streaming Audio in Tempo Reale

**Endpoint WebSocket:** `ws://localhost:5000/socket.io/?EIO=4&transport=websocket`

**Namespace:** `/audio-stream`

#### Connessione

Quando ti connetti al WebSocket, devi fornire il token di autenticazione:

**Socket.IO Client (React Native):**
```typescript
import io from 'socket.io-client';

const socket = io('http://localhost:5000', {
  path: '/socket.io',
  transports: ['websocket'],
  auth: {
    token: AUTH_TOKEN  // Token ricevuto dal login
  }
});

// Connettersi al namespace specifico
const audioSocket = socket.of('/audio-stream');
```

#### Eventi WebSocket

##### 1. Evento: `connected` (ricevuto dal server)

Ricevi questo evento quando la connessione è stabilita con successo:

```json
{
  "message": "Successfully connected to audio streaming service",
  "user_id": "mario_rossi",
  "timestamp": "2025-12-04T10:30:00"
}
```

**Esempio React Native:**
```typescript
socket.on('connected', (data) => {
  console.log('Connesso:', data.message);
  console.log('User ID:', data.user_id);
});
```

##### 2. Evento: `audio_chunk` (inviato al server)

Invia chunk audio al server per la trascrizione:

**Formato dei dati:**
```json
{
  "audio_chunk": "BASE64_ENCODED_AUDIO_DATA",
  "timestamp": "2025-12-04T10:30:01.500Z"
}
```

**Esempio React Native:**
```typescript
// Quando hai un chunk audio (Buffer o Uint8Array)
const audioBase64 = audioData.toString('base64');

socket.emit('audio_chunk', {
  audio_chunk: audioBase64,
  timestamp: new Date().toISOString()
});
```

**Specifiche Audio:**
- **Encoding:** Linear PCM (linear16)
- **Sample Rate:** 16000 Hz
- **Channels:** Mono (1 canale)
- **Bit Depth:** 16 bit
- **Chunk Size:** Consigliato 500ms - 1000ms

##### 3. Evento: `transcription` (ricevuto dal server)

Ricevi le trascrizioni in tempo reale:

```json
{
  "transcript": "Ciao, come stai?",
  "is_final": false,
  "timestamp": "2025-12-04T10:30:02",
  "confidence": 0.95
}
```

**Campi:**
- `transcript`: Testo trascritto
- `is_final`: `true` se è la trascrizione finale, `false` se è intermedia
- `timestamp`: Timestamp ISO8601
- `confidence`: Livello di confidenza (0.0 - 1.0)

**Esempio React Native:**
```typescript
socket.on('transcription', (data) => {
  if (data.is_final) {
    // Trascrizione finale - aggiungi al testo completo
    console.log('Finale:', data.transcript);
    setFinalTranscript(prev => prev + ' ' + data.transcript);
  } else {
    // Trascrizione intermedia - mostra in preview
    console.log('Intermedia:', data.transcript);
    setInterimTranscript(data.transcript);
  }
});
```

##### 4. Evento: `stop_streaming` (inviato al server)

Ferma lo streaming audio:

```typescript
socket.emit('stop_streaming');
```

**Risposta dal server:**
```json
{
  "message": "Streaming stopped successfully",
  "timestamp": "2025-12-04T10:35:00"
}
```

##### 5. Evento: `streaming_stopped` (ricevuto dal server)

Conferma che lo streaming è stato fermato:

```typescript
socket.on('streaming_stopped', (data) => {
  console.log('Streaming fermato:', data.message);
});
```

##### 6. Evento: `error` (ricevuto dal server)

Ricevi errori dal server:

```json
{
  "message": "Error processing audio data",
  "timestamp": "2025-12-04T10:30:05"
}
```

**Esempio React Native:**
```typescript
socket.on('error', (error) => {
  console.error('Errore server:', error.message);
  Alert.alert('Errore', error.message);
});
```

##### 7. Evento: `disconnect` (gestisci disconnessione)

```typescript
socket.on('disconnect', (reason) => {
  console.log('Disconnesso:', reason);
  // Riconnetti automaticamente se necessario
});
```

---

## Esempio Completo React Native

```typescript
import React, { useState, useEffect } from 'react';
import { View, Button, Text, Alert } from 'react-native';
import io from 'socket.io-client';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';

const AudioStreamingScreen = () => {
  const [socket, setSocket] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [authToken, setAuthToken] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');

  const audioRecorderPlayer = new AudioRecorderPlayer();

  // 1. Login
  const handleLogin = async () => {
    try {
      const response = await fetch('http://localhost:5000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: 'mario',
          password: 'test123'
        })
      });

      const data = await response.json();
      if (data.auth_token) {
        setAuthToken(data.auth_token);
        console.log('Login successful, token:', data.auth_token);
      }
    } catch (error) {
      Alert.alert('Errore Login', error.message);
    }
  };

  // 2. Connetti WebSocket
  const connectWebSocket = () => {
    if (!authToken) {
      Alert.alert('Errore', 'Devi prima effettuare il login');
      return;
    }

    const newSocket = io('http://localhost:5000/audio-stream', {
      transports: ['websocket'],
      auth: {
        token: authToken
      }
    });

    newSocket.on('connected', (data) => {
      console.log('WebSocket connesso:', data.message);
      Alert.alert('Successo', 'Connesso al server di trascrizione');
    });

    newSocket.on('transcription', (data) => {
      if (data.is_final) {
        setFinalTranscript(prev => prev + ' ' + data.transcript);
        setInterimTranscript('');
      } else {
        setInterimTranscript(data.transcript);
      }
    });

    newSocket.on('error', (error) => {
      console.error('WebSocket error:', error);
      Alert.alert('Errore', error.message);
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnesso');
      setIsStreaming(false);
    });

    setSocket(newSocket);
  };

  // 3. Avvia streaming audio
  const startStreaming = async () => {
    if (!socket) {
      Alert.alert('Errore', 'WebSocket non connesso');
      return;
    }

    try {
      // Configura registrazione audio
      const audioPath = 'streaming_audio.wav';
      await audioRecorderPlayer.startRecorder(audioPath, {
        AVEncoderAudioQualityKeyIOS: AVEncoderAudioQualityIOSType.high,
        AVNumberOfChannelsKeyIOS: 1,
        AVFormatIDKeyIOS: AVEncodingOption.lpcm,
        AVSampleRateKeyIOS: 16000,
      });

      // Invia chunk audio ogni 1 secondo
      const interval = setInterval(async () => {
        // Qui dovresti catturare il chunk audio dal recorder
        // Questo è un esempio semplificato
        const audioChunk = await getAudioChunk(); // Implementa questa funzione
        const audioBase64 = audioChunk.toString('base64');

        socket.emit('audio_chunk', {
          audio_chunk: audioBase64,
          timestamp: new Date().toISOString()
        });
      }, 1000);

      setIsStreaming(true);

      // Salva l'interval per poterlo fermare dopo
      setInterval(interval);

    } catch (error) {
      Alert.alert('Errore Recording', error.message);
    }
  };

  // 4. Ferma streaming
  const stopStreaming = async () => {
    if (socket) {
      socket.emit('stop_streaming');
    }

    await audioRecorderPlayer.stopRecorder();
    setIsStreaming(false);

    // Ferma l'interval
    clearInterval(interval);
  };

  // 5. Disconnetti WebSocket
  const disconnectWebSocket = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
    }
  };

  return (
    <View style={{ padding: 20 }}>
      <Button title="Login" onPress={handleLogin} disabled={!!authToken} />
      <Button
        title="Connetti WebSocket"
        onPress={connectWebSocket}
        disabled={!authToken || !!socket}
      />
      <Button
        title={isStreaming ? "Ferma Streaming" : "Avvia Streaming"}
        onPress={isStreaming ? stopStreaming : startStreaming}
        disabled={!socket}
      />
      <Button
        title="Disconnetti"
        onPress={disconnectWebSocket}
        disabled={!socket}
      />

      <Text style={{ marginTop: 20, fontWeight: 'bold' }}>
        Trascrizione Finale:
      </Text>
      <Text>{finalTranscript}</Text>

      <Text style={{ marginTop: 10, fontStyle: 'italic', color: 'gray' }}>
        Trascrizione Intermedia:
      </Text>
      <Text>{interimTranscript}</Text>
    </View>
  );
};

export default AudioStreamingScreen;
```

---

## Formato Audio Richiesto

Per garantire la compatibilità con Deepgram, l'audio deve avere queste specifiche:

- **Encoding:** Linear PCM (linear16)
- **Sample Rate:** 16000 Hz (16 kHz)
- **Channels:** Mono (1 canale)
- **Bit Depth:** 16 bit
- **Container:** Invia i dati raw PCM in Base64

---

## Test con cURL e websocat

### Test Login
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "password": "test123"}'
```

### Test WebSocket (con websocat)

1. Installa websocat: `brew install websocat` (Mac) o scarica da GitHub

2. Connetti al WebSocket:
```bash
# Sostituisci YOUR_TOKEN con il token ricevuto dal login
websocat "ws://localhost:5000/socket.io/?EIO=4&transport=websocket&token=YOUR_TOKEN"
```

---

## Note Importanti

1. **Lingua:** Il server è configurato per l'italiano (`language="it"` in [audio_stream.py:113](flask_app/sockets/audio_stream.py#L113)). Puoi modificarlo se necessario.

2. **Modello Deepgram:** Usa `nova-2`, il modello più avanzato di Deepgram.

3. **Trascrizioni Intermedie:** Il server invia sia trascrizioni intermedie (`is_final: false`) che finali (`is_final: true`). Le intermedie sono utili per mostrare il testo in tempo reale mentre l'utente parla.

4. **Autenticazione:** Il token di sessione scade dopo 24 ore. Puoi modificare la durata in [auth.py:31](flask_app/api/auth.py#L31).

5. **CORS:** Il server accetta connessioni da qualsiasi origine. In produzione, configura CORS per accettare solo il tuo dominio.

6. **Produzione:** Questo setup usa Flask-SocketIO in modalità threading. Per produzione, considera l'uso di:
   - Gunicorn con eventlet o gevent
   - Redis per session storage invece di memoria
   - HTTPS/WSS per connessioni sicure

---

## Troubleshooting

### Errore: "Connection not initialized"
- Assicurati di aver effettuato il login e di aver passato il token corretto

### Errore: "Invalid or expired token"
- Il token è scaduto (24 ore). Effettua nuovamente il login

### Audio non viene trascritto
- Verifica che l'audio sia nel formato corretto (PCM, 16kHz, mono)
- Controlla i log del server per eventuali errori

### WebSocket si disconnette
- Verifica la connessione di rete
- Controlla che il server sia ancora in esecuzione

---

## Variabili d'Ambiente Richieste

Assicurati di avere un file `.env` con:

```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

Senza la chiave API di Deepgram, il servizio di trascrizione non funzionerà.
