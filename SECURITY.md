# Security Fix: Authentication Bypass Vulnerability

## Date: December 5, 2025
## Severity: 🔴 CRITICAL
## Status: ✅ RESOLVED

---

## Vulnerability Description

### The Problem

The WebSocket `/audio-stream` endpoint accepted **two types of authentication**:

1. **Auth0 JWT tokens** (secure, properly authenticated)
2. **Session tokens** from `/mobile-auth/login` (insecure, NO authentication)

The `/mobile-auth/login` endpoint had a **critical security flaw**:

```python
@bp.route('/login', methods=['POST'])
def login():
    username = data.get('username')
    # ⚠️ NO PASSWORD VERIFICATION!
    # Creates session token for ANY username without checking credentials
    session_data = session_manager.create_session(username, expires_hours=24)
    return jsonify(session_data), 200
```

### Attack Scenario

**Any unauthenticated client could:**

1. Call `/mobile-auth/login` with `{"username": "fake_user"}`
2. Receive a valid session token (no credentials checked!)
3. Use that token to connect to `/audio-stream` WebSocket
4. Freely consume Deepgram transcription services
5. Access all WebSocket-protected features

**Cost Impact:**
- Deepgram charges per minute of audio transcription
- Attackers could rack up thousands of dollars in API costs
- No way to track or block malicious users

---

## Solution Implemented

### 1. Feature Flag for Insecure Auth

Added `ALLOW_INSECURE_SESSION_AUTH` environment variable:

```bash
# Production (SECURE - default)
ALLOW_INSECURE_SESSION_AUTH=false  # or omit entirely

# Development/Testing ONLY
ALLOW_INSECURE_SESSION_AUTH=true
```

**Default behavior:** Secure mode (session auth disabled)

### 2. Updated WebSocket Authentication

**Before:**
```python
# Always accepted both Auth0 JWT and session tokens
try:
    verify_auth0_jwt(token)
except:
    verify_session_token(token)  # ⚠️ No real auth!
```

**After:**
```python
# Try Auth0 JWT first (REQUIRED in production)
try:
    return verify_auth0_jwt(token)
except Auth0Error:
    # Session fallback ONLY if explicitly enabled
    if ALLOW_INSECURE_SESSION_AUTH:
        logger.warning("⚠️  Using insecure session auth - DEV ONLY!")
        return verify_session_token(token)
    else:
        raise Exception("Only Auth0 JWT tokens accepted in production")
```

### 3. Deprecated Mobile Auth Endpoints

All endpoints in `/mobile-auth/*` now:

1. **Return 403 Forbidden** in production (secure mode)
2. **Log security warnings** when used in dev mode
3. **Include deprecation notices** in responses

```python
@bp.route('/login', methods=['POST'])
def login():
    # Block in production
    if not ALLOW_INSECURE_SESSION_AUTH:
        return jsonify({
            'error': 'endpoint_disabled',
            'message': 'Use Auth0 authentication in production'
        }), 403
    
    logger.warning("⚠️  INSECURE endpoint used - DEV ONLY!")
    # ... rest of insecure code
```

### 4. Updated Production Configuration

**render.yaml:**
```yaml
envVars:
  # Explicitly disable insecure auth in production
  - key: ALLOW_INSECURE_SESSION_AUTH
    value: "false"
  
  # Required Auth0 configuration
  - key: AUTH0_DOMAIN
    sync: false
  - key: AUTH0_AUDIENCE
    sync: false
```

---

## Security Impact

### Before Fix (VULNERABLE)

| Endpoint | Auth Required | Credentials Checked | Exploitable |
|----------|--------------|---------------------|-------------|
| `/mobile-auth/login` | ❌ No | ❌ No | ✅ YES |
| `/audio-stream` WebSocket | ⚠️ Sort of | ❌ Session bypass | ✅ YES |

**Attack Vector:**  
→ Call `/mobile-auth/login` → Get token → Use token on WebSocket → Unlimited access

### After Fix (SECURE)

| Endpoint | Auth Required | Credentials Checked | Exploitable |
|----------|--------------|---------------------|-------------|
| `/mobile-auth/login` | ✅ Disabled in prod | N/A | ❌ NO |
| `/audio-stream` WebSocket | ✅ Auth0 JWT only | ✅ Yes (Auth0) | ❌ NO |

**Attack Vector:**  
→ Must obtain valid Auth0 JWT → Requires authentication → Access controlled

---

## Deployment Guide

### Production Deployment (Secure Mode - RECOMMENDED)

```bash
# render.yaml or environment variables
ALLOW_INSECURE_SESSION_AUTH=false  # or omit entirely
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://your-api.com
```

**Behavior:**
- ✅ Only Auth0 JWT tokens accepted
- ✅ `/mobile-auth/*` endpoints return 403
- ✅ WebSocket connections require valid Auth0 authentication
- ✅ No authentication bypass possible

**Logs:**
```
INFO: Session token fallback disabled (secure mode)
INFO: Only Auth0 JWT tokens are accepted
WARNING: Attempt to use deprecated /mobile-auth/login endpoint in secure mode
```

### Development/Testing Mode (Insecure - DEV ONLY)

```bash
# .env.local or development configuration
ALLOW_INSECURE_SESSION_AUTH=true
AUTH0_DOMAIN=dev-tenant.auth0.com
AUTH0_AUDIENCE=https://dev-api.com
```

**Behavior:**
- ⚠️ Both Auth0 JWT and session tokens accepted
- ⚠️ `/mobile-auth/*` endpoints enabled
- ⚠️ Session tokens created without credential verification

**Logs:**
```
WARNING: ⚠️ SECURITY WARNING: ALLOW_INSECURE_SESSION_AUTH is enabled!
WARNING: Session token fallback allows unauthenticated access.
WARNING: This should NEVER be enabled in production.
WARNING: ⚠️ Using insecure session auth - development mode only!
```

---

## Testing the Fix

### Test 1: Production Mode (Secure)

```bash
# Set secure mode
export ALLOW_INSECURE_SESSION_AUTH=false

# Try to use mobile auth
curl -X POST http://localhost:5000/mobile-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "attacker"}'

# Expected response:
{
  "error": "endpoint_disabled",
  "message": "This endpoint is disabled in production. Use Auth0 authentication.",
  "details": "Set ALLOW_INSECURE_SESSION_AUTH=true only in development/testing."
}
```

### Test 2: WebSocket Connection (Secure Mode)

```javascript
// Try to connect with fake session token
const socket = io('/audio-stream', {
  auth: { token: 'fake_session_token' }
});

// Expected: Connection rejected
// Error: "Invalid or expired authentication token. Please provide a valid Auth0 JWT token."
```

### Test 3: Auth0 JWT (Should Work)

```javascript
// Connect with valid Auth0 JWT
const socket = io('/audio-stream', {
  auth: { token: 'eyJhbGciOiJSUzI1NiIs...' }  // Valid Auth0 JWT
});

// Expected: Connection successful
// User authenticated via Auth0
```

---

## Migration Path for Existing Clients

### Mobile App Migration

If you have existing mobile apps using `/mobile-auth/login`:

#### Option 1: Implement Auth0 in Mobile App (RECOMMENDED)

```javascript
// Install Auth0 SDK
import Auth0 from 'react-native-auth0';

// Initialize Auth0
const auth0 = new Auth0({
  domain: 'your-tenant.auth0.com',
  clientId: 'your-client-id'
});

// Login and get JWT
const credentials = await auth0.webAuth.authorize({
  scope: 'openid profile email'
});

// Use JWT for WebSocket
const socket = io('/audio-stream', {
  auth: { token: credentials.accessToken }
});
```

#### Option 2: Backend Session Token with Real Auth

```python
# Replace the insecure endpoint with real authentication
@bp.route('/login', methods=['POST'])
def login():
    username = data.get('username')
    password = data.get('password')
    
    # ✅ VERIFY credentials against Auth0 or database
    user = verify_credentials(username, password)
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Only create session if credentials are valid
    session_data = session_manager.create_session(username, expires_hours=24)
    return jsonify(session_data), 200
```

---

## Code Changes Summary

### Files Modified

1. **`flask_app/auth/auth0.py`**
   - Added `ALLOW_INSECURE_SESSION_AUTH` flag
   - Added startup warning when insecure mode enabled

2. **`flask_app/sockets/audio_stream_auth0.py`**
   - Updated `authenticate_websocket()` function
   - Session fallback only when flag enabled
   - Added security logging

3. **`flask_app/api/auth.py`**
   - Deprecated all endpoints with security warnings
   - Block endpoints in production (403 response)
   - Added detailed security documentation

4. **`render.yaml`**
   - Added `ALLOW_INSECURE_SESSION_AUTH=false` for production
   - Documented security configuration

5. **`SECURITY.md`** (this file)
   - Complete security documentation
   - Migration guide
   - Testing instructions

---

## Compliance & Best Practices

### ✅ Security Checklist

- [x] Authentication required for all protected endpoints
- [x] Credentials verified before granting access
- [x] Insecure endpoints disabled by default in production
- [x] Clear security warnings in logs
- [x] Documentation for developers
- [x] Migration path for existing clients
- [x] Feature flag for development/testing

### 🔒 Security Recommendations

1. **Never enable `ALLOW_INSECURE_SESSION_AUTH` in production**
2. **Rotate Auth0 secrets regularly**
3. **Monitor authentication failures in production**
4. **Implement rate limiting on WebSocket connections**
5. **Add IP-based blocking for repeated auth failures**
6. **Regular security audits of authentication flow**

---

## Monitoring & Alerts

### Recommended Alerts

```yaml
# Datadog/CloudWatch/Prometheus alerts
alerts:
  - name: InsecureAuthEnabled
    condition: ALLOW_INSECURE_SESSION_AUTH == "true"
    severity: CRITICAL
    message: "Insecure session auth is enabled in production!"
    
  - name: DeprecatedEndpointUsed
    condition: log.message contains "deprecated /mobile-auth"
    severity: HIGH
    message: "Someone is trying to use deprecated mobile auth endpoint"
    
  - name: AuthFailureSpike
    condition: auth_failures > 100 per 5min
    severity: HIGH
    message: "Unusual number of authentication failures"
```

---

## Credits

**Identified by:** GitHub Copilot Code Review  
**Fixed by:** Development Team  
**Date:** December 5, 2025  
**Severity:** Critical (CVSS 9.8/10)  
**Status:** Resolved

---

## References

- [Auth0 Security Best Practices](https://auth0.com/docs/secure)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [SocketIO Authentication Guide](https://socket.io/docs/v4/middlewares/)

---

**This vulnerability has been resolved. No action required for deployments using default secure configuration.**
