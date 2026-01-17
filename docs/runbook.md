# Operational Runbook

## Overview

This runbook provides step-by-step debugging procedures for common failure scenarios in the Audio Transcription API. Use these playbooks when investigating production incidents.

---

## Table of Contents

1. [How to Debug a Failed Transcription](#1-how-to-debug-a-failed-transcription)
2. [How to Debug a Failed Translation](#2-how-to-debug-a-failed-translation)
3. [How to Debug WebSocket Audio Streaming](#3-how-to-debug-websocket-audio-streaming)
4. [Common Failure Modes](#4-common-failure-modes)

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
→ Using audio_stream_auth0.py (PREFERRED)

Pattern: "WebSocket handlers (session-based) registered successfully"
→ Using audio_stream.py (DEPRECATED)

Pattern: "WebSocket handlers not found: ..."
→ No handler registered (critical failure)
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

# Common failures:
1. Token expired → Client needs to refresh token
2. Wrong audience → AUTH0_AUDIENCE mismatch
3. Invalid signature → JWKS key rotation issue (clear PyJWKClient cache - restart service)
```

##### Session Token Validation (Deprecated)
```bash
# Only works if ALLOW_INSECURE_SESSION_AUTH=true

# Check Render logs:
"⚠️ SECURITY WARNING: ALLOW_INSECURE_SESSION_AUTH is enabled"
→ Session fallback active (BAD in production)

"Session token fallback disabled (secure mode)"
→ Session tokens rejected (GOOD in production)

# Test session token:
# First login to get token:
curl -X POST https://yourapp.onrender.com/mobile-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "ignored"}'  # NO PASSWORD CHECK!

# Response:
{"auth_token": "session_xyz123", "user_id": "testuser", "expires_at": "..."}

# Then use in WebSocket:
wscat -c "wss://yourapp.onrender.com/audio-stream?lang=en" \
  --connect-option '{"auth": {"token": "session_xyz123"}}'

# Note: Session tokens stored in-memory (lost on restart)
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
| "Connection rejected: Invalid or expired authentication token" | JWT expired or invalid | Client needs to refresh Auth0 token |
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

## 4. Common Failure Modes

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
- [ ] Monitor session count (if ALLOW_INSECURE_SESSION_AUTH=true): `session_manager.get_session_count()`
- [ ] Run session cleanup (if using sessions): `session_manager.cleanup_expired_sessions()`

### Monthly
- [ ] Review and rotate API keys (if leaked)
- [ ] Update dependencies (security patches)
- [ ] Review Auth0 user logs for anomalies
- [ ] Database cleanup (old UsageLog entries if > 1M rows)

### Quarterly
- [ ] Audit user permissions (active API keys)
- [ ] Review CORS origins (remove deprecated URLs)
- [ ] Performance testing (load test with JMeter/Locust)
- [ ] Disaster recovery drill (test database restore)
