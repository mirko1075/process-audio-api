# Security Hardening Action Plan

## Purpose

This document identifies **concrete security vulnerabilities** in the current codebase and provides **actionable remediation steps**.

---

## ✅ COMPLETED (Step 1 Security Hardening)

The following critical security issues have been **FIXED** and deployed:

### ✅ 1. JWT Expiration Policy - IMPLEMENTED
**Status:** COMPLETE
**Implementation Date:** 2026-01-17

**Changes Made:**
- JWT access tokens now expire after 1 hour (`timedelta(hours=1)`)
- JWT refresh tokens expire after 30 days (`timedelta(days=30)`)
- Added `POST /auth/refresh` endpoint for token refresh
- Added `POST /auth/logout` endpoint for token revocation
- Created `TokenBlacklist` model for tracking revoked tokens
- Token revocation enforced via `@jwt.token_in_blocklist_loader`

**Files Modified:**
- `flask_app/__init__.py` - JWT configuration
- `flask_app/api/token_refresh.py` - New refresh/logout endpoints
- `models/token_blacklist.py` - Token blacklist model

### ✅ 2. Insecure Session Authentication - REMOVED
**Status:** COMPLETE
**Implementation Date:** 2026-01-17

**Changes Made:**
- Deleted `/mobile-auth/login`, `/mobile-auth/logout`, `/mobile-auth/verify` endpoints
- Deleted `flask_app/api/auth.py` (165 lines)
- Deleted `flask_app/services/session_manager.py` (148 lines)
- Deleted `flask_app/sockets/audio_stream.py` (274 lines - deprecated handler)
- Removed all `ALLOW_INSECURE_SESSION_AUTH` references
- WebSocket now ONLY accepts Auth0 JWT tokens

**Files Modified:**
- `flask_app/auth/auth0.py` - Removed session auth flag
- `flask_app/sockets/audio_stream_auth0.py` - Removed session fallback
- `flask_app/__init__.py` - Removed blueprint registration

### ✅ 3. CORS Policy Too Permissive - FIXED
**Status:** COMPLETE
**Implementation Date:** 2026-01-17

**Changes Made:**
- WebSocket CORS now reads from `SOCKETIO_ORIGINS` environment variable
- Wildcard `*` removed - explicit origin allowlist required
- App crashes at startup if `SOCKETIO_ORIGINS` not set
- Production: `https://meeting-streamer.vercel.app`
- Development: `http://localhost:3000,http://127.0.0.1:3000`

**Files Modified:**
- `flask_app/__init__.py` - CORS enforcement
- `render.yaml` - Added SOCKETIO_ORIGINS env var
- `.env.example` - Added SOCKETIO_ORIGINS documentation

### ✅ 4. Hardcoded Secrets - ENFORCED
**Status:** COMPLETE
**Implementation Date:** 2026-01-17

**Changes Made:**
- Removed default fallback values for `JWT_SECRET_KEY` and `SECRET_KEY`
- App crashes at startup if either secret is missing
- Secrets must be set in environment variables (Render dashboard)
- No plaintext secrets in code

**Files Modified:**
- `flask_app/__init__.py` - Secret enforcement
- `render.yaml` - Secret configuration (sync: false)
- `.env.example` - Secret generation instructions

---

## Remaining Priorities (Post-MVP)

### 1. JWT Expiration Policy Missing
**Risk Level:** CRITICAL
**Location:** [flask_app/__init__.py:42](flask_app/__init__.py#L42)
**Current State:**
```python
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Tokens don't expire by default
```

**Vulnerability:**
- JWT tokens issued via `/auth/login` **NEVER expire**
- Stolen/leaked tokens remain valid indefinitely
- No mechanism to revoke compromised tokens
- Violates OWASP A07:2021 (Identification and Authentication Failures)

**Impact:**
- If an attacker obtains a JWT token (e.g., via XSS, MITM, or client compromise), they have permanent API access as that user
- No way to force re-authentication for compromised accounts
- Compliance violations (PCI DSS, SOC 2 require token expiration)

**Remediation Steps:**
1. Change `JWT_ACCESS_TOKEN_EXPIRES` to `timedelta(hours=1)` for short-lived access tokens
2. Implement refresh token pattern:
   - Add `JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)`
   - Create `/auth/refresh` endpoint to exchange refresh token for new access token
   - Store refresh tokens in database with revocation capability
3. Add token revocation table:
   - `TokenBlacklist` model with `jti` (JWT ID) and `revoked_at` timestamp
   - Check blacklist in `@require_jwt` decorator before accepting token
4. Add `/auth/logout` endpoint that blacklists the current token
5. Add admin endpoint `/auth/revoke-user-tokens/{user_id}` to revoke all tokens for a user

**Testing:**
- Verify tokens expire after 1 hour (should get 401 "Token has expired")
- Test refresh token flow (exchange old token for new)
- Test logout (token should be rejected after logout)

---

### 2. Insecure Session Authentication System
**Risk Level:** CRITICAL
**Location:** [flask_app/api/auth.py](flask_app/api/auth.py), [flask_app/services/session_manager.py](flask_app/services/session_manager.py)
**Current State:**
- Endpoint `/mobile-auth/login` generates session tokens **WITHOUT verifying passwords**
- Code comment: `# ⚠️ SECURITY ISSUE: No password validation!`
- Only blocked when `ALLOW_INSECURE_SESSION_AUTH=false` (env var gate)
- Session storage: In-memory dict (not persistent, not multi-worker safe)

**Vulnerability:**
```python
# From flask_app/api/auth.py:78-80
username = data.get('username')
# ⚠️ SECURITY ISSUE: No password validation!
# This allows ANYONE to create a session for ANY username
session_data = session_manager.create_session(username, expires_hours=24)
```

**Impact:**
- **COMPLETE AUTHENTICATION BYPASS** when `ALLOW_INSECURE_SESSION_AUTH=true`
- Attacker can impersonate any user by sending `{"username": "victim@email.com"}`
- No audit trail of unauthorized access (just looks like normal login)
- Mobile app using this endpoint has NO real authentication
- Session tokens lost on service restart (in-memory storage)
- Not safe for multi-worker deployments (sessions not shared across workers)

**Remediation Steps:**
1. **IMMEDIATE (Production):** Verify `ALLOW_INSECURE_SESSION_AUTH=false` in Render dashboard
2. **Short-term (This Sprint):**
   - Migrate mobile app to Auth0 authentication
   - Remove endpoints: `/mobile-auth/login`, `/mobile-auth/logout`, `/mobile-auth/verify`
   - Delete file: `flask_app/api/auth.py` (mobile auth blueprint)
   - Remove session manager code: `flask_app/services/session_manager.py`
   - Remove WebSocket handler: `flask_app/sockets/audio_stream.py` (session-only version)
   - Remove session manager import and instantiation from codebase
3. **Testing:**
   - Confirm mobile app can authenticate via Auth0
   - Verify WebSocket connections use Auth0 JWT tokens
   - Ensure `/mobile-auth/*` endpoints return 404 after removal

**Workaround (If Mobile App Cannot Migrate Yet):**
- Keep endpoints but add **real password verification:**
  ```python
  # Lookup user in database
  user = User.query.filter_by(email=username).first()
  if not user or not user.check_password(password):
      return jsonify({'error': 'Invalid credentials'}), 401
  ```
- Migrate to database-backed sessions (not in-memory dict)
- Add rate limiting (5 failed attempts = 15 min lockout)
- Log all failed login attempts to detect brute force

---

### 3. CORS Policy Too Permissive (WebSocket)
**Risk Level:** HIGH
**Location:** [flask_app/__init__.py:59-62](flask_app/__init__.py#L59-L62)
**Current State:**
```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Allow all origins for WebSocket
    ...
)
```

**Vulnerability:**
- WebSocket endpoint `/audio-stream` accepts connections from **ANY origin**
- Enables Cross-Site WebSocket Hijacking (CSWSH)
- Attacker can create malicious site that connects to victim's WebSocket and steals real-time transcriptions

**Attack Scenario:**
1. User authenticates to your app, gets Auth0 token (stored in localStorage)
2. User visits attacker's site: `evil.com`
3. Attacker's JavaScript reads token from localStorage (if same-domain cookie not used) OR tricks user into pasting token
4. Attacker connects to `wss://yourapp.onrender.com/audio-stream` with stolen token
5. Attacker receives victim's audio transcriptions in real-time

**Impact:**
- Data exfiltration (transcriptions, user IDs)
- Privacy violation (eavesdropping on audio streams)
- Compliance violation (GDPR, HIPAA if handling sensitive data)

**Remediation Steps:**
1. **Immediate Fix:**
   ```python
   ALLOWED_ORIGINS = [
       "https://meeting-streamer.vercel.app",  # Production frontend
       "https://staging.vercel.app",           # Staging
       "http://localhost:3000",                # Local dev
       "http://127.0.0.1:3000"                 # Local dev
   ]
   socketio = SocketIO(
       app,
       cors_allowed_origins=ALLOWED_ORIGINS,
       ...
   )
   ```
2. **Use Environment Variable:**
   - Set `SOCKETIO_ORIGINS` env var in Render
   - Read in code: `cors_allowed_origins=os.getenv("SOCKETIO_ORIGINS", "").split(",")`
3. **Add Origin Validation in WebSocket Handler:**
   ```python
   # In handle_connect():
   origin = request.headers.get('Origin')
   if origin not in ALLOWED_ORIGINS:
       logger.warning(f"Rejected connection from unauthorized origin: {origin}")
       return False
   ```
4. **Testing:**
   - Verify connection works from allowed origins
   - Verify connection **fails** from `http://localhost:8000` (not in whitelist)
   - Check Render logs for "Rejected connection from unauthorized origin" messages

---

### 4. Hardcoded Secrets in Configuration Defaults
**Risk Level:** HIGH
**Location:** [flask_app/__init__.py:40-41](flask_app/__init__.py#L40-L41)
**Current State:**
```python
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
```

**Vulnerability:**
- If env vars not set, app uses **publicly visible default secrets** from GitHub repo
- Attacker can forge JWT tokens using default secret
- Attacker can decrypt Flask session cookies

**Impact:**
- **Complete authentication bypass** (forge admin JWT tokens)
- Session hijacking (decrypt and modify session cookies)
- Persistence across restarts (default secrets don't change)

**Remediation Steps:**
1. **Remove Defaults:**
   ```python
   JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
   SECRET_KEY = os.getenv('SECRET_KEY')

   if not JWT_SECRET_KEY or not SECRET_KEY:
       raise RuntimeError("CRITICAL: JWT_SECRET_KEY and SECRET_KEY must be set in environment variables")

   app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
   app.config['SECRET_KEY'] = SECRET_KEY
   ```
2. **Production Verification:**
   - Check Render dashboard: Both secrets should be set and non-default
   - `JWT_SECRET_KEY` should use `generateValue: true` (already in render.yaml)
   - `SECRET_KEY` should be manually set to random value: `openssl rand -base64 32`
3. **Rotate Secrets:**
   - Generate new `SECRET_KEY`: `openssl rand -base64 32`
   - Update in Render dashboard
   - **Warning:** This invalidates all existing sessions (users logged out)
4. **Testing:**
   - Start app locally without env vars → should crash with "CRITICAL: ..." error
   - Start with env vars → should boot normally

---

## High Priority (Fix Within 30 Days)

### 5. Missing Rate Limiting
**Risk Level:** HIGH
**Affected Endpoints:** All public endpoints (especially `/auth/login`, `/auth/register`, `/mobile-auth/login`, transcription endpoints)
**Current State:** No rate limiting implemented

**Vulnerability:**
- Brute force attacks on `/auth/login` (unlimited password attempts)
- Credential stuffing (attacker tries stolen username/password pairs)
- Denial of Service (flood API with requests)
- Resource exhaustion (expensive transcription API calls)

**Attack Scenarios:**
1. **Brute Force:**
   ```bash
   for password in passwords.txt; do
     curl -X POST /auth/login -d "{\"email\": \"admin@example.com\", \"password\": \"$password\"}"
   done
   ```
2. **API Abuse:**
   ```bash
   while true; do
     curl -X POST /transcriptions/deepgram -F "audio=@large.wav" -H "x-api-key: stolen_key"
   done
   ```

**Remediation Steps:**
1. **Add Flask-Limiter Dependency:**
   ```
   # In requirements.txt:
   Flask-Limiter==3.5.0
   ```
2. **Configure Global Limits:**
   ```python
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address

   limiter = Limiter(
       app=app,
       key_func=get_remote_address,  # Rate limit by IP
       default_limits=["1000 per day", "100 per hour"],
       storage_uri="memory://"  # Use Redis in production: "redis://..."
   )
   ```
3. **Add Endpoint-Specific Limits:**
   ```python
   @bp.route('/login', methods=['POST'])
   @limiter.limit("5 per minute")  # Max 5 login attempts per minute
   def login():
       ...

   @bp.route('/transcriptions/deepgram', methods=['POST'])
   @limiter.limit("10 per minute")  # Max 10 transcriptions per minute
   def deepgram_transcription():
       ...
   ```
4. **Use Redis for Distributed Rate Limiting:**
   - Add to Render: Redis service (or external Redis)
   - Update `storage_uri="redis://<redis_url>"`
   - Required for multi-worker setups
5. **Testing:**
   - Make 6 login requests in 1 minute → 6th should return `429 Too Many Requests`
   - Check response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

### 6. No Input Validation for File Uploads
**Risk Level:** HIGH
**Location:** All transcription endpoints accepting file uploads
**Current Issues:**
- No MIME type validation (accepts any file with `.wav` extension)
- File size limits only enforced in specific services (not globally)
- Malicious filenames not sanitized (e.g., `../../etc/passwd.wav`)

**Vulnerability:**
- **Path Traversal:** Attacker uploads file named `../../../tmp/evil.py` → overwrite system files
- **Resource Exhaustion:** Upload 10GB file → fills disk, crashes service
- **Malware Upload:** Upload executable disguised as `.wav` → execute on server (if video processing bug)

**Remediation Steps:**
1. **Add File Validation Decorator:**
   ```python
   from werkzeug.utils import secure_filename
   from pathlib import Path

   def validate_audio_upload(max_size_mb=100, allowed_extensions={'.wav', '.mp3', '.m4a', '.flac', '.ogg'}):
       def decorator(f):
           @wraps(f)
           def wrapper(*args, **kwargs):
               if 'audio' not in request.files:
                   return jsonify({'error': 'No audio file provided'}), 400

               file = request.files['audio']

               # Validate filename
               if not file.filename:
                   return jsonify({'error': 'No filename provided'}), 400

               # Check extension
               ext = Path(file.filename).suffix.lower()
               if ext not in allowed_extensions:
                   return jsonify({'error': f'Unsupported file type: {ext}'}), 400

               # Sanitize filename (prevent path traversal)
               secure_name = secure_filename(file.filename)
               if secure_name != file.filename:
                   logger.warning(f"Rejected malicious filename: {file.filename}")
                   return jsonify({'error': 'Invalid filename'}), 400

               # Check file size
               file.seek(0, os.SEEK_END)
               size_bytes = file.tell()
               file.seek(0)  # Reset file pointer

               if size_bytes > max_size_mb * 1024 * 1024:
                   return jsonify({'error': f'File too large (max {max_size_mb}MB)'}), 413

               return f(*args, **kwargs)
           return wrapper
       return decorator

   # Usage:
   @bp.route('/transcriptions/deepgram', methods=['POST'])
   @validate_audio_upload(max_size_mb=100)
   def deepgram_transcription():
       ...
   ```
2. **Add MIME Type Validation:**
   ```python
   import magic  # pip install python-magic

   # Check actual file type (not just extension)
   file_type = magic.from_buffer(file.read(2048), mime=True)
   file.seek(0)

   allowed_mimes = {'audio/wav', 'audio/mpeg', 'audio/mp4', 'audio/flac', 'audio/ogg'}
   if file_type not in allowed_mimes:
       return jsonify({'error': f'Invalid file type: {file_type}'}), 400
   ```
3. **Global File Size Limit (Nginx/Gunicorn):**
   - Gunicorn: Add `--limit-request-line 8190 --limit-request-fields 100`
   - Nginx (if using reverse proxy): `client_max_body_size 100M;`
4. **Testing:**
   - Upload file named `../../etc/passwd.wav` → should be rejected
   - Upload 101MB file → should return `413 File too large`
   - Upload .exe file renamed to .wav → should be rejected (MIME check)

---

### 7. Error Messages Leak Implementation Details
**Risk Level:** MEDIUM
**Location:** Multiple error handlers (global + blueprint-specific)
**Current State:**
```python
except Exception as e:
    logger.error(f"Unexpected error in Deepgram transcription: {e}")
    return jsonify({'error': 'Internal server error'}), 500
```

**Vulnerability:**
- Error messages in logs include full stack traces (good for debugging, bad if logs leaked)
- Some endpoints return raw exception messages to client (e.g., database errors)
- Exposes technology stack, file paths, SQL queries to attackers

**Examples:**
```python
# Bad - Leaks file path:
{"error": "File not found: /opt/render/project/src/temp/audio_12345.wav"}

# Bad - Leaks database schema:
{"error": "column users.secret_field does not exist"}

# Good - Generic message:
{"error": "Failed to process audio file"}
```

**Remediation Steps:**
1. **Create Error Message Sanitizer:**
   ```python
   def sanitize_error_for_client(error: Exception, debug=False):
       """Return safe error message for client."""
       if debug:
           return str(error)  # Full details in dev

       # Production: generic messages
       error_map = {
           'FileNotFoundError': 'File not found',
           'PermissionError': 'Access denied',
           'SQLAlchemyError': 'Database error',
           'TranscriptionError': 'Transcription failed',
           'TranslationError': 'Translation failed',
       }

       error_type = type(error).__name__
       return error_map.get(error_type, 'Internal server error')
   ```
2. **Update Error Handlers:**
   ```python
   @bp.errorhandler(Exception)
   def handle_generic_error(error):
       # Log full details (for debugging)
       logger.error(f"Error in {request.path}: {error}", exc_info=True)

       # Return sanitized message to client
       safe_message = sanitize_error_for_client(error, debug=app.debug)
       return jsonify({'error': safe_message}), 500
   ```
3. **Audit Existing Error Returns:**
   - Search codebase for: `return jsonify({'error': str(e)})`
   - Replace with sanitized messages
4. **Testing:**
   - Trigger error in production mode → response should be generic
   - Trigger same error in dev mode (`FLASK_ENV=development`) → response should include details
   - Check logs → should have full stack trace even in production

---

### 8. Database Connection String in Logs
**Risk Level:** MEDIUM
**Location:** Application startup logs, SQLAlchemy debug mode
**Current State:**
- If `DATABASE_URL` misconfigured, error logs may print full connection string (including password)
- Example: `sqlalchemy.exc.OperationalError: could not connect to server at postgresql://user:PASSWORD@host:5432/db`

**Vulnerability:**
- Database credentials leaked in logs
- If logs exported to third-party service (Datadog, Splunk), credentials exposed
- Render logs accessible to all team members (credential sprawl)

**Remediation Steps:**
1. **Add Log Sanitizer:**
   ```python
   import re
   import logging

   class SensitiveDataFilter(logging.Filter):
       """Remove sensitive data from log messages."""

       PATTERNS = [
           (re.compile(r'postgresql://[^:]+:([^@]+)@'), r'postgresql://***:REDACTED@'),
           (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)'), r'api_key=REDACTED'),
           (re.compile(r'Bearer ([a-zA-Z0-9_\-\.]+)'), r'Bearer REDACTED'),
           (re.compile(r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)'), r'token=REDACTED'),
       ]

       def filter(self, record):
           message = record.getMessage()
           for pattern, replacement in self.PATTERNS:
               message = pattern.sub(replacement, message)
           record.msg = message
           return True

   # Apply to all loggers:
   logging.basicConfig(level=logging.INFO)
   for handler in logging.root.handlers:
       handler.addFilter(SensitiveDataFilter())
   ```
2. **Disable SQLAlchemy Echo in Production:**
   ```python
   # In flask_app/__init__.py:
   app.config['SQLALCHEMY_ECHO'] = app.debug  # Only echo SQL in dev mode
   ```
3. **Testing:**
   - Trigger database connection error → check logs for password redaction
   - Enable debug mode → verify SQL queries logged
   - Production mode → verify no SQL queries in logs

---

## Medium Priority (Fix Within 60 Days)

### 9. No API Key Rotation Policy
**Risk Level:** MEDIUM
**Current State:**
- User API keys never expire (`expires_at` is nullable and usually NULL)
- No mechanism to force rotation
- Leaked keys remain valid indefinitely

**Remediation Steps:**
1. Add `expires_at` default (1 year from creation):
   ```python
   # In models/user.py:ApiKey
   expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=365))
   ```
2. Check expiration in `verify_key()`:
   ```python
   if api_key.expires_at and api_key.expires_at < datetime.utcnow():
       logger.warning(f"Expired API key used: {api_key.id}")
       return None
   ```
3. Add endpoint `/auth/api-keys/{id}/renew` to extend expiration
4. Email users 30 days before key expiration
5. Create admin dashboard to audit key ages

---

### 10. Missing HTTPS Enforcement
**Risk Level:** MEDIUM (if Render doesn't enforce)
**Current State:**
- No explicit HTTPS redirect in app code
- Relies on Render platform to enforce HTTPS

**Remediation Steps:**
1. Add Flask-Talisman for security headers:
   ```python
   from flask_talisman import Talisman

   Talisman(app,
            force_https=True,
            strict_transport_security=True,
            content_security_policy=None)  # Configure CSP separately
   ```
2. Add security headers:
   ```python
   @app.after_request
   def set_security_headers(response):
       response.headers['X-Content-Type-Options'] = 'nosniff'
       response.headers['X-Frame-Options'] = 'DENY'
       response.headers['X-XSS-Protection'] = '1; mode=block'
       response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
       return response
   ```
3. Verify in Render: Auto-HTTPS enabled (should be default)

---

### 11. SQL Injection Risk (Low but Present)
**Risk Level:** MEDIUM
**Current State:**
- Using SQLAlchemy ORM (prevents most SQL injection)
- No raw SQL queries found in codebase (good)
- But: If future developer adds raw queries, risk increases

**Preventive Actions:**
1. Add linting rule to detect raw SQL:
   ```python
   # In .pylintrc or bandit config:
   [bandit]
   exclude = tests/*
   tests = B608  # Flag db.execute() with string interpolation
   ```
2. Document safe query patterns:
   ```python
   # SAFE - Parameterized query:
   db.session.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})

   # UNSAFE - String interpolation:
   db.session.execute(f"SELECT * FROM users WHERE id = {user_id}")  # NEVER DO THIS
   ```
3. Add code review checklist item: "No raw SQL with user input"

---

### 12. Session Storage Memory Leak Risk
**Risk Level:** MEDIUM
**Location:** [flask_app/services/session_manager.py](flask_app/services/session_manager.py)
**Current State:**
- Sessions stored in-memory dict (`self._sessions: Dict[str, Dict] = {}`)
- No automatic cleanup of expired sessions
- Manual cleanup via `cleanup_expired_sessions()` method (not scheduled)

**Vulnerability:**
- Memory grows unbounded as sessions accumulate
- Expired sessions remain in memory forever unless manually cleaned
- Service restart required to clear accumulated sessions

**Remediation Steps:**
1. **Immediate (if keeping session auth):**
   - Add periodic cleanup cron job or background task
   - Example: APScheduler to run `cleanup_expired_sessions()` every hour
2. **Long-term:**
   - Migrate to database-backed sessions (SQLAlchemy session table)
   - OR migrate to Redis-backed sessions (redis://...)
   - OR remove session auth entirely (migrate to Auth0)
3. **Monitoring:**
   - Log session count in health check endpoint
   - Alert if session count > 10,000

---

## Low Priority (Fix When Convenient)

### 13. No Content Security Policy (CSP)
**Risk Level:** LOW (API-only, no HTML served)
**Recommendation:** Add CSP header if serving any HTML (e.g., Swagger docs):
```python
response.headers['Content-Security-Policy'] = "default-src 'none'"
```

---

### 14. Database Credentials Shared Across Environments
**Risk Level:** LOW (organizational risk)
**Recommendation:**
- Use separate PostgreSQL databases for dev/staging/prod
- Never use production `DATABASE_URL` locally
- Rotate production DB password quarterly

---

### 15. No API Request Signing
**Risk Level:** LOW (nice-to-have for high-security scenarios)
**Recommendation:**
- Implement HMAC request signing for API keys (like AWS Signature V4)
- Prevents replay attacks and man-in-the-middle tampering
- Example: `X-Signature: HMAC-SHA256(API_SECRET, request_body + timestamp)`

---

## Security Audit Checklist

After implementing fixes, verify:

- [ ] JWT tokens expire (check `exp` claim in decoded token)
- [ ] Session auth endpoints removed OR properly secured with password verification
- [ ] CORS origins whitelist enforced (test from disallowed origin → connection rejected)
- [ ] Rate limiting active (make 100 requests in 1 minute → some return 429)
- [ ] File upload validation (upload malicious filename → rejected)
- [ ] Error messages sanitized (trigger error in production → no stack traces in response)
- [ ] API keys expire after 1 year (check `expires_at` in database)
- [ ] HTTPS enforced (access via http:// → redirects to https://)
- [ ] Security headers present (`curl -I https://yourapp.onrender.com | grep X-Frame-Options`)
- [ ] Secrets not in default config (start app without env vars → crash with error)
- [ ] Logs sanitized (trigger DB error → check logs for password redaction)
- [ ] Session storage monitored (check session count < 10K)

---

## Compliance Mapping

| Requirement | OWASP Top 10 | Action Items | Status |
|------------|--------------|--------------|--------|
| Token expiration | A07:2021 Auth Failures | #1 (JWT expiry) | **Not Fixed** |
| Authentication bypass | A07:2021 Auth Failures | #2 (Session auth) | **Not Fixed** |
| CORS policy | A05:2021 Security Misconfig | #3 (WebSocket CORS) | **Not Fixed** |
| Secret management | A02:2021 Cryptographic Failures | #4 (Hardcoded secrets) | **Not Fixed** |
| Rate limiting | A05:2021 Security Misconfig | #5 (DoS protection) | **Not Fixed** |
| File upload validation | A03:2021 Injection | #6 (Path traversal) | **Not Fixed** |
| Information disclosure | A05:2021 Security Misconfig | #7 (Error messages) | **Not Fixed** |
| Credential logging | A09:2021 Logging Failures | #8 (Log sanitization) | **Not Fixed** |
| Session persistence | A05:2021 Security Misconfig | #12 (Memory leak) | **Not Fixed** |

---

## Next Steps

1. **Prioritize fixes** based on risk level and effort
2. **Create GitHub issues** for each action item (link to this doc)
3. **Assign ownership** for each fix
4. **Set deadlines** based on priority tiers
5. **Schedule security review** after all critical items fixed
6. **Pen test** after all high priority items fixed
7. **Update this doc** as fixes are deployed (mark "Status: Fixed")

---

## Known Issues Summary

| Issue | Severity | Affected Components | Proposed Fix |
|-------|----------|---------------------|--------------|
| JWT never expires | CRITICAL | `/auth/login`, JWT decorator | Add expiration + refresh tokens |
| No password validation | CRITICAL | `/mobile-auth/login` | Remove endpoint OR add password check |
| Session memory leak | MEDIUM | SessionManager in-memory dict | Add cleanup cron OR migrate to database |
| Wildcard CORS | HIGH | WebSocket `/audio-stream` | Whitelist specific origins |
| Hardcoded secrets | HIGH | App config defaults | Remove defaults, require env vars |
| No rate limiting | HIGH | All endpoints | Add Flask-Limiter |
| No file validation | HIGH | File upload endpoints | Add validation decorator + MIME check |
| Error message leakage | MEDIUM | All error handlers | Sanitize messages for production |
| Logs leak credentials | MEDIUM | Logging infrastructure | Add log sanitization filter |
