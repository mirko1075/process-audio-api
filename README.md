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

**Requirements**: Python 3.10+ (recommended Python 3.11 or 3.12)

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
| `POST` | `/transcriptions/video` | **Video transcription** from URL (YouTube, etc.) or uploaded files with auto language detection |
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

Render is a modern cloud platform ideal for deploying Flask APIs with automatic CI/CD.

#### **1. Preparazione Repository**
```bash
# Make sure your repository is pushed to GitHub
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

#### **2. Render Configuration**

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
Add all the following environment variables in the Render dashboard:

```bash
# Core Configuration
FLASK_APP=app.py
FLASK_ENV=production
PORT=5000

# Authentication
# 🔐 Authentication System

This API supports **dual authentication modes** to accommodate both SaaS users and automated integrations:

## **Authentication Methods**

### **1. JWT Authentication (Recommended for SaaS)**
For web applications and user-facing interfaces:

```bash
# Register new user
curl -X POST https://your-api.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme Corp"
  }'

# Response includes JWT token and API key
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "api_key": "usr_123_AbCdEf...",
  "user": { ... }
}

# Use JWT for authenticated requests
curl -X POST https://your-api.com/transcriptions/deepgram \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -F "audio=@recording.wav"
```

### **2. API Key Authentication (For Integrations)**
For Make.com, Zapier, scripts, and automated workflows:

```bash
# Use API key in header
curl -X POST https://your-api.com/transcriptions/deepgram \
  -H "x-api-key: usr_123_AbCdEf123456..." \
  -F "audio=@recording.wav"
```

### **3. Legacy Support**
Existing integrations continue to work with the original static API key.

## **User Management**

### **Registration & Login**
```bash
# Register
POST /auth/register
{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe",
  "company": "Acme Corp",
  "plan": "pro"  // optional: free, pro, enterprise
}

# Login
POST /auth/login
{
  "email": "user@example.com", 
  "password": "password123"
}
```

### **API Key Management**
```bash
# Get profile and API keys
GET /auth/profile
Authorization: Bearer <jwt-token>

# Create new API key
POST /auth/api-keys
Authorization: Bearer <jwt-token>
{
  "name": "Make.com Integration"
}

# Deactivate API key
DELETE /auth/api-keys/{keyId}
Authorization: Bearer <jwt-token>
```

## **Database Setup**

### **Development (Docker)**
```bash
# Start PostgreSQL
docker compose up -d db

# Initialize database with admin user
python scripts/init_db.py

# Admin credentials:
# Email: admin@example.com
# Password: admin123
# API Key: usr_1_...
```

### **Production (Render/Railway)**
Set environment variables:
```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
JWT_SECRET_KEY=your-jwt-secret-key
SECRET_KEY=your-flask-secret-key
API_KEY=your-legacy-api-key  # for backward compatibility
```

## **User Plans & Limits**

| Plan | Monthly API Calls | Audio Hours | Price |
|------|-------------------|-------------|-------|
| **Free** | 100 | 2 hours | $0 |
| **Pro** | 10,000 | 50 hours | $29/month |
| **Enterprise** | Unlimited | Unlimited | Custom |

## **Security Features**

- 🔐 **Password Hashing**: bcrypt with salt
- 🎫 **JWT Tokens**: Secure user sessions  
- 🔑 **API Key Format**: `usr_{user_id}_{random_token}`
- 📊 **Usage Tracking**: Monitor API calls and audio processing
- 🚫 **Key Deactivation**: Instantly revoke access
- 🔄 **Backward Compatibility**: Legacy API keys continue working

# Authentication

API_KEY=your-secure-api-key-here

# AI Service API Keys (Obtain from respective platforms)
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
# Auto-Deploy: Yes (for automatic CI/CD)
# Health Check Path: /health
```

#### **5. Build Commands**
Render utilizzerà automaticamente il `Dockerfile` presente nel repository:
```dockerfile
# Il Dockerfile gestisce automaticamente:
# - Installazione dipendenze da requirements.txt
# - Configurazione gunicorn con 4 workers
# - Esposizione porta 5000
# - Health checks
```

#### **6. Deploy and Verification**
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

**Errore 2: Port binding issues**
```bash
# Soluzione: Render usa la variabile PORT dinamica
# Il Dockerfile è già configurato per usare $PORT
# Verifica che nel dashboard Render sia configurato:
# Environment: Docker
# Start Command: (lascia vuoto, usa il CMD del Dockerfile)
```

**Errore 3: Environment variables non trovate**
```bash
# Soluzione: Nel dashboard Render, verifica di aver aggiunto:
FLASK_APP=app.py
FLASK_ENV=production
API_KEY=your-api-key-here
DEEPGRAM_API_KEY=your-key
OPENAI_API_KEY=your-key
# ... altre variabili necessarie
```

**Errore 4: Build timeout o out of memory**
```bash
# Soluzione: Aggiungi .dockerignore per escludere file non necessari:
echo "__pycache__" >> .dockerignore
echo "*.pyc" >> .dockerignore
echo ".git" >> .dockerignore
echo "node_modules" >> .dockerignore
echo ".venv" >> .dockerignore
```

**Errore 5: Gunicorn workers crash**
```bash
# Soluzione: Il Dockerfile usa 4 workers, riduci a 2 per Starter plan
# Modifica nel Dockerfile: --workers 2
```

### **Other Cloud Platforms**
- **Railway**: Deploy simile a Render, GitHub integration
- **AWS ECS/Fargate**: Use the included Dockerfile
- **Google Cloud Run**: Auto-scaling container deployment
- **Heroku**: Git-based deployment with Procfile

### **Production Configuration**
- Uses `gunicorn` WSGI server with 4 workers
- Configured for dynamic port binding (Render/Heroku compatible)
- Health checks available at `/health`
- Comprehensive logging and error handling
- Docker multi-stage build for optimization

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

## � **Speaker Diarization with Deepgram**

### **What is Speaker Diarization?**

Speaker diarization automatically identifies and separates different speakers in an audio recording. This is essential for:

- **Meeting Transcriptions**: Identify who said what in conversations
- **Interview Analysis**: Separate interviewer from interviewee
- **Medical Consultations**: Distinguish between doctor and patient
- **Podcast Transcription**: Identify different hosts and guests

### **Diarization Features**

- **Automatic Speaker Detection**: Identifies the number of speakers present
- **Speaker Segments**: Provides transcript segments with speaker labels
- **Speaker Statistics**: Word count, speaking time, and confidence per speaker
- **Paragraph Detection**: Optional paragraph formatting for better readability
- **Advanced Punctuation**: Smart punctuation and formatting options

### **Diarization Usage Examples**

**Basic Transcription (without diarization):**

```bash
curl -X POST https://your-api.com/transcriptions/deepgram \
  -H "x-api-key: your-api-key" \
  -F "audio=@conversation.wav" \
  -F "language=en" \
  -F "model=nova-2"
```

**With Speaker Diarization:**

```bash
curl -X POST https://your-api.com/transcriptions/deepgram \
  -H "x-api-key: your-api-key" \
  -F "audio=@meeting.wav" \
  -F "language=en" \
  -F "model=nova-2" \
  -F "diarize=true" \
  -F "punctuate=true" \
  -F "paragraphs=false"
```

**With All Enhancement Options:**

```bash
curl -X POST https://your-api.com/transcriptions/deepgram \
  -H "x-api-key: your-api-key" \
  -F "audio=@interview.mp3" \
  -F "language=en" \
  -F "diarize=true" \
  -F "punctuate=true" \
  -F "paragraphs=true"
```

### **Diarization Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `audio` | File | Required | Audio file to transcribe |
| `language` | String | `en` | Language code (en, es, fr, de, it, etc.) |
| `model` | String | `nova-2` | Deepgram model to use |
| `diarize` | Boolean | `false` | Enable speaker diarization |
| `punctuate` | Boolean | `true` | Enable smart punctuation |
| `paragraphs` | Boolean | `false` | Enable paragraph detection |

### **Response Format with Diarization**

```json
{
  "transcript": "Hello, how are you doing today? I'm doing well, thank you for asking.",
  "confidence": 0.92,
  "language": "en",
  "model": "nova-2",
  "service": "deepgram",
  "word_count": 14,
  "duration_seconds": 8.5,
  "processing_info": {
    "service": "deepgram",
    "model_used": "nova-2",
    "language_requested": "en",
    "diarization_enabled": true,
    "paragraphs_enabled": false
  },
  "diarization": {
    "speakers_detected": 2,
    "total_duration": 8.5,
    "speakers": [
      {
        "speaker_id": "Speaker_0",
        "total_words": 8,
        "total_duration": 4.2,
        "average_confidence": 0.94,
        "speaking_percentage": 49.4
      },
      {
        "speaker_id": "Speaker_1",
        "total_words": 6,
        "total_duration": 4.3,
        "average_confidence": 0.90,
        "speaking_percentage": 50.6
      }
    ],
    "segments": [
      {
        "speaker": "Speaker_0",
        "speaker_id": 0,
        "text": "Hello, how are you doing today?",
        "start_time": 0.0,
        "end_time": 2.8,
        "duration": 2.8,
        "word_count": 6
      },
      {
        "speaker": "Speaker_1",
        "speaker_id": 1,
        "text": "I'm doing well, thank you for asking.",
        "start_time": 3.0,
        "end_time": 6.5,
        "duration": 3.5,
        "word_count": 8
      }
    ]
  }
}
```

### **Diarization Best Practices**

- **Audio Quality**: Clear audio with minimal background noise works best
- **Speaker Separation**: Works better when speakers don't overlap
- **File Formats**: Supports WAV, MP3, M4A, FLAC, OGG
- **Duration**: Works well for recordings from 30 seconds to several hours
- **Multiple Languages**: Specify the correct language for better accuracy

### **Diarization Use Cases**

- 📞 **Call Center Analysis**: Separate agent and customer conversations
- 🏥 **Medical Consultations**: Distinguish doctor-patient dialogue
- 📺 **Media Production**: Identify speakers in interviews and podcasts
- 💼 **Business Meetings**: Track who said what in team discussions
- 🎓 **Educational Content**: Separate teacher and student interactions

## �🎥 Video Transcription

The `/transcriptions/video` endpoint supports video transcription from multiple sources with automatic language detection:

### **Supported Video Sources**

- **YouTube URLs**: Automatic download and transcription
- **Direct Video URLs**: Any publicly accessible video URL
- **File Uploads**: MP4, AVI, MOV, MKV, and other common formats

### **Video Features**

- **Auto Language Detection**: Whisper automatically detects the spoken language
- **Multiple Model Sizes**: Choose from tiny, base, small, medium, large based on accuracy vs. speed needs
- **Video Metadata**: Extracts title, duration, uploader info for URL sources
- **Segment Timestamps**: Provides word-level timing information
- **Large File Support**: Handles long videos with automatic audio extraction

### **Video Usage Examples**

**YouTube Video Transcription:**

```bash
curl -X POST https://your-api.com/transcriptions/video \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=example",
    "language": "en",
    "model_size": "base"
  }'
```

**File Upload Transcription:**

```bash
curl -X POST https://your-api.com/transcriptions/video \
  -H "x-api-key: your-api-key" \
  -F "video=@your-video.mp4" \
  -F "model_size=small"
```

### **Model Size Guide**

- **tiny**: Fastest, least accurate (39 MB)
- **base**: Good balance (74 MB) - **Recommended**
- **small**: More accurate (244 MB)
- **medium**: High accuracy (769 MB)
- **large**: Maximum accuracy (1550 MB)

## 🔧 Troubleshooting

### **YouTube Video Download Issues (HTTP 403 Forbidden)**

If you encounter `HTTP Error 403: Forbidden` when transcribing YouTube videos:

**Common Causes:**
- YouTube's anti-bot measures blocking automated downloads
- Video has restricted access or geographic limitations
- yt-dlp needs updating to handle new YouTube protections
- Video requires login or is age-restricted

**Solutions:**

1. **Update yt-dlp** (most common fix):
   ```bash
   # Run the update script
   ./scripts/update_ytdlp.sh
   
   # Or manually update
   pip install --upgrade yt-dlp
   ```

2. **Try alternative approaches**:
   ```bash
   # Test different video URLs
   curl -X POST http://localhost:5000/transcriptions/video \
     -H "x-api-key: your-key" \
     -H "Content-Type: application/json" \
     -d '{"video_url": "https://www.youtube.com/watch?v=DIFFERENT_VIDEO_ID"}'
   
   # Upload video file directly instead
   curl -X POST http://localhost:5000/transcriptions/video \
     -H "x-api-key: your-key" \
     -F "video=@your-video.mp4"
   ```

3. **Check video accessibility**:
   - Ensure video is publicly accessible
   - Try the video URL in a browser
   - Check for geographic restrictions
   - Verify video doesn't require login

4. **Enhanced error handling**: The API now provides clearer error messages for different failure scenarios.

### **Database Connection Issues**

If you see `could not translate host name "db"`:

```bash
# For development, start PostgreSQL with Docker
docker-compose up -d db

# Or use SQLite for local testing
python scripts/init_providers_minimal.py
```

See `TROUBLESHOOTING.md` for more common issues and solutions.

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
