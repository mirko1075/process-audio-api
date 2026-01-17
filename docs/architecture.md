# Architecture Documentation

## Overview

Audio Transcription API is a Flask-based microservice providing multi-provider audio/video transcription, translation, and post-processing capabilities. The system is designed for deployment on Render with PostgreSQL persistence, real-time WebSocket streaming (via Deepgram + SocketIO), and flexible authentication (Auth0 JWT, API keys, legacy session tokens).

**Core Technologies:**
- **Runtime:** Python 3.12
- **Web Framework:** Flask 3.1.0 (application factory pattern)
- **WebSocket:** Flask-SocketIO 5.4.1 with eventlet async mode
- **Database:** PostgreSQL via SQLAlchemy
- **Authentication:** Auth0 (RS256 JWT), Flask-JWT-Extended, API keys (SHA256-hashed), optional session tokens
- **AI Services:** Deepgram (Nova-2 real-time), OpenAI (Whisper, GPT-4o-mini), AssemblyAI, Google Translate, DeepSeek

---

## High-Level Architecture Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                             │
├─────────────────────────────────────────────────────────────────┤
│  app.py (dev)  │  wsgi.py (prod - gunicorn eventlet worker)     │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│            APPLICATION FACTORY (flask_app/__init__.py)           │
│  • create_app() → (Flask app, SocketIO instance)                │
│  • Configuration loading (utils/config.py)                       │
│  • Database initialization (PostgreSQL + SQLAlchemy)             │
│  • Blueprint registration (REST APIs)                            │
│  • WebSocket handler registration (SocketIO events)             │
│  • Error handler setup (global + Auth0)                         │
│  • CORS configuration (Flask-CORS)                              │
└────────┬────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────────────────────────┐
         │                                                         │
         ▼                                                         ▼
┌──────────────────────┐                               ┌─────────────────────┐
│   REST API LAYER     │                               │  WEBSOCKET LAYER    │
│   (Blueprints)       │                               │  (SocketIO)         │
├──────────────────────┤                               ├─────────────────────┤
│ • /health            │                               │ Namespace:          │
│ • /                  │                               │ /audio-stream       │
│ • /transcriptions    │                               │                     │
│   - /deepgram        │                               │ Events:             │
│   - /whisper         │                               │ • connect           │
│   - /assemblyai      │                               │ • audio_chunk       │
│   - /video           │                               │ • stop_streaming    │
│   - /transcribe-     │                               │ • disconnect        │
│     and-translate    │                               │                     │
│ • /translations      │                               │ Handlers:           │
│   - /openai          │                               │ • audio_stream_     │
│   - /google          │                               │   auth0.py          │
│   - /deepseek        │                               │   (Auth0 JWT +      │
│ • /sentiment         │                               │    fallback session)│
│ • /documents/{fmt}   │                               │ • audio_stream.py   │
│ • /reports/{fmt}     │                               │   (session-only,    │
│ • /utilities         │                               │    deprecated)      │
│   - /audio-duration  │                               └─────────────────────┘
│   - /log-usage       │
│   - /text-file       │
│ • /auth              │
│   (web auth, main)   │
│ • /mobile-auth       │
│   (session, INSECURE)│
│ • /api/me, /api/     │
│   userinfo (Auth0)   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   AUTHENTICATION MIDDLEWARE                       │
├──────────────────────────────────────────────────────────────────┤
│ 1. Auth0 JWT (RS256) - Primary for production                    │
│    • Decorator: @require_auth (flask_app/auth/auth0.py)          │
│    • Validates: issuer, audience, signature, expiry              │
│    • JWKS caching via PyJWKClient                                │
│    • Sets: request.user, request.user_id, g.user                 │
│                                                                   │
│ 2. API Keys (SHA256-hashed)                                      │
│    • Header: x-api-key                                           │
│    • User API keys (models/user.py:ApiKey)                       │
│    • Legacy static key fallback (utils/config.py:API_KEY)        │
│    • Decorator: @require_api_key, @require_any_auth              │
│                                                                   │
│ 3. Session Tokens (DEPRECATED - dev/test ONLY)                   │
│    • Flag: ALLOW_INSECURE_SESSION_AUTH=true (MUST be false prod) │
│    • Endpoint: /mobile-auth/login (NO PASSWORD VALIDATION!)      │
│    • Storage: In-memory dict (flask_app/services/session_manager)│
│    • Used by: flask_app/sockets/audio_stream.py                  │
│    • Security Risk: Tokens generated without credential check    │
│    • Persistence: Lost on service restart (not database-backed)  │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                                │
├──────────────────────────────────────────────────────────────────┤
│ flask_app/services/                                               │
│  • transcription.py                                               │
│    - DeepgramService (Nova-2, diarization, paragraphs)           │
│    - WhisperService (auto-chunking for large files)              │
│    - AssemblyAIService                                            │
│  • translation.py                                                 │
│    - OpenAITranslationService (GPT chunking, 118K token limit)   │
│    - GoogleTranslationService                                    │
│    - DeepSeekTranslationService (webhook integration)            │
│  • video_transcription.py                                        │
│    - VideoTranscriptionService (YouTube URLs + file uploads)     │
│    - Uses: yt-dlp for download, openai-whisper for transcription │
│  • postprocessing.py                                              │
│    - SentimentService (placeholder)                              │
│    - DocumentService (Word/PDF/Excel generation - placeholders)  │
│  • session_manager.py                                             │
│    - SessionManager: In-memory session token storage             │
│    - Methods: create_session, validate_session, invalidate       │
│    - Cleanup: Manual via cleanup_expired_sessions()              │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                                 │
├──────────────────────────────────────────────────────────────────┤
│ flask_app/clients/                                                │
│  • deepgram.py - Deepgram SDK wrapper                            │
│  • openai.py - OpenAI SDK (Whisper + GPT translation)            │
│  • assemblyai.py - AssemblyAI SDK wrapper                        │
│  • google.py - Google Cloud Translate client                     │
│  • deepseek.py - DeepSeek API client (DEEPSEEK_API_KEY env var)  │
│  • video_processor.py - yt-dlp + Whisper integration             │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                              │
├──────────────────────────────────────────────────────────────────┤
│ PostgreSQL Database (SQLAlchemy ORM)                              │
│                                                                   │
│ models/user.py:                                                   │
│  • User                                                           │
│    - Credentials (email, password_hash via bcrypt)               │
│    - Profile (first_name, last_name, company)                    │
│    - Plan (free/pro/enterprise)                                  │
│    - Usage tracking (api_calls_month, audio_minutes_month)       │
│  • ApiKey                                                         │
│    - key_hash (SHA256), key_prefix (for display)                 │
│    - Metadata (name, last_used, usage_count, expires_at)         │
│  • UsageLog                                                       │
│    - Per-request billing tracking (service, endpoint, costs)     │
│    - Dimensions: audio_duration_seconds, tokens_used, cost_usd   │
│                                                                   │
│ Database Initialization:                                          │
│  • Auto-create: flask_app/__init__.py calls db.create_all()      │
│  • Manual script: scripts/init_db.py (drop/recreate + admin user)│
└──────────────────────────────────────────────────────────────────┘
```

---

## Module Boundaries and Responsibilities

### 1. **core/ (Compatibility Shim)**
**Purpose:** Transition layer to remap `import core` → `import flask_app`
**Mechanism:** `core/__init__.py` sets `__path__ = [flask_app_directory]`
**Status:** Temporary migration shim. All actual code lives in `flask_app/`.
**DO NOT add new code to core/** - it's an import redirect only.

### 2. **flask_app/ (Main Application Package)**

#### **flask_app/__init__.py**
- **Application factory:** `create_app(config_override=None) -> (Flask, SocketIO)`
- **Responsibilities:**
  - Load configuration via `utils.config.get_app_config()`
  - Initialize database (SQLAlchemy + create_all)
  - Register blueprints with fallback logic (tries multiple auth variants)
  - Register SocketIO handlers (prefers Auth0 → falls back to session-based)
  - Setup CORS (origins: localhost:3000)
  - Register global error handlers (400/401/404/500, custom exceptions)

#### **flask_app/api/ (REST Blueprints)**
| Blueprint | URL Prefix | Auth Required | Purpose |
|-----------|------------|---------------|---------|
| health | / | No | Health checks, service metadata |
| transcription | /transcriptions | Yes (@require_any_auth) | Audio/video → text (Deepgram/Whisper/AssemblyAI) |
| translation | /translations | Yes (@require_api_key) | Text translation (OpenAI/Google/DeepSeek) |
| postprocessing | / | Yes (@require_api_key) | Sentiment, document/report generation |
| utilities | /utilities | Yes (@require_api_key) | Audio duration calc, usage logging, file creation |
| web_auth (api/auth.py) | /auth | Varies | User registration, login, API key management (JWT-based) |
| mobile_auth (flask_app/api/auth.py) | /mobile-auth | No (INSECURE) | **DEPRECATED** session token login (no password check!) |
| protected (flask_app/api/protected.py) | /api | Yes (@require_auth Auth0) | Auth0 user info endpoints (/api/me, /api/userinfo) |

**Error Handling:**
- Blueprint-specific: `@bp.errorhandler(BadRequest)` → JSON response
- Global: Registered in `register_error_handlers()` for TranscriptionError, TranslationError, HTTPException

#### **flask_app/services/ (Business Logic)**
- **Encapsulates external API calls** (AI providers)
- **Handles complexity:** chunking large files (Whisper, OpenAI translation), diarization (Deepgram), webhook forwarding (DeepSeek)
- **Error translation:** Wraps provider exceptions → `TranscriptionError`/`TranslationError`
- **Temporary file management:** Creates/cleans temp files for audio processing
- **Session management:** `session_manager.py` maintains in-memory session tokens (singleton pattern, not persistent)

#### **flask_app/clients/ (External API Wrappers)**
- **Thin SDK wrappers** around provider APIs
- **Configuration injection** from `utils.config.get_app_config()` or environment variables
- **No business logic** - pure I/O adapters

#### **flask_app/auth/ (Auth0 Integration)**
- **auth0.py:** JWT verification (RS256, JWKS caching), `@require_auth` decorator, `verify_websocket_token()`
- **Security features:**
  - PyJWKClient caching (avoids repeated JWKS downloads)
  - Token validation: issuer, audience, signature, expiry
  - `ALLOW_INSECURE_SESSION_AUTH` flag (blocks deprecated endpoints in prod)

#### **flask_app/sockets/ (WebSocket Handlers)**
| Handler | Auth Method | Language Selection | Status |
|---------|-------------|-------------------|--------|
| audio_stream_auth0.py | Auth0 JWT + session fallback | Query param: `?lang=it` (30+ languages) | **Active, preferred** |
| audio_stream.py | Session tokens only | Hardcoded Italian (`language="it"`) | **Deprecated** |

**WebSocket Flow (audio_stream_auth0.py):**
1. **connect:** Authenticate via `auth={'token': '...'}` → validate Auth0 JWT → fallback to session if `ALLOW_INSECURE_SESSION_AUTH=true`
2. **Initialize Deepgram:** Create live connection with Nova-2 model, dynamic language (from `?lang=` query param, default `en`)
3. **audio_chunk:** Base64-decode audio → send to Deepgram live stream
4. **Deepgram callbacks:** `on_message` → emit `transcription` event with transcript, is_final, confidence
5. **stop_streaming / disconnect:** Close Deepgram connection, cleanup active_connections dict

### 3. **models/ (Database Schema)**
- **models/__init__.py:** Exports `db` (SQLAlchemy), `bcrypt`, `init_db(app)`
- **models/user.py:** User, ApiKey, UsageLog models (see Persistence Layer diagram)

### 4. **utils/ (Shared Utilities)**
- **config.py:** `get_app_config()` - loads env vars, frozen dataclasses (DeepgramSettings, OpenAISettings, etc.)
- **auth.py:** `@require_auth`, `@require_api_key`, `@require_jwt`, `@require_any_auth` decorators + usage logging
- **exceptions.py:** Custom exceptions (TranscriptionError, TranslationError, InvalidRequestError, ProcessingError)
- **logging.py:** Centralized logging configuration (standard Python logging module)

### 5. **api/ (Top-Level Web Auth Blueprint)**
- **api/auth.py:** User registration, login, profile, API key CRUD (uses Flask-JWT-Extended)
- **Security:** Password validation (8+ chars, letter+number), email validation
- **Mounted at:** `/auth` (separate from `/mobile-auth`)

### 6. **scripts/ (Database Utilities)**
- **init_db.py:** Database initialization and admin user creation
  - **Modes:**
    - Default: Interactive with safety checks (requires typing "yes")
    - `--safe`: Create tables only (no data loss via `db.create_all()`)
    - `--force`: Bypass safety checks for CI/CD
    - `test-user`: Create test@example.com user with API key
  - **Safety:** Refuses to run in production unless forced
  - **Creates:** admin@example.com (password: admin123, enterprise plan)

---

## Request Flows

### REST Flow: Transcription Request (Deepgram)
```
1. Client → POST /transcriptions/deepgram
   Headers: x-api-key: usr_123_xyz OR Authorization: Bearer <JWT>
   Body: multipart/form-data {audio: file, language: 'en', diarize: 'true'}

2. Flask routing → transcription_bp.deepgram_transcription()

3. Authentication:
   @require_any_auth decorator
   → Try JWT first (via @require_auth logic in utils/auth.py)
   → Fallback to API key (models/user.py:ApiKey.verify_key())
   → If valid: set g.current_user, g.auth_method

4. Service Layer:
   DeepgramService().transcribe(audio_file, language='en', diarize=True)
   → Save to temp file
   → Read file bytes
   → DeepgramClient.transcribe(audio_data, model='nova-2', diarize=True)
   → Parse response (transcript + diarization metadata)
   → Return {transcript, diarization: {speakers_detected: 2, ...}, processing_info}

5. Response:
   200 OK {transcript: "...", diarization: {...}, processing_info: {...}}

6. Usage Logging:
   log_usage(service='deepgram', endpoint='/transcriptions/deepgram', audio_duration=120)
   → UsageLog entry created in PostgreSQL
```

### WebSocket Flow: Real-Time Audio Streaming
```
1. Client connects to wss://<host>/audio-stream?lang=it
   Auth: {token: '<Auth0 JWT or session token>'}

2. SocketIO → handle_connect(auth)
   → authenticate_websocket(auth)
     → Try verify_websocket_token(token) [Auth0 JWT]
     → Fallback: is_valid_session(token) if ALLOW_INSECURE_SESSION_AUTH=true
       (validates against in-memory dict in session_manager)
   → Extract language from request.args.get('lang', 'en')
   → Validate language against SUPPORTED_LANGUAGES (30+ langs)

3. Initialize Deepgram:
   → DeepgramClient(api_key).listen.live.v("1")
   → Register event handlers:
      • on_message → emit('transcription', {transcript, is_final, confidence})
      • on_error → emit('error', {message})
   → Start with LiveOptions(model='nova-2', language='it', interim_results=True)

4. Store connection:
   active_connections[request.sid] = {
     user_id, auth_type, dg_connection, language, is_deepgram_open
   }

5. Client sends audio chunks:
   emit('audio_chunk', {audio_chunk: '<base64_audio>'})
   → handle_audio_chunk(data)
   → base64.b64decode(audio_chunk)
   → dg_connection.send(audio_bytes)

6. Deepgram streams back transcripts:
   on_message callback → emit('transcription', {transcript: "Ciao mondo", is_final: true})

7. Client stops:
   emit('stop_streaming') → dg_connection.finish()
   OR disconnect → cleanup active_connections

```

---

## Configuration Sources

### Environment Variables (Required)
| Variable | Purpose | Default | Validation |
|----------|---------|---------|------------|
| `API_KEY` | Legacy static API key | None | Required (utils/config.py) |
| `DEEPGRAM_API_KEY` | Deepgram SDK auth | None | Required |
| `OPENAI_API_KEY` | OpenAI SDK (Whisper, GPT) | None | Required |
| `ASSEMBLYAI_API_KEY` | AssemblyAI SDK | None | Optional |
| `DEEPSEEK_API_KEY` | DeepSeek API client | None | Required by DeepSeekClient (raises ValueError if missing) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON | None | Optional (for Google Translate) |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/mydb` | Required for prod |
| `JWT_SECRET_KEY` | Flask-JWT-Extended signing | `your-jwt-secret-key-change-in-production` | **MUST change in prod** |
| `SECRET_KEY` | Flask session secret | `your-secret-key-change-in-production` | **MUST change in prod** |
| `AUTH0_DOMAIN` | Auth0 tenant domain | None | Required for Auth0 features |
| `AUTH0_AUDIENCE` | Auth0 API identifier | None | Required for Auth0 JWT validation |
| `AUTH0_REQUEST_TIMEOUT` | Timeout for Auth0 API calls (seconds) | `30` | Optional |
| `ALLOW_INSECURE_SESSION_AUTH` | Enable deprecated session auth | `false` | **MUST be `false` in production** |
| `PORT` | HTTP bind port | `5000` | Auto-set by Render |
| `FLASK_ENV` | Environment (development/production) | development | Controls debug mode |
| `CORS_ORIGINS` / `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `*` | Tighten in prod |
| `LOG_LEVEL` | Logging verbosity | INFO | Optional |

### Configuration Loading Precedence
1. **Environment variables** (via `os.getenv()`)
2. **.env file** (via `python-dotenv` - for local dev)
3. **Hardcoded defaults** (in `utils/config.py` dataclasses)

### Render-Specific (render.yaml)
- `PORT`: Injected by Render platform (binds to 0.0.0.0:$PORT)
- `AUTH0_DOMAIN`, `DEEPGRAM_API_KEY`: Marked `sync: false` (manual secret entry in Render dashboard)
- `JWT_SECRET_KEY`: `generateValue: true` (Render auto-generates on first deploy)

---

## Key Architectural Decisions

### Why Application Factory Pattern?
- **Testability:** Can create isolated app instances with `config_override`
- **Blueprint isolation:** Each API module is independently mountable
- **Deferred initialization:** Database, SocketIO, blueprints registered post-construction

### Why core/ Shim?
- **Migration in progress:** Transitioning from `flask_app` to `core` namespace
- **Backward compatibility:** Existing imports `from core import X` work without mass refactor
- **Temporary solution:** DO NOT add new code to `core/`

### Why Multiple Auth Methods?
- **Auth0 (primary):** Enterprise-grade for production web/mobile apps
- **API Keys:** External integrations (Make.com, webhooks, scripts)
- **Session Tokens (deprecated):** Legacy mobile app support - **REMOVE IN FUTURE**

### Why In-Memory Session Storage?
- **Simplicity:** No Redis/database dependency for deprecated feature
- **Limitation:** Not persistent (lost on restart), not multi-worker safe
- **Migration path:** When removing session auth, delete entire `session_manager.py`

### Why Eventlet for SocketIO?
- **Real-time requirement:** Deepgram live streaming needs persistent WebSocket connections
- **Gunicorn compatibility:** `-k eventlet` worker class required (not default sync workers)
- **Single worker:** `-w 1` to avoid connection state issues across workers

### Why Dual WebSocket Handlers?
- **Graceful migration:** `audio_stream_auth0.py` adds Auth0 support while maintaining fallback
- **Feature parity:** Both support Deepgram live streaming
- **Deprecation path:** `audio_stream.py` will be removed when mobile app migrates to Auth0

### Why Dual Database Init Strategies?
- **Startup auto-create:** `db.create_all()` ensures tables exist (safe, additive-only)
- **Manual script:** `scripts/init_db.py` for destructive operations (drop/recreate, admin user)
- **No migrations:** Schema changes require manual SQL or script updates (Alembic not implemented)

---

## Observability Hooks

### Logging
- **Framework:** Python `logging` module
- **Levels:** INFO (default), DEBUG (verbose), WARNING (auth failures), ERROR (exceptions)
- **Key log points:**
  - Authentication decisions (JWT success/fail, API key verification)
  - WebSocket lifecycle (connect, disconnect, Deepgram errors)
  - Service calls (transcription start/complete, external API failures)
  - Usage tracking (logged to database + stdout)
  - Session management (create/validate/invalidate - when ALLOW_INSECURE_SESSION_AUTH=true)

### Health Check
- **Endpoint:** `GET /health`
- **Response:** `{"status": "healthy", "service": "Audio Transcription API", "version": "1.0.0"}`
- **Used by:** Render health monitoring (render.yaml: `healthCheckPath: /health`)

### Usage Tracking
- **Database:** `UsageLog` table records per-request metrics
- **Fields:** service, endpoint, audio_duration_seconds, tokens_used, cost_usd, timestamp
- **Trigger:** `utils.auth.log_usage()` called by decorators when `g.current_user` exists

---

## Deployment Architecture (Render)

```
┌────────────────────────────────────────────────────────────┐
│                    Render Platform                          │
├────────────────────────────────────────────────────────────┤
│  Web Service: audio-transcription-api                       │
│  Region: Oregon                                             │
│  Plan: Starter                                              │
│  Runtime: python                                            │
│                                                             │
│  Build:                                                     │
│    pip install -r requirements.txt                          │
│                                                             │
│  Start:                                                     │
│    gunicorn -k eventlet -w 1 wsgi:application \             │
│      --bind 0.0.0.0:$PORT \                                 │
│      --log-level info \                                     │
│      --access-logfile - \                                   │
│      --error-logfile -                                      │
│                                                             │
│  Health Check: /health (every 30s)                          │
│                                                             │
│  Auto-Deploy: main branch (on git push)                     │
└────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│              External Dependencies                          │
├────────────────────────────────────────────────────────────┤
│  • PostgreSQL Database (Render managed or external)         │
│  • Auth0 (auth0.com) - JWT issuer                          │
│  • Deepgram API (deepgram.com) - Transcription             │
│  • OpenAI API (openai.com) - Whisper, GPT                  │
│  • DeepSeek API (deepseek.com) - Translation               │
│  • AssemblyAI API (assemblyai.com) - Optional              │
│  • Google Cloud Translate API - Optional                   │
│  • External webhooks (Make.com) - For DeepSeek integration │
└────────────────────────────────────────────────────────────┘
```

---

## Security Notes

1. **JWT Secret Rotation:** `JWT_SECRET_KEY` is static post-deployment. Rotate manually if leaked (requires env var update + restart).
2. **CORS Origins:** Currently allows `localhost:3000` + production frontend. Tighten in prod via `CORS_ORIGINS` env var.
3. **Database Credentials:** `DATABASE_URL` must use SSL in production (PostgreSQL `?sslmode=require`).
4. **Session Token Risk:** `ALLOW_INSECURE_SESSION_AUTH=true` bypasses authentication. NEVER enable in prod.
5. **API Key Storage:** User API keys are SHA256-hashed. Plaintext key shown ONCE on generation.
6. **Auth0 JWKS Caching:** PyJWKClient caches public keys locally (avoids JWKS endpoint hammering).
7. **Session Persistence:** Session tokens stored in-memory only (lost on restart, not multi-worker safe).

---

## Future Considerations

1. **Remove core/ shim:** Complete migration to direct `flask_app` imports.
2. **Deprecate session auth:** Remove `flask_app/api/auth.py` (mobile-auth), `session_manager.py`, and `audio_stream.py` after mobile app migrates to Auth0.
3. **Rate limiting:** Add per-user API throttling (via Flask-Limiter or Redis).
4. **Metrics:** Export Prometheus metrics (request counts, latency, Deepgram usage).
5. **Database migrations:** Implement Alembic/Flask-Migrate for schema versioning (currently using `db.create_all()` and manual script).
6. **Postprocessing placeholders:** Implement real sentiment analysis, document generation (currently stubs).
7. **Persistent sessions:** If session auth retained, migrate to Redis or database (current in-memory dict not production-ready).
