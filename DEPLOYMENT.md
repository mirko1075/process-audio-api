# 🚀 Deployment Guide - Render

Questa guida spiega come deployare l'API di trascrizione audio su Render.

## 📋 Prerequisiti

- Account Render (gratuito su [render.com](https://render.com))
- Repository GitHub collegato
- Database PostgreSQL (fornito da Render)

## 🔧 Configurazione Deployment

### 1. File di Configurazione

Il progetto include i seguenti file per il deployment:

- **`render.yaml`**: Configurazione Blueprint per Render
- **`Procfile`**: Comando di avvio per gunicorn
- **`requirements.txt`**: Include `eventlet` per supporto WebSocket in produzione

### 2. Variabili d'Ambiente Richieste

Configura le seguenti variabili d'ambiente nel dashboard di Render:

#### Obbligatorie
```
DATABASE_URL=<fornito-automaticamente-da-render>
JWT_SECRET_KEY=<generato-automaticamente>
```

#### API Keys (almeno una richiesta)
```
DEEPGRAM_API_KEY=<tua-chiave-deepgram>
OPENAI_API_KEY=<tua-chiave-openai>
ASSEMBLYAI_API_KEY=<tua-chiave-assemblyai>
DEEPSEEK_API_KEY=<tua-chiave-deepseek>
```

#### Google Cloud (opzionale)
```
GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/google-credentials.json
```

Per le credenziali Google, carica il file JSON come "Secret File" in Render.

### 3. Deploy su Render

#### Opzione A: Blueprint (Consigliato)
1. Nel dashboard Render, vai su **Blueprints**
2. Clicca **New Blueprint Instance**
3. Connetti il tuo repository GitHub
4. Render leggerà automaticamente `render.yaml`
5. Configura le variabili d'ambiente
6. Clicca **Apply**

#### Opzione B: Web Service Manuale
1. Nel dashboard Render, clicca **New +**
2. Seleziona **Web Service**
3. Connetti il repository GitHub
4. Configura:
   - **Name**: `audio-transcription-api`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
5. Aggiungi le variabili d'ambiente
6. Clicca **Create Web Service**

## 🔍 Verifica Deployment

### Health Check
Una volta deployato, verifica che il server sia online:
```bash
curl https://your-app.onrender.com/health
```

Risposta attesa:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-04T..."
}
```

### Endpoints Disponibili
- `GET /health` - Health check
- `POST /register` - Registrazione utente
- `POST /login` - Login utente
- `POST /transcribe` - Trascrizione audio
- `POST /translate` - Traduzione testo
- `POST /postprocess` - Post-processing
- `WebSocket /audio-stream` - Streaming audio real-time

## ⚙️ Configurazione Worker

### Worker Class: eventlet
Il progetto usa `eventlet` come worker class per supportare:
- ✅ WebSocket (Flask-SocketIO)
- ✅ Connessioni long-polling
- ✅ Richieste asincrone

**Importante**: Usa **1 solo worker** (`-w 1`) perché:
- Flask-SocketIO richiede sticky sessions
- Render free tier ha limitazioni di memoria
- Eventlet gestisce efficacemente connessioni multiple

## 📊 Monitoring

### Logs
Visualizza i logs in tempo reale:
```bash
# Dal dashboard Render, vai su Logs
# Oppure usa Render CLI
render logs -s <service-name>
```

### Metrics
Render fornisce metriche automatiche:
- CPU Usage
- Memory Usage
- Request Rate
- Response Time

## 🔄 Auto-Deploy

Il deployment automatico è configurato per:
- Push su branch `main` → deploy automatico
- Pull Request → build preview (se abilitato)

## 🗄️ Database Setup

### PostgreSQL su Render
1. Crea un **PostgreSQL** service su Render
2. Copia l'**Internal Database URL**
3. Aggiungi come variabile `DATABASE_URL`
4. Le migrazioni verranno eseguite automaticamente all'avvio

### Inizializzazione Database
Se necessario, esegui manualmente:
```bash
# Render Shell
python scripts/init_db.py
```

## 🧪 Test Locale con Gunicorn

Prima del deployment, testa localmente con gunicorn:

```bash
# Installa eventlet
pip install eventlet

# Avvia con gunicorn (simula produzione)
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app

# Test health check
curl http://localhost:5000/health
```

## 🐛 Troubleshooting

### Server non si avvia
- ✅ Verifica che tutte le variabili d'ambiente siano configurate
- ✅ Controlla i logs per errori di import o dipendenze
- ✅ Assicurati che `eventlet` sia in `requirements.txt`

### WebSocket non funzionano
- ✅ Verifica che gunicorn usi `--worker-class eventlet`
- ✅ Usa 1 solo worker (`-w 1`)
- ✅ Controlla che il client usi il protocollo corretto (ws/wss)

### Errori di memoria
- ✅ Riduci il numero di worker (usa `-w 1`)
- ✅ Limita la dimensione dei file di upload
- ✅ Considera un upgrade del piano Render

### Database connection error
- ✅ Verifica che `DATABASE_URL` sia configurato
- ✅ Controlla che il database Render sia nello stesso region
- ✅ Usa Internal Database URL (più veloce)

## 🔐 Sicurezza

### Best Practices
- ✅ Usa variabili d'ambiente per segreti (no hardcode)
- ✅ Abilita HTTPS (automatico su Render)
- ✅ Configura CORS appropriatamente
- ✅ Usa JWT con secret sicuro
- ✅ Valida e sanitizza input utente

### Secret Files
Per file sensibili (es. Google credentials):
1. Vai su **Environment** nel dashboard
2. Clicca **Add Secret File**
3. Path: `/etc/secrets/google-credentials.json`
4. Incolla il contenuto del file JSON

## 📱 Mobile App Integration

Il backend supporta l'app mobile Meeting Minute Streamer:
- Vedi `MOBILE_API_GUIDE.md` per dettagli API
- Vedi `README_MOBILE_BACKEND.md` per architettura

## 🔗 Link Utili

- [Render Documentation](https://render.com/docs)
- [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [Eventlet Documentation](https://eventlet.readthedocs.io/)

## 📞 Support

Per problemi o domande:
- Consulta `TROUBLESHOOTING.md`
- Verifica i logs su Render
- Controlla le issue su GitHub

---

**Note**: Render free tier ha limitazioni:
- CPU condivisa
- 512MB RAM
- Sleep dopo 15 min inattività (riavvio automatico)
- 750 ore/mese gratis

Per produzione seria, considera un piano a pagamento.
