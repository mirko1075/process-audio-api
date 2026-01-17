# Claude Project Instructions (Flask Transcription/Translation)

## Purpose
This repository is a production-oriented Python Flask backend for transcription/translation with REST APIs and Socket.IO streaming.

Your mission when working in this repo is to **increase reliability, security, and maintainability** without breaking existing behavior.

## Non‑Negotiable Rules (Hard)
1. **No breaking changes** unless explicitly approved.
2. **Default mode is read-only.** Do not edit files unless the user explicitly asks to apply changes.
3. Any functional change MUST update **all** of:
   - Source code
   - Documentation under `docs/`
   - OpenAPI spec (single source of truth for REST)
   - Postman collection (importable JSON)
   - Tests (new/updated) and confirmation they pass
4. If any of the above cannot be satisfied, **stop** and ask for a decision.

## Safety Gates
- Ask before deleting/renaming files.
- Ask before changing auth behavior or security posture.
- Ask before changing deployment/runtime assumptions.
- Ask before introducing new major dependencies.

## Ground Truth Notes
- `app.py` is an entrypoint.
- `core/` is a compatibility shim pointing to `flask_app/`.
- The true application factory is under `flask_app/` (create_app returns `(Flask app, SocketIO instance)`).

## Deliverable Standards
When you produce a change proposal, always include:
- **Impact summary** (what changes, what stays)
- **Risk assessment** (runtime risk, security risk)
- **Files to update** (code/docs/spec/tests)
- **Validation steps** (exact commands)

## Preferred Style
- Explicit, readable code over clever code.
- Small, reversible commits.
- Keep behavior identical unless explicitly requested.
