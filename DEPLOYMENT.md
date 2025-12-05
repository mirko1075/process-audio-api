# Deployment Guide - Audio Transcription API con Auth0

Guida completa per il deployment su Render.com con autenticazione Auth0.

## Indice

1. [Prerequisiti](#prerequisiti)
2. [Configurazione Auth0](#configurazione-auth0)
3. [Deployment su Render](#deployment-su-render)
4. [Variabili d'Ambiente](#variabili-dambiente)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)
7. [Monitoring](#monitoring)

---

## Prerequisiti

### Account Necessari

- [x] Account GitHub con repository del progetto
- [x] Account [Render.com](https://render.com) (gratuito o paid)
- [x] Account [Auth0](https://auth0.com) (gratuito o paid)
- [x] API Key [Deepgram](https://deepgram.com) per trascrizioni

### File Richiesti

Il repository deve contenere:

```
├── app.py                          # Entry point applicazione
├── requirements.txt                # Dipendenze Python
├── render.yaml                     # Configurazione Render
├── flask_app/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── auth0.py               # Autenticazione Auth0
│   ├── api/
│   │   ├── protected.py           # Route protette
│   │   └── ...
│   └── sockets/
│       └── audio_stream_auth0.py  # WebSocket con Auth0
└── .env.example                   # Template variabili d'ambiente
```

---

## Configurazione Auth0

### Step 1: Creare Auth0 Application

1. Vai su [Auth0 Dashboard](https://manage.auth0.com)
2. Naviga a **Applications** → **Create Application**
3. Configura:
   - **Name:** Audio Transcription API
   - **Type:** Single Page Application (SPA) o Regular Web Application
   - **Technology:** React Native / Web

4. Clicca **Create**

### Step 2: Configurare Application Settings

Nella pagina dell'applicazione:

**Settings → Basic Information:**
- Copia il **Domain** (es: `dev-abc123.us.auth0.com`)
- Copia il **Client ID**

**Settings → Application URIs:**
- **Allowed Callback URLs:**
  ```
  http://localhost:3000/callback,
  https://your-app.render.com/callback
  ```
- **Allowed Logout URLs:**
  ```
  http://localhost:3000,
  https://your-app.render.com
  ```
- **Allowed Web Origins:**
  ```
  http://localhost:3000,
  https://your-app.render.com
  ```

**Settings → Advanced Settings → OAuth:**
- **JsonWebToken Signature Algorithm:** RS256 ✓
- **OIDC Conformant:** Enabled ✓

Salva le modifiche.

### Step 3: Creare Auth0 API

1. Naviga a **Applications** → **APIs** → **Create API**
2. Configura:
   - **Name:** Audio Transcription API
   - **Identifier (Audience):** `https://api.audio-transcription.com` (usa il tuo dominio)
   - **Signing Algorithm:** RS256

3. Clicca **Create**

4. Nelle **Settings** dell'API:
   - Abilita **Allow Offline Access** se necessario
   - Abilita **RBAC** se vuoi usare permessi

5. Copia l'**Identifier** - questo sarà il tuo `AUTH0_AUDIENCE`

### Step 4: Testare la Configurazione

Vai su **Applications** → [Tua App] → **Quick Start** per vedere esempi di integrazione.

---

## Deployment su Render

### Metodo 1: Deployment con render.yaml (Raccomandato)

Il file `render.yaml` è già configurato nel repository.

1. **Login su Render:**
   - Vai su [dashboard.render.com](https://dashboard.render.com)
   - Connetti il tuo account GitHub

2. **Crea Nuovo Web Service:**
   - Clicca **New** → **Blueprint**
   - Seleziona il repository GitHub
   - Render rileverà automaticamente `render.yaml`
   - Clicca **Apply**

3. **Configura Variabili d'Ambiente:**
   - Vai su **Environment** nel dashboard del servizio
   - Aggiungi le seguenti variabili (vedi sezione [Variabili d'Ambiente](#variabili-dambiente))

4. **Deploy:**
   - Render avvierà automaticamente il deploy
   - Attendi il completamento (5-10 minuti)

### Metodo 2: Deployment Manuale

1. **Login su Render:**
   - Dashboard → **New** → **Web Service**

2. **Connetti Repository:**
   - Seleziona il repository GitHub
   - Branch: `main`

3. **Configurazione Servizio:**
   ```
   Name: audio-transcription-api
   Region: Oregon (US West)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:$PORT --log-level info --access-logfile - --error-logfile -
   ```

4. **Plan:**
   - Seleziona piano (Starter $7/mese o Free)
   - Free tier ha limitazioni su CPU/Memory

5. **Environment Variables:**
   - Aggiungi variabili (vedi sezione successiva)

6. **Health Check:**
   - Health Check Path: `/health`

7. **Deploy:**
   - Clicca **Create Web Service**

---

## Variabili d'Ambiente

### Variabili Richieste

Configura queste variabili nella sezione **Environment** di Render:

#### Auth0 Configuration

```bash
AUTH0_DOMAIN=dev-abc123.us.auth0.com
AUTH0_AUDIENCE=https://api.audio-transcription.com
```

**Dove trovarle:**
- `AUTH0_DOMAIN`: Auth0 Dashboard → Applications → [Tua App] → Settings → Domain
- `AUTH0_AUDIENCE`: Auth0 Dashboard → APIs → [Tua API] → Settings → Identifier

#### Deepgram API

```bash
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

**Dove trovarla:**
- [Deepgram Console](https://console.deepgram.com) → API Keys

#### Flask Configuration

```bash
FLASK_ENV=production
FLASK_APP=app.py
LOG_LEVEL=INFO
```

#### CORS Configuration

```bash
CORS_ORIGINS=https://your-frontend-domain.com,https://your-app.render.com
```

**Per development:**
```bash
CORS_ORIGINS=*
```

**Per production:**
```bash
CORS_ORIGINS=https://your-app.com,https://www.your-app.com
```

#### JWT Secret (opzionale per web auth)

```bash
JWT_SECRET_KEY=auto_generated_by_render
```

Render può auto-generare questa chiave.

### Variabili Opzionali

#### Database (se usi PostgreSQL)

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Render può auto-generare questo se crei un PostgreSQL database.

#### Google Cloud (se usi traduzione)

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Template .env.example

Crea file `.env.example` nel repository:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-auth0-domain.auth0.com
AUTH0_AUDIENCE=https://api.your-domain.com

# Deepgram API
DEEPGRAM_API_KEY=your_deepgram_api_key

# Flask Configuration
FLASK_ENV=development
FLASK_APP=app.py
LOG_LEVEL=DEBUG

# CORS
CORS_ORIGINS=*

# JWT Secret
JWT_SECRET_KEY=your-super-secret-key-change-in-production

# Database (optional)
DATABASE_URL=postgresql://localhost:5432/transcription_db

# Server
PORT=5000
```

---

## Testing

### Test Locale con Gunicorn

Prima del deployment, testa localmente con gunicorn:

```bash
# Installa dipendenze
pip install -r requirements.txt

# Crea .env con variabili
cp .env.example .env
# Modifica .env con le tue chiavi

# Avvia con gunicorn (simula produzione)
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:5000 --log-level debug

# Test health check
curl http://localhost:5000/health
```

### Test Endpoints REST

#### 1. Health Check (pubblico)

```bash
curl https://your-app.render.com/health
```

**Response attesa:**
```json
{
  "status": "healthy",
  "service": "Audio Transcription API",
  "version": "1.0.0"
}
```

#### 2. Route Protetta - /api/me

Prima ottieni un token da Auth0:

**Con Auth0 Authentication API:**
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

**Test /api/me:**
```bash
curl https://your-app.render.com/api/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response attesa:**
```json
{
  "user": {
    "sub": "auth0|123456",
    "email": "user@example.com",
    ...
  },
  "user_id": "auth0|123456"
}
```

### Test WebSocket

Usa uno script Node.js o Python:

**Node.js:**
```javascript
const io = require('socket.io-client');

const socket = io('https://your-app.render.com/audio-stream', {
  transports: ['websocket'],
  auth: {
    token: 'YOUR_AUTH0_ACCESS_TOKEN'
  }
});

socket.on('connect', () => {
  console.log('✅ Connected to WebSocket');
});

socket.on('connected', (data) => {
  console.log('Server confirmed:', data);
});

socket.on('error', (error) => {
  console.error('❌ Error:', error);
});
```

---

## Troubleshooting

### Errore: "AUTH0_DOMAIN not configured"

**Causa:** Variabili d'ambiente Auth0 non configurate.

**Soluzione:**
1. Vai su Render Dashboard → Environment
2. Aggiungi `AUTH0_DOMAIN` e `AUTH0_AUDIENCE`
3. Redeploy il servizio

### Errore: "Token has expired"

**Causa:** Token JWT scaduto.

**Soluzione:**
- Ottieni un nuovo token da Auth0
- Configura token expiration nelle impostazioni Auth0

### Errore: "Invalid signature"

**Causa:** Mismatch tra algoritmo o chiavi JWKS.

**Soluzione:**
1. Verifica che Auth0 API usi RS256
2. Verifica che `AUTH0_DOMAIN` sia corretto
3. Controlla i log per errori JWKS: `https://YOUR_DOMAIN/.well-known/jwks.json`

### WebSocket non si connette

**Causa:** Gunicorn non configurato con eventlet worker.

**Soluzione:**
Verifica Start Command su Render:
```bash
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:$PORT
```

**⚠️ IMPORTANTE:** Usa `-w 1` (single worker) per SocketIO.

### CORS Errors

**Causa:** Frontend non autorizzato.

**Soluzione:**
1. Aggiungi dominio frontend a `CORS_ORIGINS`
2. Aggiungi dominio a Auth0 Allowed Origins

### Health Check Failing

**Causa:** `/health` endpoint non risponde.

**Soluzione:**
1. Verifica che l'app si avvii senza errori (controlla logs)
2. Test locale: `curl http://localhost:5000/health`
3. Verifica che il PORT sia corretto

### Build Failures

**Causa:** Dipendenze mancanti o incompatibili.

**Soluzione:**
1. Testa build locale: `pip install -r requirements.txt`
2. Verifica compatibilità Python version (Render usa Python 3.11 default)
3. Aggiungi `runtime.txt` se serve versione specifica:
   ```
   python-3.11.0
   ```

---

## Monitoring

### Logs

**Accesso ai logs:**
1. Render Dashboard → [Tuo Servizio] → Logs
2. Filtra per:
   - Info: Eventi normali
   - Warning: Autenticazioni fallite
   - Error: Errori applicazione

**Log delle autenticazioni:**
```python
logger.info(f"Token verified successfully for user: {user_id}")
logger.warning(f"Authentication failed: {error_message}")
```

### Metriche

**Render fornisce:**
- CPU Usage
- Memory Usage
- Request Count
- Response Times

**Dashboard:** Render → [Servizio] → Metrics

### Health Monitoring

Configura un servizio di monitoring esterno (es. UptimeRobot):
- URL: `https://your-app.render.com/health`
- Interval: 5 minuti
- Alert: Email/SMS se down

### Auth0 Logs

Monitora autenticazioni in Auth0 Dashboard:
- **Monitoring** → **Logs**
- Filtra per:
  - Success Login (s)
  - Failed Login (f)
  - API Limit Exceeded (limit_wc)

---

## Scaling

### Horizontal Scaling

⚠️ **ATTENZIONE:** SocketIO richiede "sticky sessions" per horizontal scaling.

**Per scalare oltre 1 worker:**

1. Usa Redis come message broker:
   ```python
   socketio = SocketIO(app, message_queue='redis://redis-url')
   ```

2. Aggiungi Redis a render.yaml:
   ```yaml
   - type: redis
     name: socketio-redis
     plan: starter
   ```

3. Aggiorna requirements.txt:
   ```
   redis==5.0.1
   ```

### Vertical Scaling

Aumenta risorse su Render:
- Dashboard → [Servizio] → Settings → Instance Type
- Scegli piano con più RAM/CPU

---

## Sicurezza

### Best Practices

1. **Secrets Management:**
   - Mai committare `.env` nel repository
   - Usa Render Environment Variables
   - Rota le chiavi periodicamente

2. **CORS:**
   - In produzione, specifica domini esatti
   - NON usare `CORS_ORIGINS=*` in produzione

3. **HTTPS:**
   - Render fornisce SSL gratuito
   - Forza HTTPS per tutte le richieste

4. **Rate Limiting:**
   - Implementa rate limiting con Flask-Limiter
   - Proteggi endpoint di autenticazione

5. **Token Expiration:**
   - Configura token expiration ragionevole in Auth0 (15-60 minuti)
   - Implementa refresh token per sessioni lunghe

---

## Commands Reference

### Render CLI

```bash
# Install Render CLI
npm install -g render-cli

# Login
render login

# Deploy
render deploy

# View logs
render logs --service audio-transcription-api

# SSH into instance
render ssh audio-transcription-api
```

### Gunicorn Start Command

**Development (locale):**
```bash
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:5000 --reload --log-level debug
```

**Production (Render):**
```bash
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:$PORT --log-level info --access-logfile - --error-logfile -
```

**Parametri:**
- `-k eventlet`: Worker class per SocketIO
- `-w 1`: Single worker (richiesto da SocketIO)
- `--bind 0.0.0.0:$PORT`: Bind su porta dinamica Render
- `--access-logfile -`: Log requests su stdout
- `--error-logfile -`: Log errors su stdout

---

## Support

### Risorse

- [Render Documentation](https://render.com/docs)
- [Auth0 Documentation](https://auth0.com/docs)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io)
- [Deepgram Documentation](https://developers.deepgram.com)

### Common Issues

Per problemi comuni vedi [GitHub Issues](https://github.com/your-repo/issues).

### Contatti

Per supporto: [il tuo email/contatto]

---

**Versione:** 1.0.0
**Ultimo aggiornamento:** 2025-12-05
**Autore:** [Il tuo nome]
