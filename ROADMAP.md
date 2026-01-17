# Step 1 — Chiudere i buchi blocking SaaS (non tutto il security backlog)

Dal documento di hardening, NON serve fare tutto ora

security-hardening-todo

Serve fare solo ciò che blocca la monetizzazione.

🔴 DA FARE SUBITO (prima del pubblico)

JWT expiration + refresh

Per SaaS pubblico è obbligatorio

Eliminare definitivamente /mobile-auth/*

Anche solo lasciarlo “spento” è debito mentale

CORS WebSocket whitelist

Altrimenti non puoi aprire una web app pubblica

Rimuovere default secrets

SaaS pubblico + secret di fallback = no

⛔ Tutto il resto (rate limiting avanzato, CSP, key rotation annuale) può stare post-MVP.

# Step 2 — SaaS data model MINIMO (si incastra con ciò che hai)

Tu hai già metà billing senza rendertene conto.

Tabelle che hai già

users

api_keys

usage_logs

Tabelle da aggiungere (solo 2)
jobs

- id
- user_id
- type (transcription | translation | stream)
- status (queued | processing | done | failed)
- input_ref (s3 key / text hash)
- created_at
- completed_at

artifacts

- id
- job_id
- kind (transcript | translation | srt | json)
- storage_ref

❗ Nota importante:
NON duplicare dati. Il DB è solo indice + stato.
Il contenuto vive in object storage.

# Step 3 — Web app minimale (backend-first, davvero)

Qui serve essere spietati.

Stack consigliato (opinione forte)

Next.js

Auth0 SDK

Server Actions per upload

Zero stato client complesso

Schermate MVP (solo queste)

Login

Upload (audio/video/text)

Job list

Job detail (download risultato)

Fine.
Niente dashboard “bella”, niente analytics UI.

# Step 4 — API SaaS wrapper (non riscrivere nulla)

Non tocchi i servizi esistenti.

Aggiungi un sottile layer:

POST   /saas/jobs
GET    /saas/jobs
GET    /saas/jobs/:id
DELETE /saas/jobs/:id

Internamente:

validi quota

chiami gli endpoint che già esistono

registri usage (già fatto)

Questo è coerente con l’architettura che hai documentato

architecture

# Step 5 — Monetizzazione (semplice e sostenibile)
❌ Cattive idee

calcolo in tempo reale perfetto dei costi

piani complicati

billing custom

✅ Scelta giusta ora

Credits mensili

Stripe Checkout

Hard stop quando finiti

Hai già UsageLog.cost_usd.
Usalo come approximation, non come verità contabile.

# Step 6 — Cose da NON fare (te lo dico esplicitamente)

❌ Non implementare:

multi-workspace ora

team / RBAC

real-time collaboration

versioning dei transcript

marketplace di provider

❌ Non toccare:

eventlet

single worker

pipeline Deepgram / Whisper

Il tuo runbook mostra che sai operare il sistema così com’è

runbook

Non romperlo prima di avere utenti paganti.

Roadmap realistica (con i piedi per terra)
Week 1

Security blocking fixes

Tabelle jobs, artifacts

Object storage

Week 2

API SaaS wrapper

Job persistence

Auth0 → user_id propagation

Week 3

Next.js UI minimale

Upload + list + download

Stripe Checkout
