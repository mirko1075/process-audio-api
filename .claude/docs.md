# Documentation Policy

## Source of Truth
- All project documentation lives under `docs/`.
- Documentation must describe **current** behavior, not future plans.
- If something is unknown, mark it as **TO CONFIRM** and continue.

## Required Docs (baseline)
Maintain these files:
- `docs/architecture.md` — architecture, modules, data flows (REST + WebSocket)
- `docs/deployment_render.md` — how it runs on Render, env vars, runtime deps
- `docs/runbook.md` — debugging playbooks (transcription/translation/websocket)
- `docs/security-hardening-todo.md` — identified risks + actionable hardening items

## Update Triggers
Update docs when:
- Any endpoint changes (path/method/payload/response)
- Auth changes (JWT/Auth0/API keys/session fallback)
- WebSocket behavior changes
- Config/env changes
- Deployment or runtime changes
- Error semantics change (status codes, payloads)

## Output Format
- Markdown, concise, operational.
- Prefer tables for env vars and configuration.
- Include minimal code snippets only when necessary.

## Change Completion Checklist
A change is not complete until:
- Docs updated and internally consistent
- OpenAPI updated and validated
- Postman updated
- Tests updated and passing
