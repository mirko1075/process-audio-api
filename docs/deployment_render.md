# Render Deployment Guide

## Overview

This Flask application is designed for deployment on Render.com as a **Web Service** with PostgreSQL persistence, WebSocket support, and integration with external AI services. The application uses **gunicorn with eventlet workers** to support real-time SocketIO connections.

---

## Boot Process on Render

### 1. **Build Phase**
```bash
# Executed by: render.yaml buildCommand
pip install -r requirements.txt
```

**Dependencies Installed (key packages):**
- Flask 3.1.0 + Flask-SocketIO 5.4.1
- gunicorn 23.0.0 + eventlet 0.36.1 (WebSocket support)
- deepgram-sdk 3.10.0 (real-time transcription)
- openai 1.61.1 (Whisper, GPT)
- PostgreSQL driver: psycopg2-binary 2.9.9
- Auth: PyJWT[crypto] 2.10.1, Flask-JWT-Extended 4.6.0
- Video processing: yt-dlp 2024.11.4, openai-whisper 20240930

**Build Notes:**
- Requirements duplicated lines 1-32 and 33-64 (cleanup recommended but non-blocking)
- Heavy dependencies: transformers (4.48.1), pandas (2.2.3) - expect 2-3 min build time
- ffmpeg required for video processing (Render provides in base image)

### 2. **Start Phase**
```bash
# Executed by: render.yaml startCommand
gunicorn -k eventlet -w 1 wsgi:application \
  --bind 0.0.0.0:$PORT \
  --log-level info \
  --access-logfile - \
  --error-logfile -
```

**Startup Sequence:**
1. **gunicorn loads** `wsgi.py`
2. **wsgi.py imports** `from core import create_app` (→ redirects to `flask_app/__init__.py`)
3. **create_app() executes:**
   - Load config from env vars (`utils/config.py:get_app_config()`)
   - Initialize PostgreSQL connection (SQLAlchemy)
   - Create database tables (`db.create_all()` if not exist)
   - Register REST blueprints (health, transcriptions, translations, etc.)
   - Register SocketIO handlers (prefers `audio_stream_auth0.py` → falls back to `audio_stream.py`)
   - Setup CORS for allowed origins
   - Register error handlers (global + Auth0)
4. **SocketIO initialized** with eventlet async_mode
5. **Application exported** as `wsgi:application` for gunicorn
6. **Gunicorn binds** to `0.0.0.0:$PORT` (PORT injected by Render)
7. **Health check endpoint** `/health` becomes available

**Critical Worker Configuration:**
- `-k eventlet`: **REQUIRED** for WebSocket support (default sync workers will fail)
- `-w 1`: Single worker to avoid connection state issues (SocketIO active_connections dict is in-memory)
- **Scaling:** For high load, use Redis-based SocketIO message queue (not currently implemented)

### 3. **Health Monitoring**
```yaml
# render.yaml configuration
healthCheckPath: /health
```

**Health Check Behavior:**
- **Endpoint:** `GET /health`
- **Response:** `{"status": "healthy", "service": "Audio Transcription API", "version": "1.0.0"}`
- **Frequency:** Every 30 seconds (Render default)
- **Failure threshold:** 3 consecutive failures → container restart
- **Startup grace period:** 60 seconds before health checks begin

**What Render Monitors:**
- HTTP 200 response from /health
- Response time < 30s
- If database connection fails during startup, app may start but fail on first API call (health endpoint does NOT test DB connectivity)

---

## Required Environment Variables

### **Secrets (Must Configure in Render Dashboard)**

| Variable | Purpose | How to Set | Validation |
|----------|---------|-----------|------------|
| `AUTH0_DOMAIN` | Auth0 tenant (e.g., `yourapp.us.auth0.com`) | Render Dashboard → Environment | **Required** for Auth0 JWT validation. Missing = 500 on protected routes. |
| `AUTH0_AUDIENCE` | Auth0 API identifier (e.g., `https://api.yourapp.com`) | Render Dashboard → Environment | **Required** for JWT audience claim validation. |
| `DEEPGRAM_API_KEY` | Deepgram API key for transcription | Render Dashboard → Environment (sync: false in render.yaml) | **Required**. Missing = TranscriptionError on /transcriptions/deepgram. |
| `OPENAI_API_KEY` | OpenAI API key (Whisper, GPT) | Render Dashboard → Environment | **Required**. Missing = config load failure at startup. |
| `DEEPSEEK_API_KEY` | DeepSeek API key for translation | Render Dashboard → Environment | **Required** by DeepSeekClient. Missing = ValueError on service init. |
| `DATABASE_URL` | PostgreSQL connection string | Auto-injected if using Render PostgreSQL service | **Required** for production. Format: `postgresql://user:pass@host:5432/dbname?sslmode=require` |
| `JWT_SECRET_KEY` | Flask-JWT-Extended signing key | `generateValue: true` in render.yaml (auto-generated) | **Auto-generated** on first deploy. Rotate manually if compromised. |
| `SECRET_KEY` | Flask session secret | Manual entry | **Must set manually**. Default is insecure placeholder. |

### **Optional Secrets**
| Variable | Purpose | Default if Missing |
|----------|---------|-------------------|
| `ASSEMBLYAI_API_KEY` | AssemblyAI transcription | AssemblyAI endpoints will fail (graceful degradation) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON | Google Translate will fail. Set to `/opt/render/project/src/google/google-credentials.json` if using. |

### **Configuration Variables (Set in render.yaml)**

| Variable | Value in render.yaml | Purpose |
|----------|----------------------|---------|
| `FLASK_ENV` | `production` | Disables debug mode, uses production error handling |
| `FLASK_APP` | `app.py` | Entry point hint (not critical for gunicorn) |
| `AUTH0_REQUEST_TIMEOUT` | `30` | Timeout for Auth0 userinfo API calls (seconds) |
| `ALLOW_INSECURE_SESSION_AUTH` | `false` | **CRITICAL SECURITY:** Blocks deprecated /mobile-auth endpoints. **NEVER set to `true` in production.** |
| `CORS_ORIGINS` | `https://meeting-streamer.vercel.app/` | CORS allowed origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |
| `PORT` | (Auto-injected by Render) | HTTP bind port |

---

## Runtime Dependencies

### **External Services (Required)**

1. **PostgreSQL Database**
   - **How to connect:**
     - Option A: Render managed PostgreSQL (auto-injects `DATABASE_URL`)
     - Option B: External database (set `DATABASE_URL` manually with SSL: `?sslmode=require`)
   - **Schema initialization:**
     - Tables auto-created on first boot via `db.create_all()` in `flask_app/__init__.py:init_database()`
     - **Manual migration script:** `scripts/init_db.py` (executable, includes admin user creation)
   - **Failure mode:** If DB unreachable, app starts but all authenticated endpoints return 500 (SQLAlchemy connection errors)

2. **Auth0 (auth0.com)**
   - **Required for:**
     - Protected routes: `/api/me`, `/api/userinfo`, `/api/protected/test`
     - WebSocket connections (when `audio_stream_auth0.py` is active)
   - **Configuration:** Set `AUTH0_DOMAIN`, `AUTH0_AUDIENCE` in Render dashboard
   - **JWKS endpoint:** `https://{AUTH0_DOMAIN}/.well-known/jwks.json` (must be publicly accessible)
   - **Failure mode:**
     - Missing env vars → 500 on protected routes
     - Auth0 down → JWT validation fails with "Token verification failed" (401)
   - **Caching:** PyJWKClient caches JWKS keys locally (reduces Auth0 API calls)

3. **Deepgram API (deepgram.com)**
   - **Required for:**
     - `/transcriptions/deepgram`
     - WebSocket real-time transcription (`/audio-stream`)
   - **API key:** Set `DEEPGRAM_API_KEY` (no default)
   - **Failure mode:** Missing key → TranscriptionError on endpoint calls

4. **OpenAI API (openai.com)**
   - **Required for:**
     - `/transcriptions/whisper`
     - `/translations/openai`
     - Video transcription (whisper model)
   - **API key:** Set `OPENAI_API_KEY` (no default)
   - **Failure mode:** Missing key → config load failure at startup (app won't boot)

5. **DeepSeek API (deepseek.com)**
   - **Required for:**
     - `/translations/deepseek`
   - **API key:** Set `DEEPSEEK_API_KEY` (no default)
   - **Failure mode:** Missing key → ValueError when DeepSeekClient initializes

### **External Services (Optional)**

| Service | Used By | Failure Impact |
|---------|---------|----------------|
| AssemblyAI | `/transcriptions/assemblyai` | Endpoint returns 500 if key missing |
| Google Cloud Translate | `/translations/google` | Endpoint returns 500 if credentials missing |
| Make.com Webhooks | DeepSeek translation forwarding | Silent failure (logs error, returns success to client) |
| Google Sheets API | `/utilities/log-usage` (billing tracking) | Silent failure (logs warning, continues without logging) |

### **System Dependencies (Provided by Render)**
- **Python 3.12** (specified in runtime or Render default)
- **ffmpeg** (for audio/video processing via pydub, yt-dlp, whisper)
- **System packages:** Already available in Render's Python base image

---

## Logs and Observability

### **Log Destinations**
```yaml
# render.yaml: Logs streamed to stdout/stderr
--access-logfile -   # HTTP access logs → stdout
--error-logfile -    # Errors → stderr
```

**Render Logging:**
- **Access:** Render Dashboard → Logs tab (real-time stream)
- **Retention:** Determined by Render plan tier (consult Render documentation or dashboard)
- **Export:** Download logs via Render UI before expiration
- **Search:** Limited to Render UI (no full-text search)
- **Note:** Log retention period varies by plan (Starter/Standard/Pro) - check current Render pricing page

### **What to Monitor**

| Log Pattern | Meaning | Action |
|-------------|---------|--------|
| `Token verified successfully for user: auth0\|123` | Auth0 JWT auth success | Normal |
| `JWT verification failed: Token has expired` | Expired token | Client needs to refresh token |
| `⚠️ SECURITY WARNING: ALLOW_INSECURE_SESSION_AUTH is enabled` | Insecure auth enabled | **FIX IMMEDIATELY** (set to `false`) |
| `WebSocket connected: user_id=X, auth_type=auth0` | SocketIO connection established | Normal |
| `Deepgram error: ...` | Transcription service failure | Check Deepgram API status, key validity |
| `Database initialization failed: ...` | DB connection error at startup | Check `DATABASE_URL`, PostgreSQL status |
| `Connection rejected: Invalid or expired authentication token` | WebSocket auth failure | Client needs valid Auth0 token |
| `Health check requested` | Render health ping | Normal (every 30s) |
| `Session created for user: X` | Session token created (when ALLOW_INSECURE_SESSION_AUTH=true) | Should NOT occur in production |

### **Error Logging**
- **Application errors:** Logged via Python `logging` module (level: INFO default)
- **Gunicorn errors:** Startup failures, worker crashes logged to stderr
- **Database errors:** SQLAlchemy exceptions logged with full traceback

### **Usage Tracking**
- **Database:** `UsageLog` table records per-request metrics (user_id, service, endpoint, duration, cost)
- **Query:** `SELECT * FROM usage_logs WHERE user_id = X ORDER BY created_at DESC;`
- **Billing:** Aggregate by month: `SELECT SUM(cost_usd) FROM usage_logs WHERE user_id = X AND created_at > '2025-01-01';`

---

## Deployment Workflow

### **Automated Deploy (Git Push)**
```bash
git push origin main
```

**Render Workflow:**
1. Detects push to `main` branch (autoDeploy: true)
2. Clones repository
3. Runs `buildCommand`: `pip install -r requirements.txt`
4. Runs `startCommand`: `gunicorn -k eventlet ...`
5. Health check at `/health` (60s grace period)
6. If healthy → routes traffic to new container
7. Old container drained and shut down

**Rollback Strategy** (see next section)

### **Manual Deploy**
- Render Dashboard → Services → audio-transcription-api → Manual Deploy → Deploy latest commit

---

## Rollback Strategy

### **Automatic Rollback (Health Check Failure)**
- **Trigger:** 3 consecutive failed health checks within 90 seconds
- **Action:** Render keeps old container running, stops new deployment
- **Result:** Service continues on previous version

### **Manual Rollback**
1. **Via Render Dashboard:**
   - Go to: Services → audio-transcription-api → Deploys tab
   - Find previous successful deploy
   - Click "Redeploy" on that commit

2. **Via Git Revert:**
   ```bash
   git revert HEAD  # Revert last commit
   git push origin main
   ```
   - Creates a new commit that undoes changes
   - Triggers auto-deploy to previous state

3. **Emergency Rollback (Database Schema Change):**
   - **Problem:** New deploy included database migration that broke old code
   - **Solution:**
     1. Suspend service in Render (stops accepting traffic)
     2. Manually revert database migration (connect via `psql $DATABASE_URL`)
     3. Redeploy previous commit
     4. Resume service

### **Rollback Testing Checklist**
- [ ] Health check still passes (`curl https://yourapp.onrender.com/health`)
- [ ] Authentication works (test `/api/me` with valid Auth0 token)
- [ ] Transcription works (test `/transcriptions/deepgram` with sample audio)
- [ ] WebSocket connects (test SocketIO handshake)
- [ ] Database queries succeed (check logs for SQLAlchemy errors)

---

## Configuration Checklist (Pre-Deploy)

### **Environment Variables (Render Dashboard)**
- [ ] `AUTH0_DOMAIN` = `<your-tenant>.us.auth0.com`
- [ ] `AUTH0_AUDIENCE` = `https://api.<yourapp>.com`
- [ ] `DEEPGRAM_API_KEY` = `<deepgram_key>`
- [ ] `OPENAI_API_KEY` = `<openai_key>`
- [ ] `DEEPSEEK_API_KEY` = `<deepseek_key>`
- [ ] `DATABASE_URL` = Auto-injected OR manual with `?sslmode=require`
- [ ] `JWT_SECRET_KEY` = Auto-generated on first deploy
- [ ] `SECRET_KEY` = Strong random value (not default placeholder)
- [ ] `ALLOW_INSECURE_SESSION_AUTH` = `false` (verify in render.yaml)

### **Optional Variables**
- [ ] `ASSEMBLYAI_API_KEY` (if using AssemblyAI)
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` (if using Google Translate)

### **Service Configuration (render.yaml)**
- [ ] `runtime: python` (correct)
- [ ] `plan: starter` (or higher for production load)
- [ ] `region: oregon` (or closest to users)
- [ ] `healthCheckPath: /health` (set)
- [ ] `autoDeploy: true` (for CI/CD)

### **Database Setup**
- [ ] PostgreSQL service created in Render (or external DB configured)
- [ ] `DATABASE_URL` injected (check Environment tab)
- [ ] SSL mode enabled (`?sslmode=require` if external)

### **External Services**
- [ ] Auth0 application created, API identifier matches `AUTH0_AUDIENCE`
- [ ] Auth0 allowed callback URLs include frontend URL
- [ ] Deepgram API key active, quota available
- [ ] OpenAI API key active, billing enabled
- [ ] DeepSeek API key active, quota available

---

## Common Deployment Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Build fails: "No module named 'X'" | Missing dependency in requirements.txt | Add package, redeploy |
| Health check fails immediately | `PORT` env var not used | Ensure `--bind 0.0.0.0:$PORT` in startCommand |
| 502 Bad Gateway after deploy | App crashed during startup | Check Render logs for Python traceback |
| WebSocket fails to connect | Wrong worker class (sync instead of eventlet) | Verify `-k eventlet` in startCommand |
| Database errors on first deploy | Tables not created | Check logs for `db.create_all()` errors |
| Auth0 endpoints return 500 | Missing `AUTH0_DOMAIN` or `AUTH0_AUDIENCE` | Set env vars in dashboard |
| Transcription endpoints fail | Missing `DEEPGRAM_API_KEY` or `OPENAI_API_KEY` | Set API keys |
| DeepSeek translation fails | Missing `DEEPSEEK_API_KEY` | Set API key in dashboard |
| CORS errors from frontend | Incorrect `CORS_ORIGINS` | Update to match frontend URL |
| "ALLOW_INSECURE_SESSION_AUTH" warning in logs | Security flag not set to `false` | Verify render.yaml, redeploy |

---

## Performance Tuning

### **Current Bottlenecks**
1. **Single worker:** `-w 1` limits concurrency (one request at a time blocks)
2. **In-memory connection state:** SocketIO `active_connections` dict not shared across workers
3. **In-memory session storage:** SessionManager dict not shared across workers or persistent
4. **Synchronous external API calls:** Deepgram, OpenAI calls block gunicorn worker

### **Scaling Recommendations**
1. **Horizontal Scaling (Multiple Instances):**
   - Requires Redis for SocketIO message queue (`redis://...`)
   - Requires Redis/database for session storage (replace in-memory dict)
   - Update `flask_app/__init__.py`: `socketio = SocketIO(app, message_queue='redis://...')`
   - Increase worker count: `-w 4` (after Redis setup)

2. **Vertical Scaling (Larger Instance):**
   - Render plan: Starter → Standard (more CPU/RAM)
   - Helps with ML model loading (whisper, transformers)

3. **Caching:**
   - Enable Redis for PyJWKClient caching (Auth0 JWKS keys)
   - Cache frequent transcriptions (duplicate audio detection)

4. **Async I/O:**
   - Migrate blocking calls to async (aiohttp, asyncio)
   - Requires Flask async views (Flask 2.0+) or Sanic/FastAPI migration

---

## Security Hardening for Production

1. **Secrets Rotation:**
   - Rotate `JWT_SECRET_KEY` every 90 days (invalidates all JWT tokens)
   - Rotate `SECRET_KEY` (invalidates Flask sessions)
   - Rotate API keys (Deepgram, OpenAI, DeepSeek) annually

2. **Database Security:**
   - Use `DATABASE_URL` with SSL: `?sslmode=require`
   - Limit database user permissions (no DROP, CREATE beyond initial setup)
   - Enable connection pooling (SQLAlchemy default: 5 connections)

3. **CORS Tightening:**
   - Change `CORS_ORIGINS` from `*` to specific frontend URLs
   - Remove `localhost:3000` in production

4. **Rate Limiting:**
   - Implement Flask-Limiter (not currently used)
   - Example: 100 requests/minute per user

5. **Monitoring:**
   - Enable Render metrics (CPU, memory, request rate)
   - Set up alerts for health check failures
   - Monitor Auth0 dashboard for anomalous login patterns

---

## Maintenance Procedures

### **Updating Dependencies**
```bash
# Local testing
pip install <package>==<new_version>
pip freeze > requirements.txt
git add requirements.txt
git commit -m "chore: update dependencies"
git push origin main
```

**Testing Checklist:**
- [ ] Run tests locally: `pytest`
- [ ] Verify health check: `/health`
- [ ] Test auth: `/api/me` with Auth0 token
- [ ] Test transcription: `/transcriptions/deepgram`
- [ ] Monitor Render logs post-deploy (first 5 minutes)

### **Database Migrations**
- **Current:** `db.create_all()` (only adds new tables, doesn't alter existing)
- **Manual script:** `scripts/init_db.py` (drop/recreate with safety checks)
- **Recommended:** Implement Flask-Migrate (Alembic)
- **Manual Migration:**
  ```bash
  # Connect to production DB
  psql $DATABASE_URL

  # Run schema changes
  ALTER TABLE users ADD COLUMN new_field VARCHAR(100);

  # Verify in app logs
  ```

### **Database Initialization**
```bash
# Local development - interactive mode (requires typing "yes")
python scripts/init_db.py

# Safe mode - create tables only (no data loss)
python scripts/init_db.py --safe

# Force mode - bypass safety checks (CI/CD)
python scripts/init_db.py --force

# Create test user only
python scripts/init_db.py test-user
```

**Admin User Created:**
- Email: `admin@example.com`
- Password: `admin123`
- Plan: enterprise
- API key generated and displayed once

### **Log Rotation**
- Render automatically rotates logs (no action needed)
- Download historical logs: Render Dashboard → Logs → Download
- Retention period varies by plan tier (check Render documentation)

---

## Emergency Contacts & Resources

| Resource | URL/Contact | Purpose |
|----------|------------|---------|
| Render Dashboard | https://dashboard.render.com | Service management, logs, environment vars |
| Render Status | https://status.render.com | Platform outages |
| Auth0 Dashboard | https://manage.auth0.com | User management, application settings |
| Deepgram Status | https://status.deepgram.com | API outages |
| OpenAI Status | https://status.openai.com | API outages |
| DeepSeek Status | (To be confirmed) | API outages |
| PostgreSQL Connection | `psql $DATABASE_URL` | Direct database access |
| Application Logs | Render Dashboard → Logs | Real-time error monitoring |

---

## Post-Deploy Verification

Run these checks after every deploy:

```bash
# 1. Health check
curl https://yourapp.onrender.com/health
# Expected: {"status": "healthy", ...}

# 2. Root endpoint (API documentation)
curl https://yourapp.onrender.com/
# Expected: {"service": "Audio Transcription API", "endpoints": {...}}

# 3. Auth0 protected route (requires valid token)
curl -H "Authorization: Bearer <AUTH0_JWT>" \
  https://yourapp.onrender.com/api/me
# Expected: {"user": {...}, "user_id": "auth0|123"}

# 4. Transcription endpoint (requires API key)
curl -X POST -H "x-api-key: usr_123_xyz" \
  -F "audio=@test_audio.wav" \
  https://yourapp.onrender.com/transcriptions/deepgram
# Expected: {"transcript": "...", "processing_info": {...}}

# 5. WebSocket connection (requires SocketIO client)
# Test via frontend or wscat:
wscat -c "wss://yourapp.onrender.com/audio-stream?lang=en" \
  --header "Authorization: Bearer <AUTH0_JWT>"
# Expected: Connection established, receives {"message": "Successfully connected"}
```

---

## Troubleshooting Guide

### **App Won't Start**
```
Check Render logs for:
- "Missing required environment variables: X, Y"
  → Set missing env vars in dashboard
- "ImportError: No module named 'X'"
  → Add to requirements.txt, redeploy
- "sqlalchemy.exc.OperationalError: could not connect to server"
  → Check DATABASE_URL, PostgreSQL service status
- "ValueError: DEEPSEEK_API_KEY environment variable is required"
  → Set DEEPSEEK_API_KEY in dashboard
```

### **WebSocket Connections Fail**
```
Check:
- Client using wss:// (not ws://)
- Auth token provided in handshake: {token: '...'}
- Render logs for "Connection rejected: ..." messages
- ALLOW_INSECURE_SESSION_AUTH=false (if using Auth0 only)
```

### **High Memory Usage**
```
Causes:
- ML models loaded (whisper, transformers) - each ~500MB
- Active WebSocket connections (~10MB each)
- Large file uploads buffered in memory
- In-memory session storage (grows unbounded if no cleanup)

Solutions:
- Upgrade Render plan (more RAM)
- Limit max file size (currently 100MB for video)
- Restart service to clear memory leaks
- Implement session cleanup cron job (call cleanup_expired_sessions())
```

### **Slow Response Times**
```
Check:
- Render metrics (CPU usage, request queue)
- External API latency (Deepgram, OpenAI - check status pages)
- Database query performance (enable SQLAlchemy query logging)
- Single worker bottleneck (scale to Redis + multiple workers)
```
