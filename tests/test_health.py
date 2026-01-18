"""Basic smoke tests for the Flask application."""
from __future__ import annotations


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("API_KEY", "test")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    from core import create_app  # Updated import path

    app, socketio = create_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    
    # Check the actual response format from the health endpoint
    response_data = response.get_json()
    assert response_data["status"] == "healthy"
    assert response_data["service"] == "Audio Transcription API"
    assert response_data["version"] == "1.0.0"
