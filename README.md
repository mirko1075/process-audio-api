# AI Medical Transcription Backend

A production-ready Flask backend for transcribing, translating and analyzing medical conversations. The service integrates with multiple AI providers including Deepgram Nova-2, OpenAI Whisper/GPT, AssemblyAI, DeepSeek, and Google Cloud services.

## 🏗️ Architecture

This Flask application follows modern best practices with a modular architecture:

```
flask_app/
  __init__.py                 # Application factory
  api/                        # Flask blueprints (routes + business logic)
    health.py                 # Health check endpoints
    transcription.py          # Audio transcription services
    translation.py            # Text translation services  
    postprocessing.py         # Document generation & sentiment analysis
    utilities.py              # Utility functions (duration, logging, files)
  services/                   # Business logic orchestration
    transcription.py          # Transcription service coordination
    translation.py            # Translation service coordination
    postprocessing.py         # Document and analysis services
  clients/                    # External API integrations
    deepgram.py              # Deepgram Nova-2 client
    openai.py                # OpenAI Whisper/GPT client
    assemblyai.py            # AssemblyAI client
    google.py                # Google Cloud services client
    deepseek.py              # DeepSeek translation client
utils/                        # Shared utilities
  config.py                  # Configuration management
  auth.py                    # Authentication decorators
  logging.py                 # Logging setup
  exceptions.py              # Custom exceptions
app.py                        # Main application entry point
```

### 🎯 Design Principles

- **Flask Best Practices**: Application factory pattern with blueprints
- **Single Responsibility**: Each layer has a clear, focused purpose
- **Separation of Concerns**: API routes, business logic, and external clients are separated
- **Modularity**: Services can be easily extended or replaced
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

## 🚀 Getting Started

1. **Clone the repository and install dependencies:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run the development server:**

   ```bash
   python app.py
   ```

   The server will start on `http://localhost:5000`

4. **Health check:** The application is ready when `GET /health` returns 200.

## 📡 API Endpoints

### **🔍 Health & Status**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root welcome message |
| `GET` | `/health` | Health check & system status |

### **🎤 Transcription Services**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/transcriptions/deepgram` | Deepgram Nova-2 transcription with speaker diarization |
| `POST` | `/transcriptions/whisper` | OpenAI Whisper transcription (auto-chunking for large files) |
| `POST` | `/transcriptions/assemblyai` | AssemblyAI transcription with language detection |
| `POST` | `/transcriptions/transcribe-and-translate` | **Combined** transcription + translation in one call |

### **🌐 Translation Services**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/translations/openai` | OpenAI GPT-4 medical translation (with text chunking) |
| `POST` | `/translations/google` | Google Cloud Translation API |
| `POST` | `/translations/deepseek` | DeepSeek AI medical translation (specialized for Asian languages) |

### **📄 Document Generation**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/<format>` | Generate documents: `word`, `excel`, `pdf`, `text` |

### **📊 Analytics & Reporting**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sentiment` | Sentiment analysis using hospital reviews model |
| `POST` | `/reports/<format>` | Generate reports: `monthly`, `billing` |

### **🛠️ Utilities**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/utilities/audio-duration` | Get audio file duration in minutes |
| `POST` | `/utilities/log-usage` | Log usage for billing (Google Sheets integration) |
| `POST` | `/utilities/text-file` | Create downloadable text files |

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY` | ✅ | API key required in `x-api-key` header |
| `DEEPGRAM_API_KEY` | ✅ | Deepgram Nova-2 API key |
| `OPENAI_API_KEY` | ✅ | OpenAI API key for Whisper + GPT |
| `DEEPSEEK_API_KEY` | ⚠️ | DeepSeek API key (required for DeepSeek translation) |
| `ASSEMBLYAI_API_KEY` | ⚠️ | AssemblyAI API key (optional) |
| `GOOGLE_APPLICATION_CREDENTIALS` | ⚠️ | Google Cloud credentials JSON path |
| `ALLOWED_ORIGINS` | ⚠️ | CORS allowed origins (comma separated) |
| `LOG_LEVEL` | ⚠️ | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | ⚠️ | Logging format |

## 🚢 Deployment

### **Docker (Recommended)**
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t medical-transcription-api .
docker run -p 5000:5000 --env-file .env medical-transcription-api
```

### **Render.com Deployment** 🌐

Render è una piattaforma cloud moderna ideale per il deployment di API Flask con CI/CD automatico.

#### **1. Preparazione Repository**
```bash
# Assicurati che il tuo repository sia pushato su GitHub
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

#### **2. Configurazione su Render**

1. **Crea un nuovo Web Service** su [render.com](https://render.com)
2. **Connetti il repository GitHub**: `mirko1075/process-audio-api`
3. **Configura il servizio**:
   ```
   Name: medical-transcription-api
   Environment: Docker
   Branch: main
   Dockerfile Path: ./Dockerfile
   ```

#### **3. Variabili d'Ambiente**
Aggiungi tutte le seguenti environment variables nel dashboard Render:

```bash
# Core Configuration
FLASK_APP=app.py
FLASK_ENV=production
PORT=5000

# Authentication
API_KEY=your-secure-api-key-here

# AI Service API Keys (Ottieni dalle rispettive piattaforme)
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Google Cloud (Base64 del file credentials JSON)
GOOGLE_APPLICATION_CREDENTIALS_JSON=base64_encoded_json_here

# Optional Configuration
GOOGLE_CLOUD_PROJECT_ID=your_project_id
ALLOWED_ORIGINS=https://yourdomain.com,https://anotherdomain.com
LOG_LEVEL=INFO
```

#### **4. Configurazione Avanzata**
```bash
# Instance Type: Starter (512MB RAM) o Standard (2GB RAM)
# Auto-Deploy: Yes (per CI/CD automatico)
# Health Check Path: /health
```

#### **5. Build Commands**
Render utilizzerà automaticamente il `Dockerfile` presente nel repository:
```dockerfile
# Il Dockerfile gestisce automaticamente:
# - Installazione dipendenze da requirements.txt
# - Configurazione gunicorn ottimizzata per AI requests
# - Timeout di 15 minuti per richieste lunghe
# - 2 workers per gestire memoria e CPU intensive tasks
# - Esposizione porta dinamica
# - Health checks
```

**Start Command Consigliato (se non usi Docker):**
```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 900 --keep-alive 5 --max-requests 50 --preload
```

#### **6. Deploy e Verifica**
```bash
# URL del tuo servizio (esempio):
https://medical-transcription-api.onrender.com

# Test health check:
curl https://medical-transcription-api.onrender.com/health

# Test endpoint di esempio:
curl -X POST https://medical-transcription-api.onrender.com/transcriptions/deepgram \
  -H "x-api-key: your-api-key" \
  -F "audio=@test.mp3" \
  -F "language=en"
```

#### **7. Monitoraggio**
- **Logs**: Visualizza in tempo reale nel dashboard Render
- **Metrics**: CPU, Memory, Request count automatici
- **Alerts**: Configura notifiche per downtime
- **Auto-scaling**: Disponibile nei piani paid

#### **🔧 Troubleshooting Render**

**Errore 1: ModuleNotFoundError: No module named 'flask_cors'**

```bash
# Soluzione: Assicurati che Flask-CORS sia nel requirements.txt
Flask-CORS==5.0.0
```

**Errore 2: OpenAI API Timeout (Worker exiting, SystemExit: 1)**

```bash
# Problema: Gunicorn worker timeout durante traduzioni lunghe
# Soluzione: Usa il comando start ottimizzato:
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 900 --keep-alive 5 --max-requests 50 --preload

# Environment Variables da aggiungere:
WEB_CONCURRENCY=2  # Numero di worker (Render lo rileva automaticamente)
```

**Errore 3: Port binding issues**

```bash
# Soluzione: Render usa la variabile PORT dinamica
# Il Dockerfile è già configurato per usare $PORT
# Verifica che nel dashboard Render sia configurato:
# Environment: Docker
# Start Command: (lascia vuoto, usa il CMD del Dockerfile)
```

**Errore 4: Environment variables non trovate**

```bash
# Soluzione: Nel dashboard Render, verifica di aver aggiunto:
FLASK_APP=app.py
FLASK_ENV=production
API_KEY=your-api-key-here
DEEPGRAM_API_KEY=your-key
OPENAI_API_KEY=your-key
# ... altre variabili necessarie
```

**Errore 5: Build timeout o out of memory**

```bash
# Soluzione: Aggiungi .dockerignore per escludere file non necessari:
echo "__pycache__" >> .dockerignore
echo "*.pyc" >> .dockerignore
echo ".git" >> .dockerignore
echo "node_modules" >> .dockerignore
echo ".venv" >> .dockerignore
```

**Errore 6: Rate limiting OpenAI**

```bash
# Soluzione: Il client ora include retry automatico con backoff esponenziale
# Configurazione automatica:
# - 3 tentativi per richiesta
# - Delay esponenziale tra retry (4-10 secondi)
# - Delay 0.5s tra chunk per evitare rate limiting
```

### **Altre Piattaforme Cloud**
- **Railway**: Deploy simile a Render, GitHub integration
- **AWS ECS/Fargate**: Use the included Dockerfile
- **Google Cloud Run**: Auto-scaling container deployment
- **Heroku**: Git-based deployment con Procfile

### **Production Configuration**
- Uses `gunicorn` WSGI server with 4 workers
- Configured for dynamic port binding (Render/Heroku compatible)
- Health checks available at `/health`
- Comprehensive logging and error handling
- Docker multi-stage build per ottimizzazione

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=flask_app tests/
```

## 📚 API Documentation

- **OpenAPI Specification**: See `openapi.yaml` for complete API documentation
- **Postman Collection**: Import `postman_collection.json` for testing endpoints
- **Interactive Docs**: Swagger UI available when running locally

## 🔒 Security Features

- **API Key Authentication**: All endpoints require `x-api-key` header
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Sanitized error responses
- **CORS Protection**: Configurable allowed origins
- **File Size Limits**: Automatic chunking for large files

## 📈 Performance Features

- **Audio Chunking**: Large audio files automatically split for processing
- **Text Chunking**: Long texts split for optimal translation
- **Async Processing**: Non-blocking operations where possible
- **Caching**: Intelligent caching of API responses
- **Compression**: Automatic audio compression for large files

## 🌍 Language Support

- **Transcription**: 50+ languages via Deepgram/Whisper
- **Translation**: All major languages via OpenAI/Google/DeepSeek
- **Specialized**: Medical terminology optimization for Asian languages
- **Speaker Diarization**: Multi-speaker conversation support

## 🔧 Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
| `POST` | `/sentiment` | Medical sentiment analysis |
| `POST` | `/documents/word` | Generate DOCX transcripts |
| `POST` | `/reports/excel` | Build Excel summaries |

All endpoints require the `x-api-key` header.

## Logging & observability

Logging is centralised in `utils/logging.py`. Switch to JSON logs by setting
`LOG_FORMAT=json` for better integration with cloud logging platforms.

## Further improvements

- Add request tracing (e.g. OpenTelemetry) for distributed debugging.
- Implement background processing for long-running transcription jobs.
- Extend test coverage with mocked service clients.
