# Architecture Documentation

## Overview

Audio Transcription API is a Flask-based microservice providing multi-provider audio/video transcription, translation, and post-processing capabilities. The system is designed for deployment on Render with PostgreSQL persistence, real-time WebSocket streaming (via Deepgram + SocketIO), and secure authentication (Auth0 JWT, API keys).

**Core Technologies:**
- **Runtime:** Python 3.12
- **Web Framework:** Flask 3.1.0 (application factory pattern)
- **WebSocket:** Flask-SocketIO 5.4.1 with eventlet async mode
- **Database:** PostgreSQL via SQLAlchemy
- **Storage:** Supabase Storage (backend-only access, private bucket, signed URLs for downloads)
- **Authentication:** Auth0 (RS256 JWT with expiration), Flask-JWT-Extended (1h access, 30d refresh), API keys (SHA256-hashed), token revocation via blacklist
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
│   - /deepseek        │                               │   (Auth0 JWT only)  │
│ • /sentiment         │                               │                     │
│ • /documents/{fmt}   │                               └─────────────────────┘
│ • /reports/{fmt}     │
│ • /utilities         │
│   - /audio-duration  │
│   - /log-usage       │
│   - /text-file       │
│ • /auth              │
│   - /login           │
│   - /refresh         │
│   - /logout          │
│ • /api/me, /api/     │
│   userinfo (Auth0)   │
│ • /saas/jobs         │
│   - POST (create)    │
│   - GET (list)       │
│   - GET /{id}        │
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
│    • Expiration: Access tokens (1 hour), Refresh tokens (30 days)│
│    • Token refresh: POST /auth/refresh (exchange refresh→access) │
│    • Token revocation: POST /auth/logout (blacklist via jti)     │
│                                                                   │
│ 2. API Keys (SHA256-hashed)                                      │
│    • Header: x-api-key                                           │
│    • User API keys (models/user.py:ApiKey)                       │
│    • Legacy static key fallback (utils/config.py:API_KEY)        │
│    • Decorator: @require_api_key, @require_any_auth              │
│                                                                   │
│ 3. Token Blacklist (JWT Revocation)                              │
│    • Model: TokenBlacklist (models/token_blacklist.py)           │
│    • Stores: jti (JWT ID), token_type, user_id, expires_at       │
│    • Enforced via: @jwt.token_in_blocklist_loader decorator      │
│    • Prevents reuse of revoked tokens (logout functionality)     │
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
│  • storage.py (Supabase Storage for SaaS file uploads)           │
│    - SupabaseStorageService (upload inputs, store artifacts)     │
│    - Path structure: users/{user_id}/jobs/{job_id}/input|output  │
│    - Signed URL generation (5-min default TTL)                   │
│    - Singleton pattern via get_storage_service()                 │
│  • postprocessing.py                                              │
│    - SentimentService (placeholder)                              │
│    - DocumentService (Word/PDF/Excel generation - placeholders)  │
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
│  • TokenBlacklist                                                 │
│    - JWT revocation tracking (models/token_blacklist.py)         │
│    - Fields: jti (unique JWT ID), token_type, user_id            │
│    - Timestamps: revoked_at, expires_at                          │
│                                                                   │
│ models/job.py:                                                    │
│  • Job (SaaS job persistence)                                    │
│    - Fields: id, user_id, type (transcription|translation),      │
│      status (queued|processing|done|failed), input_ref,          │
│      error_message, created_at, completed_at                     │
│    - Relationship: artifacts (one-to-many, cascade delete)       │
│  • Artifact (job output references)                              │
│    - Fields: id, job_id, kind (transcript|translation|srt|json), │
│      storage_ref (object storage reference)                      │
│    - Foreign key: job_id → jobs.id                               │
│                                                                   │
│ Database Initialization:                                          │
│  • Auto-create: flask_app/__init__.py calls db.create_all()      │
│  • Manual script: scripts/init_db.py (drop/recreate + admin user)│
│  • Migration: scripts/migrate_add_jobs_artifacts.py              │
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
| token_refresh (flask_app/api/token_refresh.py) | /auth | Yes (@jwt_required) | JWT token refresh (/auth/refresh) and revocation (/auth/logout) |
| protected (flask_app/api/protected.py) | /api | Yes (@require_auth Auth0) | Auth0 user info endpoints (/api/me, /api/userinfo) |
| saas_jobs (flask_app/api/saas_jobs.py) | /saas/jobs, /saas/artifacts | Yes (@jwt_required) | SaaS job persistence (create with file upload, list, retrieve jobs and artifacts, signed download URLs) |

**Error Handling:**
- Blueprint-specific: `@bp.errorhandler(BadRequest)` → JSON response
- Global: Registered in `register_error_handlers()` for TranscriptionError, TranslationError, HTTPException

#### **flask_app/services/ (Business Logic)**
- **Encapsulates external API calls** (AI providers)
- **Handles complexity:** chunking large files (Whisper, OpenAI translation), diarization (Deepgram), webhook forwarding (DeepSeek)
- **Error translation:** Wraps provider exceptions → `TranscriptionError`/`TranslationError`
- **Temporary file management:** Creates/cleans temp files for audio processing

#### **flask_app/clients/ (External API Wrappers)**
- **Thin SDK wrappers** around provider APIs
- **Configuration injection** from `utils.config.get_app_config()` or environment variables
- **No business logic** - pure I/O adapters

#### **flask_app/auth/ (Auth0 Integration)**
- **auth0.py:** JWT verification (RS256, JWKS caching), `@require_auth` decorator, `verify_websocket_token()`
- **Security features:**
  - PyJWKClient caching (avoids repeated JWKS downloads)
  - Token validation: issuer, audience, signature, expiry
  - Token expiration enforcement: 1 hour (access), 30 days (refresh)
  - Token revocation via blacklist: `@jwt.token_in_blocklist_loader`

#### **flask_app/sockets/ (WebSocket Handlers)**
| Handler | Auth Method | Language Selection | Status |
|---------|-------------|-------------------|--------|
| audio_stream_auth0.py | Auth0 JWT only | Query param: `?lang=it` (30+ languages) | **Active** |

**WebSocket Flow (audio_stream_auth0.py):**
1. **connect:** Authenticate via `auth={'token': '...'}` → validate Auth0 JWT (RS256) → reject if invalid
2. **Initialize Deepgram:** Create live connection with Nova-2 model, dynamic language (from `?lang=` query param, default `en`)
3. **audio_chunk:** Base64-decode audio → send to Deepgram live stream
4. **Deepgram callbacks:** `on_message` → emit `transcription` event with transcript, is_final, confidence
5. **stop_streaming / disconnect:** Close Deepgram connection, cleanup active_connections dict

### SaaS Job Flow: Creating and Retrieving Jobs

#### JSON Mode (existing input_ref)
```
1. Client → POST /saas/jobs
   Headers: Authorization: Bearer <JWT access token>, Content-Type: application/json
   Body: {"type": "transcription", "input_ref": "s3://bucket/audio.wav"}

2. Flask routing → saas_jobs_bp.create_job()

3. Authentication:
   @jwt_required() decorator
   → Validate JWT access token (RS256, 1-hour expiration)
   → Check token_blacklist table (reject revoked tokens)
   → Extract user_id from JWT payload (get_jwt_identity())

4. Validation:
   → Verify required fields: type, input_ref
   → Validate type ∈ {transcription, translation}
   → Return 400 if invalid

5. Job Creation:
   job = Job(user_id=user_id, type=type, status='queued', input_ref=input_ref)
   db.session.add(job)
   db.session.commit()

6. Response:
   → Return 201 Created
   → JSON: job.to_dict() (includes id, user_id, type, status, created_at, artifacts=[])
```

#### File Upload Mode (new in STEP 3)
```
1. Client → POST /saas/jobs
   Headers: Authorization: Bearer <JWT access token>, Content-Type: multipart/form-data
   Body: type=transcription, file=<audio_file>

2. Authentication: @jwt_required() → extract user_id

3. Validation:
   → Verify required fields: type, file
   → Validate type ∈ {transcription, translation}
   → Return 400 if missing

4. Job Creation (pre-upload):
   job = Job(user_id=user_id, type=type, status='queued', input_ref='pending')
   db.session.add(job)
   db.session.flush()  # Get job.id without commit

5. Storage Upload:
   storage_service = get_storage_service()
   storage_path = storage_service.upload_input(
       user_id=user_id,
       job_id=job.id,
       file=file,
       original_filename=file.filename
   )
   → Validates file size (max 100MB default)
   → Validates content type (audio/*, video/*, text/*)
   → Uploads to: users/{user_id}/jobs/{job_id}/input/original.{ext}
   → Returns storage path or raises ValueError/RuntimeError

6. Job Update:
   job.input_ref = storage_path
   db.session.commit()
   → If upload fails: db.session.rollback(), return 400 or 500

7. Response:
   → Return 201 Created
   → JSON: job.to_dict() with input_ref = "users/{user_id}/jobs/{job_id}/input/original.wav"

```

#### List Jobs
```
Client → GET /saas/jobs?status=done&limit=10&offset=0
Headers: Authorization: Bearer <JWT access token>

1. Authentication: @jwt_required() → extract user_id

2. Query Building:
   → Base: Job.query.filter_by(user_id=user_id)
   → Apply filters: status, type (if provided)
   → Order: Job.created_at.desc() (newest first)
   → Pagination: limit (default 100, max 500), offset (default 0)

3. Execution:
   → Count total matches (before pagination)
   → Apply limit/offset
   → Fetch jobs with artifacts (eager loading)

4. Response:
   → Return 200 OK
   → JSON: {jobs: [...], total: N, limit: M, offset: O}
```

#### Get Job by ID
```
Client → GET /saas/jobs/123
Headers: Authorization: Bearer <JWT access token>

1. Authentication: @jwt_required() → extract user_id

2. Fetch Job:
   → Job.query.filter_by(id=job_id).first()
   → If not found: return 404

3. Ownership Check:
   → if job.user_id != user_id: return 403 Forbidden
   → Users can ONLY access their own jobs

4. Response:
   → Return 200 OK
   → JSON: job.to_dict() (includes all artifacts)
```

#### Get Job Artifacts (STEP 3)
```
Client → GET /saas/jobs/123/artifacts
Headers: Authorization: Bearer <JWT access token>

1. Authentication: @jwt_required() → extract user_id

2. Fetch Job & Verify Ownership:
   → Job.query.filter_by(id=job_id).first()
   → If not found: return 404
   → if job.user_id != user_id: return 403

3. Fetch Artifacts:
   → Artifact.query.filter_by(job_id=job_id).all()

4. Response:
   → Return 200 OK
   → JSON: {job_id: 123, artifacts: [{id, job_id, kind, storage_ref}, ...]}
```

#### Download Artifact via Signed URL (STEP 3)
```
Client → GET /saas/artifacts/456/download
Headers: Authorization: Bearer <JWT access token>

1. Authentication: @jwt_required() → extract user_id

2. Fetch Artifact:
   → Artifact.query.filter_by(id=artifact_id).first()
   → If not found: return 404

3. Verify Job Ownership:
   → job = Job.query.filter_by(id=artifact.job_id).first()
   → If not found: return 404
   → if job.user_id != user_id: return 403

4. Path Ownership Verification (additional security):
   → storage_service.verify_path_ownership(artifact.storage_ref, user_id)
   → if False: return 403 (path ownership mismatch)

5. Generate Signed URL:
   → signed_url = storage_service.generate_signed_url(artifact.storage_ref)
   → TTL: SIGNED_URL_TTL_SECONDS (default 300s = 5 minutes)
   → Raises RuntimeError if Supabase Storage fails

6. Response:
   → Return 200 OK
   → JSON: {artifact_id, job_id, kind, download_url, expires_in_seconds: 300}
```

**Key Design Decisions for SaaS Jobs:**

- **Minimal persistence:** No async workers, queues, or business logic - just database CRUD
- **User isolation:** Strict ownership enforcement at query level (users never see other users' jobs)
- **Synchronous:** Jobs are created immediately, status updates handled externally
- **Artifact references:** Storage refs only (no embedded data) - points to Supabase Storage
- **No rewriting:** Existing transcription/translation logic remains unchanged
- **JWT-only:** Uses Flask-JWT-Extended (@jwt_required) for authentication, not API keys
- **Storage integration (STEP 3):** Backend-only file uploads via Supabase Storage
  - **Path structure:** `users/{user_id}/jobs/{job_id}/input/original.{ext}` for inputs, `users/{user_id}/jobs/{job_id}/output/{artifact}.{ext}` for outputs
  - **Security:** Path-based ownership verification, signed URLs for downloads (5-min default TTL)
  - **Frontend never uploads directly:** All file uploads go through Flask backend (multipart/form-data → Supabase Storage)
  - **File validation:** Size limits (100MB default), MIME type checking (audio/*, video/*, text/*)
  - **Singleton service:** `get_storage_service()` ensures single Supabase client instance

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
   Auth: {token: '<Auth0 JWT>'}

2. SocketIO → handle_connect(auth)
   → authenticate_websocket(auth)
     → verify_websocket_token(token) [Auth0 JWT RS256]
     → Reject connection if token is invalid or expired
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
| `JWT_SECRET_KEY` | Flask-JWT-Extended signing | None | **REQUIRED** - app crashes if missing |
| `SECRET_KEY` | Flask session secret | None | **REQUIRED** - app crashes if missing |
| `SOCKETIO_ORIGINS` | WebSocket CORS allowlist (comma-separated) | None | **REQUIRED** - app crashes if missing |
| `AUTH0_DOMAIN` | Auth0 tenant domain | None | Required for Auth0 features |
| `AUTH0_AUDIENCE` | Auth0 API identifier | None | Required for Auth0 JWT validation |
| `AUTH0_REQUEST_TIMEOUT` | Timeout for Auth0 API calls (seconds) | `30` | Optional |
| `PORT` | HTTP bind port | `5000` | Auto-set by Render |
| `FLASK_ENV` | Environment (development/production) | development | Controls debug mode |
| `CORS_ORIGINS` / `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `*` | Tighten in prod |
| `LOG_LEVEL` | Logging verbosity | INFO | Optional |
| `SUPABASE_URL` | Supabase project URL | None | Required for storage (STEP 3) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (backend-only) | None | Required for storage (STEP 3) |
| `SUPABASE_STORAGE_BUCKET` | Supabase Storage bucket name | `saas-files` | Optional (defaults to saas-files) |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size in MB | `100` | Optional |
| `ALLOWED_UPLOAD_TYPES` | Comma-separated MIME types for uploads | audio/*, video/*, text/plain, application/json | Optional |
| `SIGNED_URL_TTL_SECONDS` | Download URL expiration time | `300` (5 min) | Optional |

### Configuration Loading Precedence
1. **Environment variables** (via `os.getenv()`)
2. **.env file** (via `python-dotenv` - for local dev)
3. **Hardcoded defaults** (in `utils/config.py` dataclasses)

### Render-Specific (render.yaml)
- `PORT`: Injected by Render platform (binds to 0.0.0.0:$PORT)
- `AUTH0_DOMAIN`, `DEEPGRAM_API_KEY`: Marked `sync: false` (manual secret entry in Render dashboard)
- `JWT_SECRET_KEY`, `SECRET_KEY`: Must be manually set in Render dashboard (app crashes without them)
- `SOCKETIO_ORIGINS`: Must be comma-separated list of allowed origins (e.g., `https://yourdomain.com,https://app.yourdomain.com`)

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
- **Auth0 (primary):** Enterprise-grade JWT authentication for production web/mobile apps with RS256 asymmetric signing
- **API Keys:** External integrations (Make.com, webhooks, scripts) - simpler auth for machine-to-machine

### Why JWT Token Expiration and Refresh?
- **Security:** Short-lived access tokens (1 hour) limit exposure if compromised
- **User experience:** Long-lived refresh tokens (30 days) avoid frequent re-authentication
- **Revocation:** Token blacklist enables immediate logout/invalidation via database persistence
- **Compliance:** Meets OWASP A07:2021 (Identification and Authentication Failures) requirements

### Why Eventlet for SocketIO?
- **Real-time requirement:** Deepgram live streaming needs persistent WebSocket connections
- **Gunicorn compatibility:** `-k eventlet` worker class required (not default sync workers)
- **Single worker:** `-w 1` to avoid connection state issues across workers

### Why Single WebSocket Handler (Auth0 Only)?
- **Security first:** Removed insecure session token fallback as of Step 1 Security Hardening (2026-01-17)
- **Auth0 only:** `audio_stream_auth0.py` now strictly validates RS256 JWT tokens
- **CORS enforcement:** WebSocket connections restricted to explicit origin allowlist via `SOCKETIO_ORIGINS` env var

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
│  • Supabase Storage (supabase.com) - File storage (STEP 3) │
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

1. **JWT Expiration Enforcement:** Access tokens expire after 1 hour, refresh tokens after 30 days. No perpetual tokens allowed.
2. **Token Revocation:** Logout immediately invalidates tokens via database blacklist. Revoked tokens cannot be reused.
3. **JWT Secret Rotation:** `JWT_SECRET_KEY` and `SECRET_KEY` are static post-deployment. Rotate manually if leaked (requires env var update + restart).
4. **Required Secrets:** App crashes at startup if `JWT_SECRET_KEY`, `SECRET_KEY`, or `SOCKETIO_ORIGINS` are missing. No default fallbacks.
5. **WebSocket CORS:** `SOCKETIO_ORIGINS` must be explicit comma-separated allowlist. Wildcard `*` rejected at startup.
6. **Database Credentials:** `DATABASE_URL` must use SSL in production (PostgreSQL `?sslmode=require`).
7. **API Key Storage:** User API keys are SHA256-hashed. Plaintext key shown ONCE on generation.
8. **Auth0 JWKS Caching:** PyJWKClient caches public keys locally (avoids JWKS endpoint hammering).
9. **Insecure Session Auth Removed:** All `/mobile-auth/*` endpoints and session token authentication deleted as of Step 1 Security Hardening (2026-01-17).
10. **Storage Security (STEP 3):**
    - **Backend-only uploads:** Frontend NEVER uploads directly to Supabase Storage. All uploads go through Flask backend with JWT validation.
    - **Path-based ownership:** Storage paths enforce ownership via `users/{user_id}/...` structure. Additional verification via `verify_path_ownership()`.
    - **Signed URLs:** Download URLs expire in 5 minutes (default). URLs are never persisted, generated on-demand only.
    - **Service role key:** `SUPABASE_SERVICE_ROLE_KEY` used for backend access. Never exposed to frontend.
    - **File validation:** Size limits (100MB default) and MIME type checking (audio/*, video/*, text/*) prevent abuse.
    - **Private bucket:** All files stored in private bucket. Public access disabled. Downloads require signed URLs.

---

## Future Considerations

1. **Remove core/ shim:** Complete migration to direct `flask_app` imports.
2. **Rate limiting:** Add per-user API throttling (via Flask-Limiter or Redis).
3. **Metrics:** Export Prometheus metrics (request counts, latency, Deepgram usage).
4. **Database migrations:** Implement Alembic/Flask-Migrate for schema versioning (currently using `db.create_all()` and manual script).
5. **Postprocessing placeholders:** Implement real sentiment analysis, document generation (currently stubs).
6. **Token blacklist cleanup:** Implement periodic job to purge expired tokens from `token_blacklist` table (currently unbounded growth).
