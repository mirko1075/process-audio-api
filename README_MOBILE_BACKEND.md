# Backend per Meeting Minute Streamer (App React Native)

Backend Flask completo per l'app mobile Meeting Minute Streamer con supporto per streaming audio real-time e trascrizione via Deepgram.

## Riepilogo delle Modifiche

### File Aggiunti

1. **[flask_app/api/auth.py](flask_app/api/auth.py)** - Endpoint di autenticazione
   - `POST /auth/login` - Login con username/password
   - `POST /auth/verify` - Verifica validità token
   - `POST /auth/logout` - Logout e invalidazione token

2. **[flask_app/sockets/audio_stream.py](flask_app/sockets/audio_stream.py)** - WebSocket handler
   - Namespace: `/audio-stream`
   - Eventi: `connect`, `audio_chunk`, `transcription`, `stop_streaming`, `disconnect`
   - Integrazione con Deepgram Live Transcription

3. **[flask_app/sockets/__init__.py](flask_app/sockets/__init__.py)** - Package marker

4. **[MOBILE_API_GUIDE.md](MOBILE_API_GUIDE.md)** - Guida completa API
   - Documentazione dettagliata endpoint
   - Esempi React Native
   - Esempi cURL per testing

5. **[test_endpoints.py](test_endpoints.py)** - Script di test
   - Test automatizzati per tutti gli endpoint REST
   - Verifica funzionamento server

### File Modificati

1. **[requirements.txt](requirements.txt)**
   - Aggiunto: `Flask-SocketIO==5.4.1`

2. **[flask_app/__init__.py](flask_app/__init__.py)**
   - Inizializzato Flask-SocketIO
   - Registrato blueprint auth
   - Registrati handler WebSocket
   - Aggiornato CORS per supporto WebSocket

3. **[app.py](app.py)**
   - Usato `socketio.run()` invece di `app.run()`
   - Supporto completo per WebSocket

## Installazione

### 1. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 2. Configura variabili d'ambiente

Assicurati di avere un file `.env` con:

```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

### 3. Avvia il server

```bash
python app.py
```

Il server sarà disponibile su:
- HTTP: `http://localhost:5000`
- WebSocket: `ws://localhost:5000/socket.io/`

## Endpoint Disponibili

### REST API

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/auth/login` | POST | Autenticazione utente |
| `/auth/verify` | POST | Verifica validità token |
| `/auth/logout` | POST | Logout utente |
| `/health` | GET | Health check server |

### WebSocket

| Namespace | Eventi | Descrizione |
|-----------|--------|-------------|
| `/audio-stream` | `connect`, `audio_chunk`, `transcription` | Streaming audio real-time |

## Test

### Test Endpoint REST

```bash
python test_endpoints.py
```

### Test Login manuale

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "mario", "password": "test123"}'
```

### Test WebSocket

Vedi [MOBILE_API_GUIDE.md](MOBILE_API_GUIDE.md) per esempi completi di integrazione React Native.

## Architettura

```
┌─────────────────┐
│  React Native   │
│   Mobile App    │
└────────┬────────┘
         │
         │ HTTP POST /auth/login
         ├──────────────────────────┐
         │                          │
         │                          ▼
         │                   ┌──────────────┐
         │                   │ Flask Server │
         │                   │   (port 5000)│
         │                   └──────┬───────┘
         │                          │
         │ WebSocket                │
         │ /audio-stream            │
         ├──────────────────────────┤
         │                          │
         │ audio_chunk (base64)     │
         ├─────────────────────────>│
         │                          │
         │                          │ Deepgram Live
         │                          │ Transcription
         │                          ├──────────────┐
         │                          │              │
         │                          │              ▼
         │                          │      ┌──────────────┐
         │ transcription            │      │  Deepgram    │
         │<─────────────────────────┤      │   API        │
         │                          │      └──────────────┘
         │                          │
         │                          │
         ▼                          ▼
   ┌──────────┐            ┌──────────────┐
   │  User    │            │  Session     │
   │Interface │            │  Storage     │
   └──────────┘            └──────────────┘
```

## Flusso di Utilizzo

1. **Login**
   - App invia username/password a `/auth/login`
   - Server restituisce `auth_token`
   - App salva il token

2. **Connessione WebSocket**
   - App si connette a `ws://localhost:5000/audio-stream`
   - Passa `auth_token` nei parametri di connessione
   - Server valida token e stabilisce connessione Deepgram

3. **Streaming Audio**
   - App registra audio in chunks (500ms - 1s)
   - Converte chunks in Base64
   - Invia via evento `audio_chunk`
   - Server inoltra a Deepgram

4. **Ricezione Trascrizioni**
   - Server riceve trascrizioni da Deepgram
   - Invia via evento `transcription`
   - App mostra trascrizioni (intermedie e finali)

5. **Stop Streaming**
   - App invia evento `stop_streaming`
   - Server chiude connessione Deepgram
   - Connessione WebSocket rimane aperta

6. **Logout**
   - App invia richiesta a `/auth/logout` con token
   - Server invalida token
   - App disconnette WebSocket

## Configurazione Lingua

Il server è configurato per l'italiano. Per cambiare lingua, modifica in [flask_app/sockets/audio_stream.py:113](flask_app/sockets/audio_stream.py#L113):

```python
options = LiveOptions(
    model="nova-2",
    language="en",  # Cambia qui: "en", "es", "fr", ecc.
    smart_format=True,
    # ...
)
```

## Formato Audio

L'audio deve essere nel formato:
- **Encoding:** Linear PCM (linear16)
- **Sample Rate:** 16000 Hz
- **Channels:** Mono (1)
- **Bit Depth:** 16 bit

## Note di Sicurezza

⚠️ Questo è un setup di sviluppo. Per produzione:

1. **Storage Sessioni:** Usa Redis invece di memoria
2. **CORS:** Limita origins ai tuoi domini
3. **HTTPS/WSS:** Usa connessioni sicure
4. **Token Security:** Implementa JWT con scadenza e refresh
5. **Rate Limiting:** Aggiungi rate limiting agli endpoint
6. **Validazione Input:** Aggiungi validazione più robusta
7. **Logging:** Non loggare dati sensibili

## Troubleshooting

### Server non si avvia
- Verifica che Flask-SocketIO sia installato
- Controlla che la porta 5000 sia libera
- Verifica che `DEEPGRAM_API_KEY` sia nel file `.env`

### WebSocket non si connette
- Assicurati di usare il namespace corretto: `/audio-stream`
- Verifica che il token sia valido
- Controlla i log del server per errori

### Trascrizioni non arrivano
- Verifica formato audio (PCM, 16kHz, mono)
- Controlla che la chiave Deepgram sia valida
- Verifica i log del server per errori Deepgram

## Documentazione Completa

Vedi [MOBILE_API_GUIDE.md](MOBILE_API_GUIDE.md) per:
- Documentazione completa API
- Esempi React Native dettagliati
- Guide di integrazione
- Best practices

## Contatti e Supporto

Per problemi o domande:
1. Controlla i log del server
2. Verifica la documentazione in MOBILE_API_GUIDE.md
3. Testa con `test_endpoints.py`
4. Verifica la configurazione Deepgram

## License

Questo progetto è parte del sistema Meeting Minute Streamer.
