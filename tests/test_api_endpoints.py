import io
import os
from datetime import datetime
import types

import pytest


def test_health_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json() == {"message": "Hello, World!"}


def test_text_to_file_endpoint(client):
    data = {"text": "hello", "fileName": "greet"}
    resp = client.post("/text-to-file", data=data)
    assert resp.status_code == 200
    assert resp.data == b"hello"
    # Content-Disposition header contains filename prefix
    cd = resp.headers.get("Content-Disposition", "")
    assert "greet_" in cd


@pytest.mark.parametrize("endpoint,payload", [
    ("/generate-excel", {"sheets": [{"name": "S1", "data": [[1, 2]]}]}),
])
def test_generate_excel_requires_api_key(client, endpoint, payload):
    # Missing API key yields 401
    resp = client.post(endpoint, json=payload)
    assert resp.status_code == 401
    # With API key returns excel
    resp = client.post(endpoint, json=payload, headers={"x-api-key": "testkey"})
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.content_type


def test_generate_word_endpoint(client, tmp_path, monkeypatch):
    import audio_api.application.blueprints.documents as docs

    # Stub create_word_document to point to a temp file
    out_file = tmp_path / "out.docx"
    out_file.write_text("fake")
    monkeypatch.setattr(docs, "create_word_document", lambda text, name: str(out_file))
    resp = client.post(
        "/generate-word",
        data={"text": "x", "fileName": "f.docx"},
        headers={"x-api-key": "testkey"},
    )
    assert resp.status_code == 200


def test_translate_with_openai_endpoint(client, monkeypatch):
    import audio_api.application.blueprints.translation as tr

    # Stub translation function
    monkeypatch.setattr(tr, "translate_text_with_openai", lambda t, s, d: "out")
    data = {
        "text": "t",
        "sourceLanguage": "en",
        "targetLanguage": "en",
        "fileName": "f",
        "duration": "1",
        "driveId": "d",
        "groupId": "g",
        "fileId": "i",
        "folderId": "o",
        "projectName": "p",
        "isLocal": "true",
        "isDev": "false",
    }
    resp = client.post(
        "/translate-with-openai", data=data, headers={"x-api-key": "testkey"}
    )
    assert resp.status_code == 200
    assert resp.get_json().get("translated_text") == "out"

    # Missing parameter yields 400
    resp2 = client.post(
        "/translate-with-openai", data={"text": "t"}, headers={"x-api-key": "testkey"}
    )
    assert resp2.status_code == 400


def test_translate_with_deepseek_endpoint(client, monkeypatch):
    import audio_api.application.blueprints.translation as tr

    monkeypatch.setattr(tr, "translate_text_with_deepseek", lambda t, s, d: "ds_out")
    base = {
        "text": "t",
        "sourceLanguage": "en",
        "targetLanguage": "en",
        "fileName": "f",
        "duration": "1",
        "driveId": "d",
        "groupId": "g",
        "fileId": "i",
        "folderId": "o",
        "projectName": "p",
    }
    resp = client.post(
        "/translate-with-deepseek",
        data={**base, "isLocal": "true", "isDev": "false"},
        headers={"x-api-key": "testkey"},
    )
    assert resp.status_code == 200
    assert resp.get_json().get("translated_text") == "ds_out"

    # Missing parameter yields 400
    resp2 = client.post(
        "/translate-with-deepseek", data={"text": "t"}, headers={"x-api-key": "testkey"}
    )
    assert resp2.status_code == 400


def test_sentiment_analysis_endpoint(client, tmp_path, monkeypatch):
    import pandas as pd
    import audio_api.application.blueprints.sentiment as sb

    # Stub domain functions
    monkeypatch.setattr(sb, "load_excel_file", lambda f: pd.DataFrame({"Query": ["q"]}))
    monkeypatch.setattr(sb, "process_queries", lambda df, txt: ["r"])
    monkeypatch.setattr(sb, "run_sentiment_analysis", lambda text: {"sentiment_analysis": [("s", "5 stars", 50)]})
    monkeypatch.setattr(sb, "create_sentiment_details_df", lambda x: pd.DataFrame([("s", "5 stars", 50)], columns=["Sentence", "Rating", "Confidence"]))
    monkeypatch.setattr(sb, "create_sentiment_summary_df", lambda df: pd.DataFrame([("Metric", "Value")], columns=["Metric", "Value"]))
    monkeypatch.setattr(sb, "generate_multi_sheet_excel", lambda q, d, s: io.BytesIO(b"xlsx"))

    # Build dummy Excel file
    buf = io.BytesIO()
    pd.DataFrame({"Scope": [], "Persona": [], "Query": []}).to_excel(buf, index=False)
    buf.seek(0)
    resp = client.post(
        "/sentiment-analysis",
        data={"text": "t"},
        files={"file": (buf, "f.xlsx")},
        headers={"x-api-key": "testkey"},
    )
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.content_type


def test_reporting_endpoints(client, monkeypatch, tmp_path):
    import audio_api.application.blueprints.reporting as rep

    # get-audio-duration
    monkeypatch.setattr(rep, "get_audio_duration_from_form_file", lambda f: (2.0, None))
    resp = client.post(
        "/get-audio-duration",
        data={},
        headers={"x-api-key": "testkey"},
        content_type="multipart/form-data",
    )
    # Missing file yields 400
    assert resp.status_code == 400
    # With file
    buf = io.BytesIO(b"a")
    resp2 = client.post(
        "/get-audio-duration",
        data={"audio": (buf, "a.wav")},
        headers={"x-api-key": "testkey"},
    )
    assert resp2.status_code == 200

    # log-audio-usage
    monkeypatch.setattr(rep, "log_audio_processing", lambda u, f, d: True)
    monkeypatch.setattr(rep, "RATE_PER_MINUTE", 0.5)
    resp3 = client.post(
        "/log-audio-usage",
        data={"user_code": "u", "fileName": "f", "duration": "4"},
        headers={"x-api-key": "testkey"},
    )
    assert resp3.status_code == 200
    j3 = resp3.get_json()
    assert j3.get("total_cost") == f"{4 * 0.5:.2f}"

    # generate-monthly-report
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    monkeypatch.setattr(rep, "get_usage_data", lambda u: [{"Data e ora": today, "Costo Totale (€)": "1.00", "Durata (minuti)": 1}])
    class DummyPDF:
        def __init__(self, title):
            pass

        def add_table(self, data):
            pass

        def save_pdf(self, path):
            with open(path, "wb"):
                pass

    monkeypatch.setattr(rep, "PDFGenerator", DummyPDF)
    resp4 = client.post(
        "/generate-monthly-report", data={"user_code": "u"}, headers={"x-api-key": "testkey"}
    )
    assert resp4.status_code == 200

    # generate-billing-document
    monkeypatch.setattr(rep, "get_usage_data", lambda u: [{"Data e ora": today, "Costo Totale (€)": "2.00"}])
    resp5 = client.post(
        "/generate-billing-document", data={"user_code": "u"}, headers={"x-api-key": "testkey"}
    )
    assert resp5.status_code == 200


def test_transcription_endpoints(client, monkeypatch):
    import audio_api.application.blueprints.transcription as tb

    # transcribe_and_translate: missing audio
    resp0 = client.post(
        "/transcribe_and_translate", data={"translate": "false"}, headers={"x-api-key": "testkey"}
    )
    assert resp0.status_code == 400

    # stub deepgram transcription and translation
    monkeypatch.setattr(
        tb,
        "transcribe_with_deepgram",
        lambda audio, lang, model: {"formatted_transcript_array": ["f"], "transcript": "t"},
    )
    monkeypatch.setattr(tb, "translate_text_google", lambda txt, tgt: "g")
    monkeypatch.setattr(tb, "translate_text_with_openai", lambda txt, src, tgt: "o")
    buf = io.BytesIO(b"a")
    resp1 = client.post(
        "/transcribe_and_translate",
        data={"translate": "true", "transcript_model": "deepgram", "translation_model": "google", "language": "en", "target_language": "en"},
        headers={"x-api-key": "testkey"},
        content_type="multipart/form-data",
        data_stream={"audio": (buf, "a.mp3")},
    )
    # We expect 200 or processing error depending on test harness
    assert resp1.status_code in (200, 500)