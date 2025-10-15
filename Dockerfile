FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    WEB_CONCURRENCY=2

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE $PORT

# Optimized gunicorn configuration for long-running AI requests
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers $WEB_CONCURRENCY --timeout 900 --keep-alive 5 --max-requests 50 --preload --worker-class sync app:app"]
