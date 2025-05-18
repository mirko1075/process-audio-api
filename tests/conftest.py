import os
import sys
import types

# Ensure src directory is on path for module imports.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, SRC_DIR)

# Set required environment variables for process_audio module import.
os.environ.setdefault("ASSEMBLYAI_API_KEY", "test")
os.environ.setdefault("DEEPGRAM_API_KEY", "test")
os.environ.setdefault("DEEPL_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
# Point to existing Google credentials file to satisfy FILE existence checks.
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(ROOT_DIR, "google", "google-credentials.json"),
)

# Stub oauth2client ServiceAccountCredentials to prevent real credential loading.
try:
    import oauth2client.service_account as _service_account_mod

    _service_account_mod.ServiceAccountCredentials.from_json_keyfile_name = (
        lambda filename, scope: None
    )
except ImportError:
    pass

# Stub gspread.authorize to no-op.
try:
    import gspread as _gspread_mod

    _gspread_mod.authorize = lambda creds: None
except ImportError:
    pass

# Stub google.cloud modules to prevent real network or credential use.
sys.modules.setdefault(
    "google.cloud.speech_v1p1beta1",
    types.SimpleNamespace(SpeechClient=lambda: None),
)
sys.modules.setdefault(
    "google.cloud.storage",
    types.SimpleNamespace(Client=lambda: types.SimpleNamespace(bucket=lambda name: None)),
)
sys.modules.setdefault(
    "google.cloud.translate_v2",
    types.SimpleNamespace(Client=lambda: types.SimpleNamespace(translate=lambda batch, target_language: [])),
)

# Stub FPDF to avoid font dependencies in PDFGenerator.
try:
    import fpdf as _fpdf_mod

    class _DummyFPDF:
        def __init__(self):
            pass

        def set_auto_page_break(self, auto, margin):
            pass

        def add_page(self):
            pass

        def add_font(self, *args, **kwargs):
            pass

        def set_font(self, *args, **kwargs):
            pass

        def cell(self, *args, **kwargs):
            pass

        def ln(self, *args, **kwargs):
            pass

        def output(self, filename):
            with open(filename, "wb"):
                pass

    _fpdf_mod.FPDF = _DummyFPDF
except ImportError:
    pass

# Stub transformers.pipeline and nltk.download to avoid external downloads in sentiment_analysis module.
try:
    import transformers as _trans_mod
    _trans_mod.pipeline = lambda *args, **kwargs: (lambda text: [{"label": "POSITIVE", "score": 1.0}])
except ImportError:
    pass
try:
    import nltk as _nltk_mod
    _nltk_mod.download = lambda *args, **kwargs: None
except ImportError:
    pass

# Override API key for require_api_key decorator.
try:
    import audio_api.application.auth as _auth_mod

    _auth_mod.API_KEY = "testkey"
except ImportError:
    pass

import pytest

@pytest.fixture(autouse=True)
def assert_no_requests(monkeypatch):
    """
    Prevent actual HTTP requests during tests by raising if requests.post is used unexpectedly.
    """
    import requests

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("HTTP request made")))
    yield

@pytest.fixture
def app():
    """
    Create Flask app for testing.
    """
    from audio_api.application.factory import create_app

    # Ensure app sees test API_KEY from auth override.
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()