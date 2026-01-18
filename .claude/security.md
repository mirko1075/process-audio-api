# Security & Hardening Policy

## High-Risk Areas (treat as critical)
- Authentication & authorization (Auth0/JWT/API keys/session fallback)
- WebSocket origin policy and token verification
- Secrets management (API keys, JWT secrets, Auth0 secrets)
- CORS policy
- Debug mode in production

## Mandatory Hardening Checks
When reviewing or changing code, always evaluate:
1. **JWT expiry** (tokens must expire in production)
2. **Session-auth fallback** (must be disabled or fail-closed in production)
3. **CORS** (no wildcard origins in production unless explicitly approved)
4. **Socket.IO origins** (no `*` in production)
5. **Secrets** (no secrets in repo; env-only; rotation plan)
6. **Error leakage** (avoid returning internal exception details)
7. **Rate limiting / abuse** (identify where needed)

## Production Guard Rails
Prefer explicit runtime assertions:
- If `ENV=production` then:
  - Debug must be off
  - Insecure auth fallback must be off
  - CORS and WS origins must be restricted

## Reporting Format
For any security finding, provide:
- Severity: critical/high/medium/low
- Impact
- Exploit scenario (brief)
- Concrete remediation steps

## Change Policy
Security posture changes require explicit user approval.
