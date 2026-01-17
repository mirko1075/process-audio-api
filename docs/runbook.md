# Operational Runbook

## Overview

This runbook provides step-by-step debugging procedures for common failure scenarios in the Audio Transcription API. Use these playbooks when investigating production incidents.

---

## Table of Contents

1. [How to Debug a Failed Transcription](#1-how-to-debug-a-failed-transcription)
2. [How to Debug a Failed Translation](#2-how-to-debug-a-failed-translation)
3. [How to Debug WebSocket Audio Streaming](#3-how-to-debug-websocket-audio-streaming)
4. [How to Debug JWT Authentication Issues](#4-how-to-debug-jwt-authentication-issues)
5. [Common Failure Modes](#5-common-failure-modes)

---

## 1. How to Debug a Failed Transcription

### Symptoms
- HTTP 400/500 response from `/transcriptions/deepgram`, `/transcriptions/whisper`, or `/transcriptions/assemblyai`
- Empty transcript returned
- Client timeout waiting for response
- Error: "TranscriptionError: ..."

### Investigation Steps

#### Step 1: Identify the Service Provider
```
Request endpoint determines provider:
• /transcriptions/deepgram → DeepgramService
• /transcriptions/whisper → WhisperService (OpenAI)
• /transcriptions/assemblyai → AssemblyAIService
• /transcriptions/video → VideoTranscriptionService (Whisper)
```

#### Step 2: Check Render Logs
```bash
# Access Render Dashboard → Logs tab
# Search for error patterns:

Pattern: "Deepgram transcription failed: ..."
Location: flask_app/services/transcription.py:DeepgramService.transcribe()

Pattern: "Whisper transcription failed: ..."
Location: flask_app/services/transcription.py:WhisperService.transcribe()

Pattern: "AssemblyAI transcription failed: ..."
Location: flask_app/services/transcription.py:AssemblyAIService.transcribe()
```

#### Step 3: Verify API Keys
```bash
# Check environment variables in Render Dashboard:
DEEPGRAM_API_KEY = *********** (set?)
OPENAI_API_KEY = *********** (set?)
ASSEMBLYAI_API_KEY = *********** (set?)

# Test key validity (local):
curl -H "Authorization: Token $DEEPGRAM_API_KEY" \
  https://api.deepgram.com/v1/listen \
  -X POST \
  -F "audio=@test.wav"

# Expected: Valid transcription OR specific error (invalid key, quota exceeded)
```

#### Step 4: Verify Audio File Format
```bash
# Common issues:
• File too large (Whisper max: 25MB per chunk, auto-chunking enabled)
• Unsupported format (accepts: wav, mp3, m4a, flac, ogg, webm)
• Corrupted file (ffmpeg fails to read)

# Test locally:
ffprobe test_audio.wav
# Check: codec, sample_rate, duration

# Whisper expects: 16kHz sample rate (auto-converted by service)
# Deepgram accepts: any sample rate
```

#### Step 5: Check Provider Service Status
```
Deepgram: https://status.deepgram.com
OpenAI: https://status.openai.com
AssemblyAI: https://status.assemblyai.com

If provider is down:
→ Retry with different provider (e.g., switch Deepgram → Whisper)
```

#### Step 6: Inspect Service-Specific Errors

##### Deepgram Errors
```python
# File: flask_app/clients/deepgram.py
# Common errors:

1. "Invalid API key"
   → Check DEEPGRAM_API_KEY

2. "Unsupported language: xyz"
   → Verify language code in request (e.g., 'en', 'es', 'fr')
   → See supported languages in Deepgram docs

3. "Audio file too short" (< 0.5s)
   → Check audio file duration with ffprobe

4. "Rate limit exceeded"
   → Check Deepgram dashboard for quota
   → Implement retry with exponential backoff (to be added)
```

##### Whisper Errors
```python
# File: flask_app/clients/openai.py
# Common errors:

1. "File size exceeds 25MB limit"
   → Should not occur (auto-chunking implemented at >20MB threshold)
   → Check logs for chunking errors

2. "Invalid audio format"
   → ffmpeg conversion failed
   → Check audio file codec: ffprobe test.wav

3. "OpenAI API error: 429 Too Many Requests"
   → Rate limit hit (60 RPM for Whisper API)
   → Retry after 60 seconds

4. "Insufficient quota"
   → Check OpenAI billing dashboard
   → Add credits or upgrade plan
```

##### AssemblyAI Errors
```python
# File: flask_app/clients/assemblyai.py
# Common errors:

1. "Upload failed"
   → Network issue or AssemblyAI outage
   → Check status.assemblyai.com

2. "Transcription timeout"
   → Large file took > 10 minutes
   → Check AssemblyAI dashboard for job status

3. "Invalid API key"
   → Check ASSEMBLYAI_API_KEY
```

#### Step 7: Test End-to-End
```bash
# Minimal test case:
curl -X POST https://yourapp.onrender.com/transcriptions/deepgram \
  -H "x-api-key: YOUR_API_KEY" \
  -F "audio=@short_test.wav" \
  -F "language=en"

# Expected success response:
{
  "transcript": "Hello world",
  "processing_info": {
    "service": "deepgram",
    "model_used": "nova-2",
    "language_requested": "en",
    "diarization_enabled": false
  },
  "confidence": 0.95
}

# Expected error response:
{
  "error": "Deepgram transcription failed: [specific error]"
}
```

### Resolution Patterns

| Error | Root Cause | Fix |
|-------|-----------|-----|
| "Missing required environment variables: DEEPGRAM_API_KEY" | Config issue | Set env var in Render dashboard |
| "Failed to save audio file: [Errno 28] No space left on device" | Disk full | Restart service (clears /tmp), upgrade instance |
| "TranscriptionError: Connection timeout" | Provider API slow/down | Retry, check provider status page |
| Empty transcript returned | Silent audio file | Verify audio has speech content |
| "Invalid language code" | Client sent unsupported language | Return 400 with list of supported languages |

---

## 2. How to Debug a Failed Translation

### Symptoms
- HTTP 400/500 response from `/translations/openai`, `/translations/google`, or `/translations/deepseek`
- Empty translation returned
- Error: "TranslationError: ..."

### Investigation Steps

#### Step 1: Identify Translation Provider
```
Endpoint mapping:
• /translations/openai → OpenAITranslationService (GPT-4o-mini)
• /translations/google → GoogleTranslationService (Google Cloud Translate)
• /translations/deepseek → DeepSeekTranslationService (+ webhook integration)
```

#### Step 2: Check Render Logs
```bash
# Search patterns:

"OpenAI translation failed: ..."
Location: flask_app/services/translation.py:OpenAITranslationService.translate()

"Google translation failed: ..."
Location: flask_app/services/translation.py:GoogleTranslationService.translate()

"DeepSeek translation failed: ..."
Location: flask_app/services/translation.py:DeepSeekTranslationService.translate()
```

#### Step 3: Verify Configuration

##### OpenAI Translation
```bash
# Check:
OPENAI_API_KEY = *********** (set?)

# Test:
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Translate to Spanish: Hello"}]}'

# Expected: Valid translation OR error (invalid key, quota)
```

##### Google Translation
```bash
# Check:
GOOGLE_APPLICATION_CREDENTIALS = /path/to/service-account.json

# Test:
gcloud auth activate-service-account \
  --key-file=$GOOGLE_APPLICATION_CREDENTIALS
gcloud projects list

# Expected: Service account has access to projects

# Verify API enabled:
gcloud services list --enabled | grep translate
# Expected: translate.googleapis.com ENABLED
```

##### DeepSeek Translation
```bash
# Check:
DEEPSEEK_API_KEY = *********** (set?)

# Test:
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-chat", "messages": [{"role": "user", "content": "Translate to English: Bonjour"}]}'

# Expected: Valid translation OR error (invalid key, quota)

# Test webhook integration:
curl -X POST https://hook.eu2.make.com/... \
  -d "translation=test&transcription=test&fileName=test.wav"

# Expected: 200 OK from Make.com webhook
```

#### Step 4: Check Request Payload
```bash
# Common issues:

1. Empty text:
   {"text": ""}
   → Returns 400: "Text cannot be empty"

2. Missing target_language:
   {"text": "Hello"}  # Missing target_language
   → Returns 400: "Missing required field: target_language"

3. Unsupported language pair (Google):
   {"text": "Hello", "target_language": "zzzz"}
   → Google API error: "Invalid language code"

4. Text too long (OpenAI):
   • Max tokens: ~118,000 for GPT-4o-mini (conservative limit: 120K - 2K buffer)
   • Auto-chunking implemented (splits by sentences at 15K tokens per chunk)
   • Check logs for "chunks_processed" count
```

#### Step 5: Test Provider-Specific Issues

##### OpenAI Translation Errors
```python
# File: flask_app/clients/openai.py

1. "OpenAI API error: 429 Too Many Requests"
   → Rate limit: 10,000 TPM (tokens per minute)
   → Retry with exponential backoff

2. "Context length exceeded"
   → Text + translation prompt > 120K tokens
   → Auto-chunking should handle this (check logs for chunking activation)

3. "Model overloaded"
   → OpenAI capacity issue
   → Retry or switch to Google Translate
```

##### Google Translation Errors
```python
# File: flask_app/clients/google.py

1. "Service account not found"
   → GOOGLE_APPLICATION_CREDENTIALS path wrong
   → Verify file exists: ls -la $GOOGLE_APPLICATION_CREDENTIALS

2. "Permission denied"
   → Service account lacks Cloud Translation API permission
   → Add role: Cloud Translation API User

3. "Quota exceeded"
   → Monthly character limit hit
   → Check GCP billing dashboard
```

##### DeepSeek Translation Errors
```python
# File: flask_app/clients/deepseek.py + services/translation.py

1. "ValueError: DEEPSEEK_API_KEY environment variable is required"
   → Missing API key
   → Set DEEPSEEK_API_KEY in Render dashboard

2. "DeepSeek API error: [status code]"
   → Check DeepSeek API status (status page URL to be confirmed)
   → Verify API key validity

3. "Failed to send request to external service"
   → Webhook (Make.com) unreachable
   → Check webhook URL in code (hardcoded in DeepSeekTranslationService)
   → Verify Make.com scenario is active

4. "Webhook request failed: 500"
   → Make.com scenario error
   → Check Make.com logs for execution history
```

#### Step 6: Test End-to-End
```bash
# OpenAI translation:
curl -X POST https://yourapp.onrender.com/translations/openai \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_language": "en", "target_language": "es"}'

# Expected:
{
  "translated_text": "Hola mundo",
  "source_language": "en",
  "target_language": "es",
  "model_used": "gpt-4o-mini",
  "service": "openai_gpt"
}

# For large text (chunking test):
{
  "translated_text": "...",
  "chunks_processed": 3,
  "total_chunks": 3
}

# Google translation:
curl -X POST https://yourapp.onrender.com/translations/google \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "target_language": "es"}'

# Expected:
{
  "translated_text": "Hola mundo",
  "detected_source_language": "en"
}

# DeepSeek translation:
curl -X POST https://yourapp.onrender.com/translations/deepseek \
  -H "x-api-key: YOUR_API_KEY" \
  -F "text=Hello world" \
  -F "source_language=en" \
  -F "target_language=es"

# Expected:
{
  "translated_text": "Hola mundo"
}
# Or (if webhook integration):
{
  "message": "Request sent to external service"
}
```

### Resolution Patterns

| Error | Root Cause | Fix |
|-------|-----------|-----|
| "Missing OPENAI_API_KEY" | Config missing | Set in Render dashboard |
| "Google Cloud credentials not found" | File path wrong | Upload service account JSON to /opt/render/project/src/google/ |
| "Invalid target_language" | Client sent bad language code | Return 400 with supported language list |
| "Webhook request failed" | Make.com down or scenario disabled | Reactivate scenario, check Make.com status |
| Empty translation | Provider API issue | Retry with different provider |
| "ValueError: DEEPSEEK_API_KEY environment variable is required" | Missing DeepSeek key | Set DEEPSEEK_API_KEY in Render |

---

## 3. How to Debug WebSocket Audio Streaming

### Symptoms
- Client cannot connect to `wss://.../audio-stream`
- Connection established but no transcription events received
- Connection drops after few seconds
- Error: "Connection rejected: ..."

### Investigation Steps

#### Step 1: Verify WebSocket Handler
```bash
# Check Render logs for handler registration:

Pattern: "WebSocket handlers (Auth0-enabled) registered successfully"
→ Using audio_stream_auth0.py (Auth0 JWT only)

Pattern: "WebSocket handlers not found: ..."
→ No handler registered (critical failure)

Note: Session-based WebSocket handler (audio_stream.py) removed as of Step 1 Security Hardening (2026-01-17)
```

#### Step 2: Test Connection Handshake
```bash
# Using wscat (install: npm install -g wscat):

# With Auth0 JWT:
wscat -c "wss://yourapp.onrender.com/audio-stream?lang=en" \
  -H "Authorization: Bearer <AUTH0_JWT_TOKEN>"

# Or via SocketIO handshake auth:
# (requires SocketIO client library - see client code)

# Expected on success:
Connected
< {"message": "Successfully connected to audio streaming service", "user_id": "auth0|123", "auth_type": "auth0", "language": "en", "timestamp": "..."}

# Expected on auth failure:
Connection rejected
< {"message": "Connection rejected: Invalid or expired authentication token", "timestamp": "..."}
```

#### Step 3: Check Authentication Issues

##### Auth0 JWT Validation
```bash
# Decode JWT to inspect claims (use jwt.io or):
echo "<JWT_TOKEN>" | cut -d'.' -f2 | base64 -d | jq .

# Verify:
• "iss": "https://<AUTH0_DOMAIN>/"  (matches AUTH0_DOMAIN env var)
• "aud": "<AUTH0_AUDIENCE>"  (matches AUTH0_AUDIENCE env var)
• "exp": <timestamp>  (not expired: exp > current Unix time)
• "sub": "auth0|123"  (user ID present)
• "jti": "<unique_token_id>"  (JWT ID for revocation tracking)

# Common failures:
1. Token expired → Client needs to refresh token via POST /auth/refresh
2. Wrong audience → AUTH0_AUDIENCE mismatch
3. Invalid signature → JWKS key rotation issue (clear PyJWKClient cache - restart service)
4. Token revoked → Check token_blacklist table for this jti
```

##### JWT Token Expiration and Refresh
```bash
# Access token expiration: 1 hour
# Refresh token expiration: 30 days

# If client gets 401 "Token has expired":
1. Client should call POST /auth/refresh with refresh token
2. Server returns new access token (valid for 1 hour)
3. Client uses new access token for subsequent requests

# Test refresh endpoint:
curl -X POST https://yourapp.onrender.com/auth/refresh \
  -H "Authorization: Bearer <REFRESH_TOKEN>"

# Expected success:
{"access_token": "<NEW_ACCESS_TOKEN>"}

# Expected failure (expired refresh token):
{"msg": "Token has expired"}
→ Client must re-authenticate via Auth0 login flow

# Test logout (revoke token):
curl -X POST https://yourapp.onrender.com/auth/logout \
  -H "Authorization: Bearer <ACCESS_OR_REFRESH_TOKEN>"

# Expected:
{"msg": "Access token revoked successfully"}
# OR
{"msg": "Refresh token revoked successfully"}

# Verify revocation in database:
psql $DATABASE_URL -c "SELECT jti, token_type, revoked_at FROM token_blacklist ORDER BY revoked_at DESC LIMIT 5;"
```

##### Session Token Validation (REMOVED)
```bash
# Session authentication removed as of Step 1 Security Hardening (2026-01-17)
# All /mobile-auth/* endpoints deleted
# ALLOW_INSECURE_SESSION_AUTH environment variable no longer supported
# WebSocket now requires Auth0 JWT only
```

#### Step 4: Check Deepgram Integration
```bash
# Render logs patterns:

Pattern: "Deepgram connection opened"
→ Deepgram live connection established

Pattern: "Deepgram error: ..."
→ Deepgram API issue (key invalid, quota exceeded, service down)

Pattern: "Failed to start Deepgram connection"
→ LiveOptions configuration error or API key missing

# Verify Deepgram API key:
curl -H "Authorization: Token $DEEPGRAM_API_KEY" \
  https://api.deepgram.com/v1/projects

# Expected: List of projects OR error (invalid key)
```

#### Step 5: Test Audio Streaming
```javascript
// Client-side test (JavaScript):

const socket = io('wss://yourapp.onrender.com/audio-stream?lang=it', {
  auth: { token: '<AUTH0_JWT_TOKEN>' }
});

socket.on('connected', (data) => {
  console.log('Connected:', data);
  // Start sending audio chunks
});

socket.on('transcription', (data) => {
  console.log('Transcript:', data.transcript);
  console.log('Is final:', data.is_final);
  console.log('Confidence:', data.confidence);
});

socket.on('error', (data) => {
  console.error('Error:', data.message);
});

// Send audio chunk (Base64-encoded PCM 16kHz):
socket.emit('audio_chunk', {
  audio_chunk: '<base64_audio_data>',
  timestamp: new Date().toISOString()
});
```

#### Step 6: Verify Language Selection
```bash
# Language passed via query parameter:
wss://yourapp.onrender.com/audio-stream?lang=it  # Italian
wss://yourapp.onrender.com/audio-stream?lang=en  # English
wss://yourapp.onrender.com/audio-stream  # Default: en

# Check Render logs:
"Language set to 'it' for user auth0|123"
→ Correct language selected

"Invalid language 'xyz' requested by user ... Defaulting to 'en'"
→ Unsupported language code (check SUPPORTED_LANGUAGES list)

# Supported languages (30+):
en, es, fr, it, de, pt, nl, hi, ja, ko, zh, sv, no, da, fi, pl, ru, tr, ar, el, he, cs, uk, ro, hu, id, ms, th, vi
```

#### Step 7: Check Connection State Management
```bash
# Render logs patterns:

"WebSocket connected: user_id=X, auth_type=auth0"
→ Connection added to active_connections dict

"WebSocket disconnected: user_id=X"
→ Connection removed from active_connections

"Audio chunk received from unknown connection: ..."
→ Connection not in active_connections (client reconnect needed)

"Deepgram connection not open, cannot send audio"
→ is_deepgram_open=False (Deepgram failed to start or crashed)
```

### Common WebSocket Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Connection rejected: No authentication token provided" | Client didn't send `auth: {token}` | Add auth parameter to SocketIO connection |
| "Connection rejected: Invalid or expired authentication token" | JWT expired or invalid | Client needs to refresh token via POST /auth/refresh |
| "Connection rejected: Token has been revoked" | Token in blacklist (user logged out) | Client must re-authenticate via Auth0 login flow |
| "Transcription service error" | Deepgram API failure | Check DEEPGRAM_API_KEY, Deepgram status |
| "Invalid audio data format" | Base64 decode failed | Verify audio_chunk is valid Base64 string |
| "Connection not initialized" | Client sent audio before receiving 'connected' event | Wait for 'connected' before sending chunks |
| No transcription events received | Silent audio or wrong encoding | Verify: 16kHz sample rate, linear16 PCM encoding |
| Connection drops after 30s | Render timeout | Send periodic keepalive pings OR audio chunks |

### Resolution Patterns

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Cannot connect | Missing Auth0 token | Get token from Auth0 login flow |
| Connects but no transcripts | Wrong audio format | Ensure 16kHz, linear16, mono PCM |
| Transcripts in wrong language | Query param missing/wrong | Add `?lang=it` to WebSocket URL |
| Random disconnects | Deepgram error | Check Deepgram API status, key quota |
| Memory leak (connections not cleaned up) | Disconnect handler not running | Check logs for disconnect events, restart service |

---

## 4. How to Debug JWT Authentication Issues

### Symptoms
- 401 "Token has expired" errors
- 422 "Token signature verification failed" errors
- Client unable to refresh access token
- Logout (token revocation) not working

### Investigation Steps

#### Step 1: Verify Environment Variables
```bash
# Check Render Dashboard → Environment:
JWT_SECRET_KEY = *********** (set? REQUIRED - app crashes if missing)
SECRET_KEY = *********** (set? REQUIRED - app crashes if missing)
AUTH0_DOMAIN = *********** (set?)
AUTH0_AUDIENCE = *********** (set?)

# If any are missing, app will crash at startup with:
RuntimeError: JWT_SECRET_KEY environment variable is required
RuntimeError: SECRET_KEY environment variable is required
```

#### Step 2: Check Token Expiration Configuration
```bash
# Verify JWT expiration settings in logs at startup:
# Look for log messages from flask_app/__init__.py:

Pattern: "JWT_ACCESS_TOKEN_EXPIRES = 1 hour"
→ Access tokens configured correctly

Pattern: "JWT_REFRESH_TOKEN_EXPIRES = 30 days"
→ Refresh tokens configured correctly

# If not found, check flask_app/__init__.py:
# Should have:
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
```

#### Step 3: Test Token Refresh Flow
```bash
# Step 1: Get initial tokens from Auth0 login
# (Use your frontend login flow or Auth0 dashboard test)

# Step 2: Test access token works
curl -X GET https://yourapp.onrender.com/api/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Expected: User info returned

# Step 3: Wait >1 hour or force expiration, then test refresh
curl -X POST https://yourapp.onrender.com/auth/refresh \
  -H "Authorization: Bearer <REFRESH_TOKEN>"

# Expected success:
{
  "access_token": "<NEW_ACCESS_TOKEN>"
}

# Expected failure (if refresh token also expired):
{
  "msg": "Token has expired"
}

# Expected failure (if refresh token revoked):
{
  "msg": "Token has been revoked"
}

# Step 4: Verify new access token works
curl -X GET https://yourapp.onrender.com/api/me \
  -H "Authorization: Bearer <NEW_ACCESS_TOKEN>"
```

#### Step 4: Test Token Revocation (Logout)
```bash
# Logout with access token:
curl -X POST https://yourapp.onrender.com/auth/logout \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Expected:
{"msg": "Access token revoked successfully"}

# Verify token is blacklisted:
psql $DATABASE_URL -c "SELECT * FROM token_blacklist ORDER BY revoked_at DESC LIMIT 1;"

# Expected output:
 id |        jti        | token_type | user_id |      revoked_at      |      expires_at
----+-------------------+------------+---------+----------------------+---------------------
  1 | abc-123-def-456   | access     | auth0|x | 2026-01-17 10:30:00  | 2026-01-17 11:30:00

# Try to use revoked token:
curl -X GET https://yourapp.onrender.com/api/me \
  -H "Authorization: Bearer <REVOKED_ACCESS_TOKEN>"

# Expected:
{"msg": "Token has been revoked"}
```

#### Step 5: Check Token Blacklist Table
```bash
# Verify token_blacklist table exists:
psql $DATABASE_URL -c "\dt token_blacklist"

# Expected:
            List of relations
 Schema |      Name       | Type  |  Owner
--------+-----------------+-------+---------
 public | token_blacklist | table | postgres

# If table doesn't exist, run migration:
python scripts/migrate_add_token_blacklist.py

# Check blacklist entries:
psql $DATABASE_URL -c "SELECT COUNT(*) FROM token_blacklist;"

# If count > 10000, consider cleanup job to delete expired entries
```

#### Step 6: Troubleshoot Common JWT Errors

##### Error: "Token has expired"
```bash
# Cause: Access token expired (> 1 hour old) or refresh token expired (> 30 days old)

# Fix for client:
1. If access token expired: Call POST /auth/refresh with refresh token
2. If refresh token expired: Re-authenticate via Auth0 login flow
3. Implement automatic token refresh in client (refresh when exp - now < 5 minutes)
```

##### Error: "Token has been revoked"
```bash
# Cause: User called POST /auth/logout and token is in blacklist

# Fix for client:
1. Clear local token storage
2. Redirect to login page
3. User must re-authenticate via Auth0

# Debug server-side:
psql $DATABASE_URL -c "SELECT * FROM token_blacklist WHERE jti = '<TOKEN_JTI>';"
# If entry exists, token was deliberately revoked
```

##### Error: "Signature verification failed"
```bash
# Cause: JWT_SECRET_KEY mismatch or token corrupted

# Fix:
1. Verify JWT_SECRET_KEY not changed recently (check Render deploy history)
2. If changed, all existing tokens are invalid - users must re-login
3. Check token format: Should be xxx.yyy.zzz (3 parts separated by dots)
4. Decode token at jwt.io to verify structure
```

##### Error: "Missing Authorization Header"
```bash
# Cause: Client not sending Authorization: Bearer <token>

# Fix for client:
1. Add header: Authorization: Bearer <access_token>
2. For refresh endpoint: Use refresh_token not access_token
3. Check client code sends header for ALL protected endpoints
```

#### Step 7: Monitor Token Blacklist Growth
```bash
# Check blacklist size:
psql $DATABASE_URL -c "SELECT COUNT(*) as total, token_type, COUNT(*) FROM token_blacklist GROUP BY token_type;"

# Expected output:
 total | token_type | count
-------+------------+-------
   150 | access     |   100
       | refresh    |    50

# If total > 50000, implement cleanup job:
# Delete tokens where expires_at < NOW() - INTERVAL '7 days'
psql $DATABASE_URL -c "DELETE FROM token_blacklist WHERE expires_at < NOW() - INTERVAL '7 days';"

# Add to cron or scheduled task (future enhancement)
```

### Resolution Patterns

| Error | Root Cause | Fix |
|-------|-----------|-----|
| "JWT_SECRET_KEY environment variable is required" | Missing config | Set JWT_SECRET_KEY in Render dashboard, redeploy |
| "Token has expired" (access token) | > 1 hour old | Client calls POST /auth/refresh with refresh token |
| "Token has expired" (refresh token) | > 30 days old | User must re-authenticate via Auth0 login |
| "Token has been revoked" | User logged out | Client clears tokens, redirects to login |
| "Signature verification failed" | JWT_SECRET_KEY changed | All users must re-login (tokens invalidated) |
| token_blacklist table missing | Migration not run | Run `python scripts/migrate_add_token_blacklist.py` |
| Blacklist growing unbounded | No cleanup job | Implement periodic DELETE of expired tokens |

---

## 5. Common Failure Modes

### Database Connection Failures

#### Symptoms
- 500 errors on all authenticated endpoints
- Logs: "sqlalchemy.exc.OperationalError: could not connect to server"
- App starts but first API call fails

#### Investigation
```bash
# Check DATABASE_URL:
echo $DATABASE_URL  # In Render dashboard → Environment

# Test connection (from local or SSH):
psql "$DATABASE_URL"

# Common issues:
1. PostgreSQL service down → Check Render dashboard for DB status
2. Wrong connection string → Verify host, port, username, password
3. SSL required but not in URL → Add ?sslmode=require
4. Connection pool exhausted → Restart service, check for connection leaks
```

#### Resolution
```bash
# If database is down:
1. Check Render DB service status
2. Restart DB service if needed
3. Wait for DB health check to pass
4. Restart web service to reconnect

# If connection string wrong:
1. Render Dashboard → Database → Connection String
2. Copy correct DATABASE_URL
3. Update in Web Service → Environment
4. Trigger manual deploy (restart)
```

### Auth0 Configuration Issues

#### Symptoms
- 401 errors on /api/me, /api/userinfo
- Logs: "AUTH0_DOMAIN environment variable not set"
- Logs: "Token verification failed"

#### Investigation
```bash
# Check env vars:
AUTH0_DOMAIN = *********** (set?)
AUTH0_AUDIENCE = *********** (set?)

# Verify Auth0 application settings:
1. Go to Auth0 Dashboard → Applications → Your App
2. Check:
   • Domain matches AUTH0_DOMAIN env var
   • Identifier (Audience) matches AUTH0_AUDIENCE
   • Signing Algorithm = RS256 (NOT HS256)
   • Token Endpoint Authentication Method = None (for SPAs) or Post (for web apps)

# Test JWKS endpoint:
curl https://<AUTH0_DOMAIN>/.well-known/jwks.json

# Expected: JSON with public keys
```

#### Resolution
```bash
# If env vars missing:
1. Render Dashboard → Environment → Add Variable
2. Set AUTH0_DOMAIN (without https://)
3. Set AUTH0_AUDIENCE (API identifier from Auth0)
4. Trigger manual deploy

# If JWT validation fails:
1. Verify algorithm is RS256 (not HS256)
2. Check token expiration (decode JWT at jwt.io)
3. Verify audience claim matches AUTH0_AUDIENCE
4. Clear PyJWKClient cache (restart service)
```

### External API Failures

#### Symptoms
- Specific service fails (Deepgram, OpenAI, DeepSeek, Google) while others work
- Logs: "Connection timeout", "429 Too Many Requests", "Service Unavailable"

#### Investigation
```bash
# Check service status pages:
Deepgram: https://status.deepgram.com
OpenAI: https://status.openai.com
Google Cloud: https://status.cloud.google.com
DeepSeek: (Status page URL to be confirmed)

# Check API quotas:
Deepgram: Dashboard → Usage
OpenAI: Dashboard → Usage Limits
Google Cloud: Console → APIs & Services → Quotas
DeepSeek: Dashboard (to be confirmed)

# Test API connectivity (from Render shell or local):
# Deepgram:
curl -H "Authorization: Token $DEEPGRAM_API_KEY" \
  https://api.deepgram.com/v1/projects

# OpenAI:
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# DeepSeek:
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-chat", "messages": [{"role": "user", "content": "Hello"}]}'

# Google Translate:
curl -X POST https://translation.googleapis.com/language/translate/v2 \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d "q=hello&target=es"
```

#### Resolution
```bash
# If service is down:
→ Wait for recovery (check status page for ETA)
→ Switch to alternative provider (e.g., Deepgram → Whisper)

# If quota exceeded:
Deepgram: Upgrade plan or wait for monthly reset
OpenAI: Add credits or upgrade tier
DeepSeek: Upgrade plan or contact support
Google Cloud: Request quota increase

# If API key invalid:
1. Regenerate key in provider dashboard
2. Update env var in Render
3. Trigger manual deploy
```

### Configuration Drift

#### Symptoms
- Works locally but fails in production
- Works in staging but fails in production
- Sudden failures after deploy with "no code changes"

#### Investigation
```bash
# Compare environment variables:
# Local (.env file):
cat .env

# Render production:
Render Dashboard → Environment → View All

# Check for:
• Missing env vars (present locally but not in Render)
• Different values (e.g., wrong API keys)
• Typos in variable names

# Compare dependency versions:
# Local:
pip freeze | grep Flask

# Render (check build logs):
Render Dashboard → Logs → Filter for "Collecting Flask..."
```

#### Resolution
```bash
# Sync env vars:
1. Create checklist from .env.example (if exists)
2. Verify each var in Render dashboard
3. Add missing vars
4. Trigger manual deploy

# Lock dependency versions:
# In requirements.txt, use exact versions:
Flask==3.1.0  # NOT Flask>=3.0
deepgram-sdk==3.10.0  # NOT deepgram-sdk
```

### Memory/Resource Exhaustion

#### Symptoms
- App crashes after running for hours/days
- Logs: "MemoryError", "Out of memory"
- Render kills process: "Process exited with code 137" (OOM killed)

#### Investigation
```bash
# Check Render metrics:
Dashboard → Metrics → Memory Usage

# Look for:
• Steadily increasing memory (memory leak)
• Sudden spikes during specific operations
• Correlation with active WebSocket connections

# Likely causes:
1. WebSocket connections not cleaned up (active_connections dict growing)
2. Session tokens accumulating in-memory (SessionManager._sessions dict)
3. Temporary files not deleted (check /tmp)
4. ML models loaded multiple times (whisper, transformers)
5. Large file uploads buffered in memory
```

#### Resolution
```bash
# Short-term:
Restart service to clear memory

# Long-term:
1. Upgrade Render plan (more RAM)
2. Add connection cleanup logging:
   • Log active_connections.keys() on each connect/disconnect
   • Alert if > 100 connections
3. Implement connection timeouts (disconnect idle clients)
4. Add session cleanup cron job:
   • Call session_manager.cleanup_expired_sessions() periodically
   • Log session count: session_manager.get_session_count()
5. Add file size limits (reject uploads > 100MB)
6. Use streaming file uploads (not in-memory buffering)
```

### CORS Errors

#### Symptoms
- Frontend gets "CORS policy blocked" error
- OPTIONS preflight request fails
- Request succeeds in Postman/curl but fails in browser

#### Investigation
```bash
# Check CORS configuration:
# File: flask_app/__init__.py

CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"],
     supports_credentials=True)

# Verify frontend URL matches:
Frontend URL: https://meeting-streamer.vercel.app
CORS origins: Should include https://meeting-streamer.vercel.app

# Test OPTIONS request:
curl -X OPTIONS https://yourapp.onrender.com/transcriptions/deepgram \
  -H "Origin: https://meeting-streamer.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Expected headers in response:
Access-Control-Allow-Origin: https://meeting-streamer.vercel.app
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: x-api-key, Content-Type
```

#### Resolution
```bash
# Update CORS origins:
# File: flask_app/__init__.py
CORS(app, origins=[
  "http://localhost:3000",  # Local dev
  "https://meeting-streamer.vercel.app",  # Production frontend
  "https://staging.vercel.app"  # Staging
], supports_credentials=True)

# Or use environment variable:
origins = os.getenv("CORS_ORIGINS", "*").split(",")
CORS(app, origins=origins, supports_credentials=True)

# Set in Render:
CORS_ORIGINS = https://meeting-streamer.vercel.app,http://localhost:3000

# Redeploy to apply changes
```

---

## Emergency Procedures

### Critical Incident Response

#### Severity 1: Complete Service Outage
```
1. Check Render status: https://status.render.com
2. Check health endpoint: curl https://yourapp.onrender.com/health
3. If health fails: Check Render logs for crash/panic
4. If Render issue: Monitor status page, no action needed
5. If app issue:
   a. Identify error in logs (last 50 lines before crash)
   b. Check recent deploys (within last 24h)
   c. Rollback to previous working version
   d. Notify team with incident details
```

#### Severity 2: Degraded Service (One Feature Down)
```
1. Identify failing feature (transcription, translation, WebSocket)
2. Check external service status (Deepgram, OpenAI, DeepSeek, Auth0)
3. If external outage: Switch to alternative provider OR wait
4. If configuration issue: Fix env var, redeploy
5. Document workaround for users
```

#### Severity 3: Performance Degradation
```
1. Check Render metrics (CPU, memory, request queue)
2. Check database slow query log (if accessible)
3. Check external API latency (Deepgram status page)
4. If high load: Consider scaling plan or adding rate limiting
5. If database slow: Restart DB service, add indexes
6. If memory leak: Check session count, WebSocket connections
```

### On-Call Checklist

```
□ Access to Render dashboard (login credentials saved)
□ Access to Auth0 dashboard
□ Access to external service dashboards (Deepgram, OpenAI, DeepSeek)
□ Rollback procedure tested
□ Recent backup of database available (automated by Render)
□ Emergency contact list updated (team members, providers)
□ Incident response runbook reviewed (this document)
```

---

## Maintenance Tasks

### Weekly
- [ ] Review Render logs for WARNING/ERROR patterns
- [ ] Check external service usage (Deepgram, OpenAI, DeepSeek quotas)
- [ ] Verify database backups are running (Render automated backups)
- [ ] Monitor token blacklist size: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM token_blacklist;"`
- [ ] Check for expired tokens: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM token_blacklist WHERE expires_at < NOW();"`

### Monthly
- [ ] Review and rotate API keys (if leaked)
- [ ] Update dependencies (security patches)
- [ ] Review Auth0 user logs for anomalies
- [ ] Database cleanup (old UsageLog entries if > 1M rows)
- [ ] Token blacklist cleanup: Delete expired tokens older than 7 days
- [ ] Verify JWT expiration configuration hasn't changed

### Quarterly
- [ ] Audit user permissions (active API keys)
- [ ] Review CORS origins (remove deprecated URLs)
- [ ] Performance testing (load test with JMeter/Locust)
- [ ] Disaster recovery drill (test database restore)
