import io
import json
import os
import subprocess
import tempfile
import types

import pandas as pd
import pytest

import audio_api.domain.process_audio as pa


def test_split_text_at_sentences():
    text = "Hello world. How are you? I'm fine!"
    sentences = pa.split_text_at_sentences(text)
    assert sentences == ["Hello world.", "How are you?", "I'm fine!"]


def test_split_text_into_chunks(monkeypatch):
    # Monkeypatch tokenizer to count one token per word
    class DummyEnc:
        def encode(self, line):
            return line.split()

    monkeypatch.setattr(
        pa.tiktoken, "encoding_for_model", lambda model: DummyEnc()
    )
    text = "one two three\nfour five six seven"
    chunks = pa.split_text_into_chunks(text, model="any", max_tokens=3)
    # Ensure no chunk exceeds max_tokens words
    for chunk in chunks:
        words = chunk.split()
        assert len(words) <= 3


def test_split_text_into_chunks_oriental_default():
    text = "Sentence one. Sentence two."
    chunks = pa.split_text_into_chunks_oriental(text, language_hint="en", max_tokens=100)
    # Text under limit should remain single chunk
    assert chunks == [text]


def test_get_audio_duration(monkeypatch):
    # Simulate successful ffprobe call
    class Result:
        returncode = 0
        stdout = "123.45\n"

    monkeypatch.setattr(
        pa.subprocess, "run", lambda *args, **kwargs: Result()
    )
    duration = pa.get_audio_duration("dummy")
    assert abs(duration - 123.45) < 1e-6

    # Simulate ffprobe failure
    class BadResult:
        returncode = 1
        stderr = "error"

    monkeypatch.setattr(
        pa.subprocess, "run", lambda *args, **kwargs: BadResult()
    )
    with pytest.raises(RuntimeError):
        pa.get_audio_duration("dummy")


def test_get_audio_duration_from_form_file(monkeypatch):
    # Successful ffprobe JSON output
    data = {"format": {"duration": "180"}}
    class Res:
        returncode = 0
        stdout = json.dumps(data)

    monkeypatch.setattr(
        pa.subprocess, "run", lambda *args, **kwargs: Res()
    )
    fake_file = io.BytesIO(b"dummy audio")
    minutes, error = pa.get_audio_duration_from_form_file(fake_file)
    assert minutes == pytest.approx(3.0)
    assert error is None

    # ffprobe returns error
    class ErrRes:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(
        pa.subprocess, "run", lambda *args, **kwargs: ErrRes()
    )
    minutes, error = pa.get_audio_duration_from_form_file(fake_file)
    assert minutes is None and "FFprobe failed" in error


def test_transcribe_audio_openai(monkeypatch, tmp_path):
    # Create dummy audio file
    file_path = tmp_path / "audio.wav"
    file_path.write_bytes(b"data")

    class DummyResp:
        text = "transcribed"

    monkeypatch.setattr(
        pa.openai.audio.transcriptions, "create", lambda **kwargs: DummyResp()
    )
    result = pa.transcribe_audio_openai(str(file_path), language="en")
    assert result == "transcribed"


def test_perform_sentiment_analysis(monkeypatch):
    # Stub pipeline to return fixed sentiment
    monkeypatch.setattr(
        pa, "pipeline", lambda *args, **kwargs: (lambda s: [{"label": "POSITIVE", "score": 0.5}])
    )
    res = pa.perform_sentiment_analysis(text="Hi there.")
    assert res["average_sentiment"] == "POSITIVE"
    assert res.get("positive_sentences", 0) >= 0


def test_transcribe_audio_with_google_diarization(monkeypatch):
    # Stub speech_client for test
    class DummyOp:
        def done(self):
            return True

        def result(self):
            # create dummy response with one result and one alternative
            alt = types.SimpleNamespace(transcript="hello world")
            res = types.SimpleNamespace(alternatives=[alt])
            return types.SimpleNamespace(results=[res])

    monkeypatch.setattr(pa, "speech_client", types.SimpleNamespace(long_running_recognize=lambda config, audio: DummyOp()))
    out = pa.transcribe_audio_with_google_diarization("gs://bucket/file.wav", language_code="en-US")
    assert "hello world" in out


def test_upload_and_delete_to_from_gcs(monkeypatch, tmp_path):
    # Stub storage_client
    calls = []

    class DummyBlob:
        def __init__(self, name):
            self.name = name

        def upload_from_filename(self, path):
            calls.append(("upload", path, self.name))

        def delete(self):
            calls.append(("delete", self.name))

    class DummyBucket:
        def __init__(self, bucket):
            self.bucket = bucket

        def blob(self, name):
            return DummyBlob(name)

    monkeypatch.setattr(pa, "storage_client", types.SimpleNamespace(bucket=lambda b: DummyBucket(b)))
    uri = pa.upload_to_gcs("/path/file.txt", "mybucket", "dest.txt")
    assert uri == "gs://mybucket/dest.txt"
    pa.delete_from_gcs("gs://mybucket/blob/dest.txt")
    assert any(c[0] == "delete" for c in calls)


def test_translate_text_google(monkeypatch):
    # Stub translate client
    class DummyTranslate:
        def translate(self, batch, target_language):
            return [{"translatedText": f"[{t}]"} for t in batch]

    monkeypatch.setattr(pa, "translate", types.SimpleNamespace(Client=lambda: DummyTranslate()))
    res = pa.translate_text_google(["a", "b"], "en")
    assert res["translated_texts"] == ["[a]", "[b]"]
    assert "[a]" in res["joined_translated_text"]


def test_format_transcript():
    # Build dummy response object
    class DummyWord:
        def __init__(self, speaker, punctuated_word):
            self.speaker = speaker
            self.punctuated_word = punctuated_word

    alt = types.SimpleNamespace(words=[DummyWord(1, "Hello"), DummyWord(1, "world."), DummyWord(2, "Test")])
    channel = types.SimpleNamespace(alternatives=[alt])
    resp = types.SimpleNamespace(results=types.SimpleNamespace(channels=[channel]))
    out = pa.format_transcript(resp)
    assert isinstance(out, dict)
    assert "Speaker 1:" in out["formatted_transcript_array"][0]


def test_load_and_process_queries_and_sentiment(tmp_path, monkeypatch):
    # Prepare Excel file with required columns
    df = pd.DataFrame({"Scope": ["s"], "Persona": ["p"], "Query": ["q1"]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    loaded = pa.load_excel_file(buf)
    assert list(loaded.columns)[:3] == ["Scope", "Persona", "Query"]

    # Stub OpenAI client for process_query
    monkeypatch.setattr(
        pa.client.chat.completions, "create", lambda **kwargs: types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="answer"))])
    )
    answer = pa.process_query("q1", "text")
    assert answer == "answer"
    responses = pa.process_queries(loaded, "text")
    assert responses == ["answer"]

    # Sentiment details and summary
    sentiment_results = {"sentiment_analysis": [("s1", "5 stars", 90)]}
    df_details = pa.create_sentiment_details_df(sentiment_results)
    assert "Sentence" in df_details.columns
    df_summary = pa.create_sentiment_summary_df(df_details)
    assert any(df_summary["Metric"] == "Total Sentences")

    # Excel generation
    out = pa.generate_multi_sheet_excel(df, df_details, df_summary)
    assert hasattr(out, "read")