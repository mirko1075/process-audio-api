import pytest

import audio_api.domain.sentiment_analysis as sa


@pytest.mark.parametrize(
    "label,expected_rating",
    [
        ("POSITIVE", "5 stars"),
        ("NEGATIVE", "1 star"),
        ("NEUTRAL", "3 stars"),
    ],
)
def test_run_sentiment_analysis_rating(monkeypatch, label, expected_rating):
    # Stub sentiment_pipeline to return given label and fixed score
    monkeypatch.setattr(
        sa,
        "sentiment_pipeline",
        lambda text: [{"label": label, "score": 0.4}],
    )
    result = sa.run_sentiment_analysis("Some text.")
    entries = result.get("sentiment_analysis", [])
    assert entries and entries[0][1] == expected_rating


def test_run_sentiment_analysis_multiple_sentences(monkeypatch):
    # Stub sentiment_pipeline to always return positive
    monkeypatch.setattr(
        sa,
        "sentiment_pipeline",
        lambda text: [{"label": "POSITIVE", "score": 0.2}],
    )
    text = "First sentence. Second sentence!"
    result = sa.run_sentiment_analysis(text)
    assert isinstance(result, dict)
    assert len(result["sentiment_analysis"]) == 2