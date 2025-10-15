"""Sentiment analysis utilities using Hugging Face transformers."""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Tuple

import nltk
from nltk.tokenize import sent_tokenize
from transformers import pipeline


@lru_cache(maxsize=1)
def _get_pipeline():
    nltk.download("punkt", quiet=True)
    return pipeline(
        "sentiment-analysis",
        model="brettclaus/Hospital_Reviews",
        tokenizer="brettclaus/Hospital_Reviews",
    )


def run_sentiment_analysis(text: str) -> Dict[str, List[Tuple[str, str, float]]]:
    classifier = _get_pipeline()
    results: List[Tuple[str, str, float]] = []
    for sentence in sent_tokenize(text):
        output = classifier(sentence)[0]
        label = output["label"].upper()
        if label == "POSITIVE":
            rating = "5 stars"
        elif label == "NEGATIVE":
            rating = "1 star"
        else:
            rating = "3 stars"
        results.append((sentence, rating, output["score"] * 100))
    return {"sentiment_analysis": results}
