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
    try:
        # Ensure the data is a dictionary
        if isinstance(data, str):
            data = json.loads(data)

        # Validate workbook structure
        if "workbook" not in data or not isinstance(data["workbook"], list):
            raise ValueError("Invalid workbook structure in assistant response.")

        # Create a BytesIO object for the Excel file
        output = io.BytesIO()

        # Write workbook data to Excel
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet in data["workbook"]:
                sheet_name = sheet.get("name", "Sheet")
                sheet_data = sheet.get("data", [])

                # Convert sheet data to a DataFrame
                if sheet_data:
                    df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])  # Use the first row as headers
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Add Resume Sheet
            if "Resume" in data:
                resume_data = data["Resume"]
                resume_df = pd.DataFrame(resume_data[1:], columns=resume_data[0])
                resume_df.to_excel(writer, sheet_name="Resume", index=False)

        # Prepare the file for download
        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="sentiment_analysis.xlsx"
        )

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in generate_excel_from_data: {e}")
        return jsonify({"error": f"Failed to parse JSON data: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Error generating Excel: {e}")
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

    Generate a valid JSON object containing an Excel workbook structure. The JSON should have:
    - A "workbook" key with a list of sheets.
    - Each sheet should have:
      - A "name" key for the sheet name.
      - A "data" key with rows of data (each row as a list).
    Ensure the JSON is properly formatted and does not contain comments or incomplete data.
    Avoid using the prefix "```json" or "```" in the response.
    """
    try:
        # Call OpenAI API using the correct method
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI that generates Excel reports from sentiment analysis data and queries."},
                {"role": "user", "content": prompt}
            ]
        )
        assistant_response = response.choices[0].message.content

        # DEBUG: Log assistant response
        print(f"Assistant Response from OpenAI: {assistant_response}")

        if assistant_response.startswith("{"):
            return json.loads(assistant_response)  # Parse JSON response directly
        else:
            return {"error": "Assistant response was not JSON."}
        
    except Exception as e:
        logging.error(f"Error in query_assistant: {e}")
        return json.dumps({"error": str(e)})

def parse_assistant_response(response_text):
    """
    Parse the assistant's response to extract structured workbook data.
    """
    try:
        # DEBUG: Log raw response
        logging.debug(f"Parsing Assistant Response: {response_text}")

        # If the response is already a dictionary
        if isinstance(response_text, dict):
            return response_text

        # If the response is a string and starts with '{', parse as JSON
        if isinstance(response_text, str) and response_text.startswith("{"):
            parsed_json = json.loads(response_text)
            return parsed_json

        # Handle unexpected response format
        logging.error("Assistant response format is not recognized.")
        return {"error": "Assistant response was not JSON."}

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        return {"error": f"Failed to parse assistant response: {e}"}
    except Exception as e:
        logging.error(f"Error parsing assistant response: {e}")
        return {"error": f"Failed to parse assistant response: {str(e)}"}

def process_sentiment_data(sentiment_results, queries):
    """
    Process sentiment analysis data to generate summary, insights, and resume.
    """
    summary_data = []
    sentiment_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    total_confidence = 0
    total_segments = len(sentiment_results["results"]["sentiment_analysis"])

    # Process each segment in sentiment analysis
    for segment in sentiment_results["results"]["sentiment_analysis"]:
        text, stars, score = segment

        # Determine sentiment based on stars
        if "5 stars" in stars:
            sentiment = "Positive"
        elif "1 star" in stars:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        # Update sentiment counts
        sentiment_counts[sentiment] += 1

        # Update total confidence
        total_confidence += score

        # Extract start and end words
        words = text.split()
        start_word, end_word = words[0], words[-1]

        # Add to summary data
        summary_data.append([text, sentiment, stars, score, start_word, end_word])

    # Calculate averages
    average_confidence = total_confidence / total_segments if total_segments > 0 else 0

    # Prepare sentiment analysis results (overview)
    results_data = [
        ["Message", "Average Confidence", "Average Sentiment", "Negative Sentences", "Neutral Sentences", "Positive Sentences"],
        [
            sentiment_results["message"],
            round(average_confidence, 2),
            sentiment_results["results"]["average_sentiment"],
            sentiment_counts["Negative"],
            sentiment_counts["Neutral"],
            sentiment_counts["Positive"],
        ],
    ]

    # Prepare query insights (placeholders for now)
    insights_data = [["Query", "Average Sentiment Score", "Positive %", "Neutral %", "Negative %"]]
    insights_data += [["NA", "NA", "NA", "NA", "NA"] for _ in queries]

    # Prepare resume sheet data
    resume_data = [
        ["Metric", "Value"],
        ["Average Sentiment", sentiment_results["results"]["average_sentiment"]],
        ["Confidence in Average Sentiment", f"{round(average_confidence, 2)}%"],
        ["Total Positive Chunks", sentiment_counts["Positive"]],
        ["Total Neutral Chunks", sentiment_counts["Neutral"]],
        ["Total Negative Chunks", sentiment_counts["Negative"]],
    ]

    return {
        "Sentiment Analysis Summary": summary_data,
        "Sentiment Analysis Results": results_data,
        "Query Insights": insights_data,
        "Resume": resume_data,
    }
