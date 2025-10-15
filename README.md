# AI Medical Transcription Backend

A production-ready Flask backend for transcribing, translating and analysing
medical conversations. The service integrates with Deepgram Nova-2 for
transcription, OpenAI GPT models for translation, and optional AssemblyAI /
Google Cloud services.

## Project structure

```
api/
  controllers/
  routes/
core/
  transcription/
  translation/
  postprocessing/
utils/
tests/
app.py
```

Each layer has a single responsibility:

- **core/** contains service clients and reusable business logic.
- **api/controllers/** orchestrate requests by combining core services.
- **api/routes/** expose HTTP endpoints using Flask blueprints.
- **utils/** provides configuration, logging and auth helpers.

## Getting started

1. Clone the repository and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and populate the required API keys:

   ```bash
   cp .env.example .env
   ```

3. Run the development server:

   ```bash
   flask --app app run --debug
   ```

4. The health check is available at `GET /health`.

## Environment variables

| Variable | Description |
| --- | --- |
| `API_KEY` | API key required in the `x-api-key` header |
| `DEEPGRAM_API_KEY` | Deepgram Nova-2 key |
| `OPENAI_API_KEY` | OpenAI API key for Whisper + GPT |
| `ASSEMBLYAI_API_KEY` | Optional AssemblyAI support |
| `GOOGLE_APPLICATION_CREDENTIALS` | Optional Google Cloud JSON path |
| `ALLOWED_ORIGINS` | Comma separated list for CORS |
| `LOG_LEVEL` / `LOG_FORMAT` | Logging configuration |

## Deployment

A `Dockerfile` and `docker-compose.yml` are included for containerised
deployments. On Render or AWS ECS, build the image and supply the environment
variables listed above. The default command runs `gunicorn` bound to port 5000.

## Testing

Run unit tests with:

```bash
pytest
```

## Key endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe |
| `POST` | `/transcriptions/deepgram` | Deepgram Nova-2 transcription |
| `POST` | `/transcriptions/whisper` | OpenAI Whisper transcription |
| `POST` | `/translations/openai` | GPT-based translation |
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
