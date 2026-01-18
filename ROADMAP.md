# SaaS Plan — Backend-first, lean, senza riscritture

Questo piano parte dallo stato attuale del progetto:
- backend Flask già in produzione
- Auth0
- Postgres già usato
- MCP discovery + docs completati
- Step 1 e Step 2 già fatti

Obiettivo: arrivare a un SaaS pagante senza rompere nulla.

---

## Step 1 — Chiudere i buchi *blocking* SaaS  
✅ GIÀ FATTO

Dal documento `security-hardening-todo.md` si è fatto **solo ciò che blocca la monetizzazione**.

### Fatto
- JWT expiration + refresh
- Eliminazione definitiva `/mobile-auth/*`
- WebSocket CORS whitelist
- Rimozione default / fallback secrets

### Rimandato post-MVP
- rate limiting avanzato
- CSP
- key rotation periodica
- audit logging esteso

---

## Step 2 — SaaS data model MINIMO  
✅ GIÀ FATTO

Il sistema aveva già metà del billing senza accorgersene.

### Tabelle esistenti
- users
- api_keys
- usage_logs

### Tabelle aggiunte
**jobs**
- id
- user_id
- type (transcription | translation | stream)
- status (queued | processing | done | failed)
- input_ref (storage path o text hash)
- created_at
- completed_at

**artifacts**
- id
- job_id
- kind (transcript | translation | srt | json)
- storage_ref (path nel bucket)

❗ Regola chiave  
Il DB contiene **solo stato e indici**.  
I contenuti binari vivono **sempre** in object storage.

---

## Step 3 — Object Storage (Supabase Buckets)  
▶️ PROSSIMO STEP

### Scelte architetturali
- Storage: **Supabase Storage**
- Bucket: **private**
- Auth: **solo backend Python**
- Supabase Auth: **NON usato**

### Naming strategy (ownership by path)
users/{user_id}/jobs/{job_id}/input/original.wav
users/{user_id}/jobs/{job_id}/output/transcript.txt
users/{user_id}/jobs/{job_id}/output/translation.json   

### Flusso
- upload input → salvato su bucket
- `jobs.input_ref` = path
- output generati → salvati su bucket
- `artifacts.storage_ref` = path

### Download
- preferenza: **signed URL a TTL breve**
- alternativa: stream-through backend

---

## Step 4 — API SaaS wrapper (NON riscrivere nulla)  
▶️ DOPO Step 3

Aggiunta di un sottile layer `/saas/*` sopra i servizi esistenti.

### Endpoint
POST /saas/jobs
GET /saas/jobs
GET /saas/jobs/{id}
DELETE /saas/jobs/{id}


### Responsabilità del wrapper
- validazione ownership (`user_id`)
- validazione quota / credits (quando introdotti)
- chiamata agli endpoint tecnici esistenti
- persistenza job + artifacts
- registrazione usage (già presente)

❗ I servizi core NON sanno di essere in un SaaS.

---

## Step 5 — Web app minimale (MVP reale)  
▶️ DOPO Step 4

Web app separata dal backend.

### Stack
- Next.js
- Auth0 SDK
- chiamate solo alle API `/saas/*`

### Schermate (solo queste)
1. Login
2. Upload (audio / video / testo)
3. Job list
4. Job detail + download artifacts

Niente dashboard avanzate.
Niente analytics UI.
Niente feature extra.

---

## Step 6 — Monetizzazione semplice e sostenibile

### Cattive idee (NO)
- calcolo costi perfetto in tempo reale
- piani complessi
- billing custom

### Scelta giusta ora
- credits mensili
- Stripe Checkout
- hard stop quando i credits finiscono

`usage_logs.cost_usd` = stima operativa, non contabilità.

---

## Step 7 — Cose da NON fare (esplicitamente)

❌ Non implementare ora:
- multi-workspace
- team / RBAC
- collaboration real-time
- versioning transcript
- marketplace provider

❌ Non toccare:
- eventlet
- single worker
- pipeline Deepgram / Whisper
- architettura attuale del backend

Il runbook dimostra che il sistema è operabile così com’è.
Non romperlo prima di avere utenti paganti.

---

## Roadmap realistica

### Week 1
- Step 3: Supabase Storage
- artifacts completi

### Week 2
- Step 4: API SaaS wrapper
- job lifecycle completo
- ownership enforcement

### Week 3
- Step 5: Web app MVP
- upload / list / download
- Stripe Checkout
