# Prompt per Frontend Developer (React Native) - Meeting Minute Streamer

## Contesto

Hai già creato la parte client dell'applicazione "Meeting Minute Streamer" utilizzando React Native con TypeScript. Ora il backend è stato completato, testato e deployato. Questo documento contiene tutte le informazioni tecniche necessarie per completare l'integrazione.

## Backend Disponibile

Il backend Flask è operativo e testato con i seguenti endpoint:

### Server Details
- **Base URL Development:** `http://localhost:5000`
- **Base URL Production:** `https://your-domain.render.com` (da configurare)
- **Protocollo WebSocket:** Socket.IO
- **Documentazione API:** Vedi file `openapi.yaml`

---

## REST API Endpoints

### 1. POST /auth/login - Autenticazione

**Descrizione:** Autentica un utente e ottiene un token di sessione per il WebSocket.

**Request:**
```http
POST http://localhost:5000/auth/login
Content-Type: application/json

{
  "username": "mario_rossi",
  "password": "demo123"
}
```

**Response Success (200):**
```json
{
  "auth_token": "session_XyJenG2Tj7UFLWs2g5FZ4jiHAQgz_C0z6ElME-bzOTY",
  "user_id": "mario_rossi",
  "expires_at": "2025-12-05T20:42:34.974864",
  "message": "Login successful"
}
```

**Response Error (400):**
```json
{
  "error": "Username is required"
}
```

**Note:**
- In modalità demo, qualsiasi username/password è accettato
- Il token scade dopo 24 ore
- Salva `auth_token` per le successive chiamate WebSocket

---

### 2. POST /auth/verify - Verifica Token

**Descrizione:** Verifica se un token è ancora valido.

**Request:**
```http
POST http://localhost:5000/auth/verify
Content-Type: application/json

{
  "auth_token": "session_XyJenG2Tj7UFLWs2g5FZ4jiHAQgz..."
}
```

**Response Success (200):**
```json
{
  "valid": true,
  "user_id": "mario_rossi",
  "username": "Mario Rossi"
}
```

**Response Error (401):**
```json
{
  "valid": false,
  "message": "Invalid token"
}
```

---

### 3. POST /auth/logout - Logout

**Descrizione:** Invalida un token di sessione.

**Request:**
```http
POST http://localhost:5000/auth/logout
Content-Type: application/json

{
  "auth_token": "session_XyJenG2Tj7UFLWs2g5FZ4jiHAQgz..."
}
```

**Response Success (200):**
```json
{
  "message": "Logout successful"
}
```

---

## WebSocket Streaming Endpoint

### Connessione: ws://localhost:5000/socket.io/

**Namespace:** `/audio-stream`
**Protocollo:** Socket.IO
**Autenticazione:** Token dal login passato nell'oggetto `auth`

### Setup Socket.IO

**Installazione:**
```bash
npm install socket.io-client
```

**Connessione TypeScript:**
```typescript
import io from 'socket.io-client';

const socket = io('http://localhost:5000/audio-stream', {
  transports: ['websocket'],
  auth: {
    token: authToken  // Token ottenuto dal login
  }
});
```

---

### Eventi Client → Server

#### 1. Evento: `audio_chunk`

Invia chunk audio per la trascrizione in tempo reale.

**Payload:**
```typescript
{
  audio_chunk: string;  // Audio PCM in Base64
  timestamp: string;    // ISO 8601 timestamp
}
```

**Esempio:**
```typescript
socket.emit('audio_chunk', {
  audio_chunk: audioData.toString('base64'),
  timestamp: new Date().toISOString()
});
```

**Specifiche Audio Richieste:**
- **Encoding:** Linear PCM (linear16)
- **Sample Rate:** 16000 Hz
- **Channels:** Mono (1 canale)
- **Bit Depth:** 16 bit
- **Chunk Duration:** 500ms - 1000ms (raccomandato)

#### 2. Evento: `stop_streaming`

Ferma lo streaming audio.

**Payload:** Nessuno o oggetto vuoto

**Esempio:**
```typescript
socket.emit('stop_streaming');
```

---

### Eventi Server → Client

#### 1. Evento: `connected`

Ricevuto quando la connessione è stabilita con successo.

**Payload:**
```typescript
{
  message: string;
  user_id: string;
  timestamp: string;
}
```

**Esempio Gestione:**
```typescript
socket.on('connected', (data) => {
  console.log('✅ Connesso:', data.message);
  setConnectionStatus('connected');
});
```

#### 2. Evento: `transcription`

Ricevuto quando sono disponibili trascrizioni (intermedie o finali).

**Payload:**
```typescript
{
  transcript: string;     // Testo trascritto
  is_final: boolean;      // true = finale, false = intermedia
  timestamp: string;      // ISO 8601
  confidence: number;     // 0.0 - 1.0
}
```

**Esempio Gestione:**
```typescript
socket.on('transcription', (data) => {
  if (data.is_final) {
    // Trascrizione finale - aggiungi al testo completo
    setFinalTranscript(prev => prev + ' ' + data.transcript);
    setInterimTranscript('');  // Pulisci interim
  } else {
    // Trascrizione intermedia - mostra come preview
    setInterimTranscript(data.transcript);
  }

  console.log(`[${data.is_final ? 'FINAL' : 'INTERIM'}] ${data.transcript}`);
});
```

#### 3. Evento: `streaming_stopped`

Conferma che lo streaming è stato fermato.

**Payload:**
```typescript
{
  message: string;
  timestamp: string;
}
```

**Esempio Gestione:**
```typescript
socket.on('streaming_stopped', (data) => {
  console.log('⏹️ Streaming fermato');
  setIsStreaming(false);
});
```

#### 4. Evento: `error`

Ricevuto in caso di errore.

**Payload:**
```typescript
{
  message: string;
  timestamp: string;
}
```

**Errori Comuni:**
- `"Connection not initialized"` - Audio inviato prima della connessione
- `"Invalid audio data format"` - Audio non in Base64 valido
- `"Error processing audio data"` - Errore generico processing
- `"Transcription service error"` - Errore Deepgram

**Esempio Gestione:**
```typescript
socket.on('error', (error) => {
  console.error('❌ Errore:', error.message);
  Alert.alert('Errore', error.message);
});
```

#### 5. Evento: `disconnect`

WebSocket disconnesso.

**Esempio Gestione:**
```typescript
socket.on('disconnect', (reason) => {
  console.log('🔌 Disconnesso:', reason);
  setConnectionStatus('disconnected');

  // Riconnessione automatica se necessario
  if (reason === 'io server disconnect') {
    // Server ha forzato disconnessione - non riconnettere automaticamente
  } else {
    // Disconnessione client o rete - riconnetti
    socket.connect();
  }
});
```

---

## Flusso Completo di Integrazione

### Step 1: Setup Iniziale

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { View, Button, Text, Alert } from 'react-native';
import io from 'socket.io-client';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';

const API_URL = 'http://localhost:5000';  // Cambia per production

const MeetingMinuteScreen = () => {
  const [authToken, setAuthToken] = useState('');
  const [socket, setSocket] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [finalTranscript, setFinalTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  const audioRecorderPlayer = useRef(new AudioRecorderPlayer()).current;
  const streamInterval = useRef(null);
```

### Step 2: Implementa Login

```typescript
  const handleLogin = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'mario',  // Ottieni da form
          password: 'demo123'  // Ottieni da form
        })
      });

      if (!response.ok) {
        throw new Error('Login fallito');
      }

      const data = await response.json();
      setAuthToken(data.auth_token);
      Alert.alert('Successo', 'Login effettuato!');

      // Opzionale: salva token in AsyncStorage per persistenza
      // await AsyncStorage.setItem('auth_token', data.auth_token);

    } catch (error) {
      Alert.alert('Errore Login', error.message);
    }
  };
```

### Step 3: Implementa Connessione WebSocket

```typescript
  const connectWebSocket = () => {
    if (!authToken) {
      Alert.alert('Errore', 'Devi prima effettuare il login');
      return;
    }

    setConnectionStatus('connecting');

    const newSocket = io(`${API_URL}/audio-stream`, {
      transports: ['websocket'],
      auth: { token: authToken }
    });

    // Handler eventi
    newSocket.on('connected', (data) => {
      console.log('✅ Connesso:', data.message);
      setConnectionStatus('connected');
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

    newSocket.on('streaming_stopped', (data) => {
      console.log('⏹️ Streaming fermato');
      setIsStreaming(false);
    });

    newSocket.on('error', (error) => {
      console.error('❌ Errore:', error.message);
      Alert.alert('Errore', error.message);
    });

    newSocket.on('disconnect', (reason) => {
      console.log('🔌 Disconnesso:', reason);
      setConnectionStatus('disconnected');
      setIsStreaming(false);
    });

    setSocket(newSocket);
  };
```

### Step 4: Implementa Recording e Streaming

```typescript
  const startStreaming = async () => {
    if (!socket || connectionStatus !== 'connected') {
      Alert.alert('Errore', 'WebSocket non connesso');
      return;
    }

    try {
      // Configura audio recording
      const audioConfig = {
        AudioEncoderAndroid: AudioEncoderAndroidType.AAC,
        AudioSourceAndroid: AudioSourceAndroidType.MIC,
        AVEncoderAudioQualityKeyIOS: AVEncoderAudioQualityIOSType.high,
        AVNumberOfChannelsKeyIOS: 1,
        AVFormatIDKeyIOS: AVEncodingOption.lpcm,
        AVSampleRateKeyIOS: 16000,
        OutputFormatAndroid: OutputFormatAndroidType.AAC_ADTS,
      };

      await audioRecorderPlayer.startRecorder(undefined, audioConfig);
      setIsStreaming(true);

      // Invia chunk audio ogni 1 secondo
      streamInterval.current = setInterval(async () => {
        // NOTA: Implementazione audio chunk dipende dalla libreria usata
        // Questo è un esempio semplificato

        try {
          const audioChunk = await getAudioChunk();  // Implementa questa funzione
          const audioBase64 = audioChunk.toString('base64');

          socket.emit('audio_chunk', {
            audio_chunk: audioBase64,
            timestamp: new Date().toISOString()
          });
        } catch (error) {
          console.error('Errore invio chunk:', error);
        }
      }, 1000);

    } catch (error) {
      Alert.alert('Errore Recording', error.message);
    }
  };
```

### Step 5: Implementa Stop Streaming

```typescript
  const stopStreaming = async () => {
    try {
      // Ferma recording
      await audioRecorderPlayer.stopRecorder();

      // Ferma interval
      if (streamInterval.current) {
        clearInterval(streamInterval.current);
        streamInterval.current = null;
      }

      // Notifica server
      if (socket) {
        socket.emit('stop_streaming');
      }

      setIsStreaming(false);

    } catch (error) {
      console.error('Errore stop streaming:', error);
    }
  };
```

### Step 6: Implementa Cleanup

```typescript
  const disconnectWebSocket = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
      setConnectionStatus('disconnected');
    }
  };

  const handleLogout = async () => {
    try {
      // Ferma streaming se attivo
      if (isStreaming) {
        await stopStreaming();
      }

      // Disconnetti WebSocket
      disconnectWebSocket();

      // Logout dal server
      if (authToken) {
        await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ auth_token: authToken })
        });
      }

      // Pulisci stato
      setAuthToken('');
      setFinalTranscript('');
      setInterimTranscript('');

      Alert.alert('Successo', 'Logout effettuato');

    } catch (error) {
      console.error('Errore logout:', error);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isStreaming) {
        stopStreaming();
      }
      disconnectWebSocket();
    };
  }, []);
```

### Step 7: UI Rendering

```typescript
  return (
    <View style={{ padding: 20 }}>
      <Text>Status: {connectionStatus}</Text>

      {!authToken && (
        <Button title="Login" onPress={handleLogin} />
      )}

      {authToken && !socket && (
        <Button title="Connetti WebSocket" onPress={connectWebSocket} />
      )}

      {socket && connectionStatus === 'connected' && (
        <Button
          title={isStreaming ? "Ferma Riunione" : "Avvia Riunione"}
          onPress={isStreaming ? stopStreaming : startStreaming}
          color={isStreaming ? 'red' : 'green'}
        />
      )}

      {authToken && (
        <Button title="Logout" onPress={handleLogout} color="gray" />
      )}

      <View style={{ marginTop: 30 }}>
        <Text style={{ fontWeight: 'bold', fontSize: 18 }}>
          Trascrizione Finale:
        </Text>
        <Text>{finalTranscript}</Text>
      </View>

      {interimTranscript && (
        <View style={{ marginTop: 20 }}>
          <Text style={{ fontStyle: 'italic', color: 'gray' }}>
            Trascrizione in corso:
          </Text>
          <Text style={{ color: 'gray' }}>{interimTranscript}</Text>
        </View>
      )}
    </View>
  );
};

export default MeetingMinuteScreen;
```

---

## Configurazione Audio Recording

Per React Native, usa `react-native-audio-recorder-player` o libreria equivalente.

**Installazione:**
```bash
npm install react-native-audio-recorder-player
```

**Configurazione iOS (ios/Podfile):**
```ruby
post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['ENABLE_BITCODE'] = 'NO'
    end
  end
end
```

**Permessi iOS (ios/Info.plist):**
```xml
<key>NSMicrophoneUsageDescription</key>
<string>We need access to your microphone to record meetings</string>
```

**Permessi Android (android/app/src/main/AndroidManifest.xml):**
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
```

---

## Best Practices

### 1. Gestione Errori
```typescript
// Wrapper per fetch con retry
const fetchWithRetry = async (url, options, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response;
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};
```

### 2. Token Persistence
```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';

// Salva token
await AsyncStorage.setItem('auth_token', token);

// Carica token all'avvio
const loadToken = async () => {
  const token = await AsyncStorage.getItem('auth_token');
  if (token) {
    // Verifica validità
    const response = await fetch(`${API_URL}/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auth_token: token })
    });
    const data = await response.json();
    if (data.valid) {
      setAuthToken(token);
    } else {
      await AsyncStorage.removeItem('auth_token');
    }
  }
};
```

### 3. Indicatori Visivi
```typescript
// Connection status indicator
const StatusIndicator = ({ status }) => {
  const colors = {
    disconnected: 'gray',
    connecting: 'yellow',
    connected: 'green'
  };

  return (
    <View style={{
      width: 12,
      height: 12,
      borderRadius: 6,
      backgroundColor: colors[status]
    }} />
  );
};
```

### 4. Performance Optimization
```typescript
// Debounce transcript updates
import { useCallback } from 'react';
import { debounce } from 'lodash';

const debouncedUpdateTranscript = useCallback(
  debounce((text) => {
    setInterimTranscript(text);
  }, 100),
  []
);
```

---

## Testing

### Test con Mock Server
```typescript
// __tests__/websocket.test.ts
import io from 'socket.io-client';

describe('WebSocket Integration', () => {
  let socket;

  beforeEach(() => {
    socket = io('http://localhost:5000/audio-stream', {
      auth: { token: 'test_token' }
    });
  });

  afterEach(() => {
    socket.disconnect();
  });

  it('should connect successfully', (done) => {
    socket.on('connected', (data) => {
      expect(data.message).toBeDefined();
      done();
    });
  });

  it('should receive transcription', (done) => {
    socket.on('transcription', (data) => {
      expect(data.transcript).toBeDefined();
      expect(typeof data.is_final).toBe('boolean');
      done();
    });

    // Simulate audio chunk
    socket.emit('audio_chunk', {
      audio_chunk: 'base64_test_data',
      timestamp: new Date().toISOString()
    });
  });
});
```

---

## Deployment

### Configurazione Production

**Variabili d'Ambiente (.env):**
```env
API_BASE_URL=https://your-domain.render.com
WS_BASE_URL=wss://your-domain.render.com
```

**Config File (src/config.ts):**
```typescript
export const config = {
  apiUrl: __DEV__
    ? 'http://localhost:5000'
    : process.env.API_BASE_URL,
  wsUrl: __DEV__
    ? 'ws://localhost:5000'
    : process.env.WS_BASE_URL
};
```

---

## Troubleshooting

### Problema: WebSocket non si connette
**Soluzione:**
- Verifica che il token sia valido
- Controlla che il server sia raggiungibile
- Verifica firewall/proxy

### Problema: Audio non viene trascritto
**Soluzione:**
- Verifica formato audio (PCM 16kHz mono)
- Controlla che i dati Base64 siano corretti
- Verifica permessi microfono

### Problema: Trascrizioni arrivano in ritardo
**Soluzione:**
- Riduci dimensione chunk (500ms invece di 1000ms)
- Verifica connessione di rete
- Controlla latenza server

---

## Risorse Aggiuntive

- **OpenAPI Spec:** `openapi.yaml`
- **Guida API Completa:** `MOBILE_API_GUIDE.md`
- **Backend README:** `README_MOBILE_BACKEND.md`
- **Test Script:** `test_endpoints.py`

---

## Supporto

Per problemi o domande:
1. Verifica i log del server
2. Testa con `test_endpoints.py`
3. Controlla `MOBILE_API_GUIDE.md` per esempi
4. Consulta OpenAPI specs in `openapi.yaml`

---

## Checklist Completamento

- [ ] Implementato login con gestione token
- [ ] Implementato connessione WebSocket
- [ ] Implementato recording audio con formato corretto (PCM 16kHz)
- [ ] Implementato invio audio chunks via Socket.IO
- [ ] Implementato ricezione trascrizioni (interim e final)
- [ ] Implementato stop streaming
- [ ] Implementato logout e cleanup
- [ ] Aggiunto gestione errori completa
- [ ] Aggiunto indicatori UI per stato connessione
- [ ] Implementato persistenza token (AsyncStorage)
- [ ] Testato flusso completo login → stream → logout
- [ ] Configurato permessi iOS/Android
- [ ] Preparato per deployment production

Buon lavoro! 🚀
