import pandas as pd
import json
import io
from flask import request, jsonify, send_file
from openpyxl import Workbook

def process_sentiment_analysis_results(sentiment_results, queries_df):
    """
    Process the sentiment analysis results and queries to generate the output JSON structure.
    """
    sentiment_analysis = sentiment_results["sentiment_analysis"]

    # Map ratings to sentiment labels
    sentiment_map = {"5 stars": "POSITIVE", "3 stars": "NEUTRAL", "1 star": "NEGATIVE"}
    sentiment_results_processed = [
        [sentence, rating, sentiment_map.get(rating, "NEUTRAL")]
        for sentence, rating, confidence in sentiment_analysis
    ]

    # Process Queries
    query_results = []
    for _, row in queries_df.iterrows():
        scope, persona, query = row["Scope"], row["Persona"], row["Query"]
        related_sentences = [
            sentence_data
            for sentence_data in sentiment_analysis
            if query.lower() in sentence_data[0].lower()
        ]

        if related_sentences:
            response = " ".join(
                f"{sentence_data[0]} (Confidence: {sentence_data[2]:.2f})"
                for sentence_data in related_sentences
            )
            positive_count = sum(1 for _, rating, _ in related_sentences if rating == "5 stars")
            neutral_count = sum(1 for _, rating, _ in related_sentences if rating == "3 stars")
            negative_count = sum(1 for _, rating, _ in related_sentences if rating == "1 star")
        else:
            response = "NA"
            positive_count = neutral_count = negative_count = 0

        query_results.append([scope, persona, query, response, positive_count, negative_count, neutral_count])

    # Summarize Resumed Data
    resumed_data = [
        [
            sentiment_results["average_sentiment"],
            sentiment_results["average_confidence"],
            sum(1 for _, rating, _ in sentiment_analysis if rating == "5 stars"),
            sum(1 for _, rating, _ in sentiment_analysis if rating == "1 star"),
            sum(1 for _, rating, _ in sentiment_analysis if rating == "3 stars"),
        ]
    ]

    # Prepare Output JSON
    output_json = {
        "sheets": [
            {
                "name": "Queries",
                "data": [
                    ["Scope", "Persona", "Query", "Response", "Positive Sentences", "Negative Sentences", "Neutral Sentences"]
                ] + query_results,
            },
            {
                "name": "Sentiment Analysis Results",
                "data": [["Sentence", "Rating", "Sentiment Label"]] + sentiment_results_processed,
            },
            {
                "name": "Resumed Data",
                "data": [
                    ["General Sentiment", "Average Confidence", "Positive Sentences", "Negative Sentences", "Neutral Sentences"]
                ] + resumed_data,
            },
        ]
    }

    return output_json