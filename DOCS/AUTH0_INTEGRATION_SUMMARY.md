# Auth0 Integration Summary

## Completamento Integrazione Auth0 ✅

L'integrazione Auth0 è stata completata con successo. Il backend è ora pronto per il deployment su Render con autenticazione JWT RS256.

---

## File Creati/Modificati

### Nuovi File

#### 1. **flask_app/auth/auth0.py** ⭐
Modulo principale per autenticazione Auth0 con:
- `verify_jwt(token)` - Valida token JWT con algoritmo RS256
- `require_auth` - Decoratore per route Flask protette
- `verify_websocket_token(token)` - Validazione per WebSocket
- `get_user_info(access_token)` - Recupera profilo utente da Auth0
- Gestione errori con `Auth0Error` exception

#### 2. **flask_app/auth/__init__.py**
Export dei componenti Auth0 per import semplificato.

#### 3. **flask_app/sockets/audio_stream_auth0.py** ⭐
Handler WebSocket con supporto doppia autenticazione:
- Auth0 JWT (primary)
- Session tokens (fallback per compatibilità mobile)
- Eventi: connect, audio_chunk, stop_streaming, disconnect
- Integrazione Deepgram per trascrizione real-time

#### 4. **flask_app/api/protected.py** ⭐
Route protette di esempio:
- `GET /api/me` - Ritorna dati utente dal token JWT
- `GET /api/userinfo` - Recupera profilo esteso da Auth0
- `GET /api/protected/test` - Endpoint di test autenticazione

#### 5. **render.yaml** ⭐
Configurazione deployment Render:
- Build command
- Start command con gunicorn + eventlet
- Variabili d'ambiente
- Health check
- Auto-deploy settings

#### 6. **DEPLOYMENT.md** 📚
Guida completa deployment su Render (150+ righe):
- Setup Auth0 passo-passo
- Configurazione Render
- Variabili d'ambiente richieste
- Testing endpoints
- Troubleshooting
- Monitoring e scaling

#### 7. **.env.example**
Template variabili d'ambiente con:
- Auth0 config (AUTH0_DOMAIN, AUTH0_AUDIENCE)
- Deepgram API
- Flask settings
- CORS configuration
- Database URLs
- Feature flags

### File Modificati

#### 8. **flask_app/__init__.py**
Aggiornato per:
- Registrare blueprint protected routes
- Registrare handler WebSocket Auth0 (con fallback session-based)
- Registrare Auth0 error handlers

#### 9. **requirements.txt**
Aggiunte dipendenze:
```
PyJWT[crypto]==2.10.1
cryptography==44.0.0
eventlet==0.36.1  # (già presente)
gunicorn==23.0.0  # (già presente)
```

---

## Architettura Autenticazione

### Sistema Duale

Il backend supporta **DUE sistemi di autenticazione** in parallelo:

1. **Auth0 JWT (RS256)** - per applicazioni web/mobile production
   - Endpoint: `/api/*` (route protette)
   - WebSocket: namespace `/audio-stream` con token Auth0

2. **Session Tokens** - per compatibilità con mobile app esistente
   - Endpoint: `/mobile-auth/*` (login, verify, logout)
   - WebSocket: fallback se Auth0 token non valido

### Flusso Auth0

```
Client → Login Auth0 → JWT Token (RS256)
        ↓
    Headers: Authorization: Bearer <token>
        ↓
    @require_auth decorator
        ↓
    verify_jwt() → Valida con JWKS
        ↓
    request.user = payload
```

---

## Endpoint Disponibili

### Pubblici (No Auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | Root welcome message |

### Autenticazione Mobile (Session-Based)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mobile-auth/login` | POST | Login mobile → session token |
| `/mobile-auth/verify` | POST | Verifica validità token |
| `/mobile-auth/logout` | POST | Invalida session token |

### Protetti Auth0 (JWT Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/me` | GET | Dati utente corrente |
| `/api/userinfo` | GET | Profilo esteso Auth0 |
| `/api/protected/test` | GET | Test autenticazione |

### WebSocket (Auth0 + Session)

| Namespace | Events | Auth |
|-----------|--------|------|
| `/audio-stream` | connect, audio_chunk, transcription, stop_streaming | Bearer token o session |

---

## Variabili d'Ambiente Richieste

### Critiche per Produzione

```bash
# Auth0 (OBBLIGATORIE)
AUTH0_DOMAIN=dev-abc123.us.auth0.com
AUTH0_AUDIENCE=https://api.your-domain.com

# Deepgram (OBBLIGATORIA)
DEEPGRAM_API_KEY=your_deepgram_api_key

# Flask
FLASK_ENV=production
PORT=5000

# CORS (specifica domini in production!)
CORS_ORIGINS=https://your-app.com
```

### Opzionali

```bash
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=auto-generated
OPENAI_API_KEY=sk-...
```

---

## Deployment su Render

### Comando Start (Render)

```bash
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:$PORT --log-level info --access-logfile - --error-logfile -
```

**⚠️ IMPORTANTE:**
- `-k eventlet` - Worker class per SocketIO
- `-w 1` - Single worker (obbligatorio per SocketIO)
- `--bind 0.0.0.0:$PORT` - Render fornisce PORT dinamico

### Passi Deployment

1. **Push codice** su GitHub
2. **Render Dashboard** → New Blueprint
3. **Seleziona repository** → Render rileva `render.yaml`
4. **Configura variabili** nel dashboard Render:
   - AUTH0_DOMAIN
   - AUTH0_AUDIENCE
   - DEEPGRAM_API_KEY
5. **Deploy** → automatico
6. **Verifica health**: `https://your-app.render.com/health`

---

## Testing Locale

### 1. Setup Ambiente

```bash
# Copia template
cp .env.example .env

# Modifica .env con le tue chiavi
nano .env

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Avvia con Gunicorn (simulazione produzione)

```bash
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:5000 --log-level debug
```

### 3. Test Endpoints

```bash
# Health check
curl http://localhost:5000/health

# Protected endpoint (senza auth → 401)
curl http://localhost:5000/api/me

# Protected endpoint (con auth → 200)
curl http://localhost:5000/api/me \
  -H "Authorization: Bearer YOUR_AUTH0_TOKEN"
```

### 4. Ottenere Token Auth0

**Da Auth0 Dashboard:**
1. Applications → [Your App] → Quick Start
2. Oppure usa Authentication API:

```bash
curl --request POST \
  --url https://YOUR_AUTH0_DOMAIN/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id":"YOUR_CLIENT_ID",
    "client_secret":"YOUR_CLIENT_SECRET",
    "audience":"YOUR_API_AUDIENCE",
    "grant_type":"client_credentials"
  }'
```

---

## Verifica Integrazione

### ✅ Checklist Completamento

- [x] Modulo `auth0.py` con verify_jwt + decoratore
- [x] Route `/api/me` funzionante
- [x] WebSocket con autenticazione Auth0
- [x] Fallback session-based per compatibilità
- [x] Error handlers Auth0
- [x] `render.yaml` configurato
- [x] `DEPLOYMENT.md` completo
- [x] `.env.example` creato
- [x] `requirements.txt` aggiornato
- [x] Test con gunicorn + eventlet ✅

### Test Eseguiti

```bash
✅ Gunicorn startup con eventlet worker
✅ Health endpoint: GET /health → 200 OK
✅ Protected endpoint senza auth: GET /api/me → 401 Unauthorized
✅ Blueprint registrations:
   - Mobile auth: /mobile-auth/*
   - Auth0 protected: /api/*
   - WebSocket handlers (Auth0-enabled)
   - Auth0 error handlers
```

---

## Codice di Esempio

### Backend: Route Protetta

```python
from flask import Blueprint, request
from flask_app.auth.auth0 import require_auth

bp = Blueprint('protected', __name__)

@bp.route('/api/me')
@require_auth
def get_current_user():
    # request.user contiene il JWT payload
    return {'user': request.user}, 200
```

### Frontend: Chiamata Autenticata

**React/React Native:**
```javascript
const response = await fetch('https://your-app.render.com/api/me', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
const data = await response.json();
console.log(data.user);
```

### WebSocket: Connessione Auth0

```javascript
import io from 'socket.io-client';

const socket = io('https://your-app.render.com/audio-stream', {
  transports: ['websocket'],
  auth: {
    token: accessToken  // Auth0 JWT token
  }
});

socket.on('connected', (data) => {
  console.log('Connected:', data.user_id, data.auth_type);
});
```

---

## Prossimi Passi

1. **Configurare Auth0:**
   - Creare Application
   - Creare API con audience
   - Configurare callbacks/CORS

2. **Deploy su Render:**
   - Collegare repository GitHub
   - Configurare variabili d'ambiente
   - Avviare deployment

3. **Testing Production:**
   - Verificare health check
   - Testare endpoint con token Auth0
   - Testare WebSocket streaming

4. **Frontend Integration:**
   - Usare `PROMPT_FOR_FRONTEND_DEV.md` per mobile app
   - Aggiungere Auth0 SDK al frontend
   - Implementare login flow

---

## Supporto e Documentazione

### File di Riferimento

- **DEPLOYMENT.md** - Guida completa deployment (150+ righe)
- **PROMPT_FOR_FRONTEND_DEV.md** - Integrazione frontend React Native
- **openapi.yaml** - Documentazione API OpenAPI 3.1
- **.env.example** - Template variabili d'ambiente

### Link Utili

- [Auth0 Documentation](https://auth0.com/docs)
- [Render Deployment Guide](https://render.com/docs)
- [Flask-SocketIO Docs](https://flask-socketio.readthedocs.io)
- [Deepgram API](https://developers.deepgram.com)

---

## Note Tecniche

### Sicurezza

- ✅ Token validation con JWKS da Auth0
- ✅ Algoritmo RS256 (asimmetrico)
- ✅ Verifica issuer, audience, expiration
- ✅ HTTPS obbligatorio in produzione
- ⚠️ Cambia `CORS_ORIGINS=*` con domini specifici in production

### Performance

- Single worker eventlet (richiesto da SocketIO)
- Per scaling orizzontale: usa Redis message queue
- Render fornisce SSL/TLS gratuito
- Health check ogni 30 secondi

### Compatibilità

- Python 3.9+
- Flask 3.1.0
- Flask-SocketIO 5.4.1
- Eventlet 0.36.1
- PyJWT 2.10.1

---

**✅ Integrazione Completata**
**📅 Data:** 2025-12-05
**🚀 Pronto per Deployment su Render**
