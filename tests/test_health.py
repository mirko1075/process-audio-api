"""Basic smoke tests for the Flask application."""
from __future__ import annotations


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("API_KEY", "test")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    from api import create_app  # Import lazily so env vars are available

    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
