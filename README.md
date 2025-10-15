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

### **Production Platforms**
- **Render/Railway**: Deploy directly from GitHub
- **AWS ECS/Fargate**: Use the included Dockerfile
- **Google Cloud Run**: Auto-scaling container deployment
- **Heroku**: Git-based deployment

### **Production Configuration**
- Uses `gunicorn` WSGI server
- Configured for port 5000 by default
- Health checks available at `/health`
- Comprehensive logging and error handling

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
