import json
import logging
import pandas as pd
import io
from flask import send_file, jsonify
from openai import OpenAI

client = OpenAI()


# Allowed file extensions for Excel
ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_excel_from_data(data):
    """
    Generate an Excel file from structured data returned by OpenAI.
    """
    try:
        # Ensure the data is a dictionary
        if isinstance(data, str):
            data = json.loads(data)

        # Extract data from the structured dictionary
        summary_data = data.get("SentimentAnalysisSummary", [])
        insights_data = data.get("QueryInsights", [])

        # Create Pandas DataFrames
        summary_df = pd.DataFrame(summary_data)
        insights_df = pd.DataFrame(insights_data)

        # Write to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Sentiment Analysis Summary", index=False)
            insights_df.to_excel(writer, sheet_name="Query Insights", index=False)

        output.seek(0)

        # Return the Excel file
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="sentiment_analysis.xlsx"
        )

    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel: {str(e)}"}), 500

def query_assistant(queries_file, sentiment_data):
    # Load Excel and JSON data
    queries_df = pd.read_excel(queries_file, sheet_name="Queries")
    queries_text = queries_df.to_string(index=False)
    sentiment_json_text = json.dumps(sentiment_data, indent=4)

    # Prepare OpenAI assistant prompt
    prompt = f"""
    Based on the following inputs:

    **Queries (Excel, Sheet: Queries)**:
    {queries_text}

    **Sentiment Analysis Results (JSON)**:
    {sentiment_json_text}

    Generate an Excel file with two sheets:
    1. Sentiment Analysis Summary:
        - Columns: Segment Text, Sentiment, Stars, Sentiment Score, Start Word, End Word.
    2. Query Insights:
        - Columns: Query, Average Sentiment Score, Positive %, Neutral %, Negative %.
    If generating an Excel file is not possible, return the structured data so the backend can create the Excel.
    """

    try:
        # Call OpenAI API using the new method
        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI that generates Excel reports from sentiment analysis data and queries."},
            {"role": "user", "content": prompt}
        ])
        assistant_response = response.choices[0].message.content

        # DEBUG: Log assistant response
        print(f"Assistant Response from OpenAI: {assistant_response}")

        return assistant_response
    except Exception as e:
        logging.error(f"Error in query_assistant: {e}")
        return json.dumps({"error": str(e)})



    except Exception as e:
        return {"error": str(e)}

