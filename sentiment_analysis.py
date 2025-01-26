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

                # Validate sheet data
                if not sheet_data:
                    logging.warning(f"Sheet '{sheet_name}' is empty. Skipping.")
                    continue

                headers = sheet_data[0]  # First row as headers
                rows = sheet_data[1:]  # Remaining rows as data

                # Validate row lengths
                for row in rows:
                    if len(row) != len(headers):
                        logging.error(f"Row length mismatch in sheet '{sheet_name}': {row} (Expected {len(headers)} columns)")
                        raise ValueError(f"Row length mismatch in sheet '{sheet_name}'.")

                # Convert sheet data to a DataFrame
                df = pd.DataFrame(rows, columns=headers)
                df.to_excel(writer, sheet_name=sheet_name, index=False)

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
    except ValueError as e:
        logging.error(f"Data validation error: {e}")
        return jsonify({"error": f"Data validation error: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Error generating Excel: {e}")
        return jsonify({"error": f"Failed to generate Excel: {str(e)}"}), 500


def query_assistant(queries_file, sentiment_data):
    # Load Excel and JSON data
    queries_df = pd.read_excel(queries_file, sheet_name="Queries")
    queries_text = queries_df.to_string(index=False)
    sentiment_json_text = json.dumps(sentiment_data, indent=4)
    
    # Debugging: Log the constructed texts
    print(f"SENTIMENT JSON TEXT: {sentiment_json_text}")
    print(f"QUERIES TEXT: {queries_text}")

    # Prepare OpenAI assistant prompt
    prompt = f"""
        You are tasked with processing sentiment analysis results and queries to generate a structured dataset for creating an Excel workbook. Based on the following inputs:

        **Queries:**
        {queries_text}

        **Sentiment Analysis Results (JSON):**
        {sentiment_json_text}

        Your task is to calculate and structure the data into the following sheets:

        1. **Sheet: Queries**
            - Columns: Scope, Persona, Query, Average Sentiment, Positive Sentences, Negative Sentences, Neutral Sentences.
            - For each query:
                - **Average Sentiment**: The average confidence score of all sentences related to this query.
                - **Positive Sentences**: Count of sentences rated as "5 stars" related to this query.
                - **Negative Sentences**: Count of sentences rated as "1 star" related to this query.
                - **Neutral Sentences**: Count of sentences rated as "3 stars" related to this query.
                - If no sentences are related to a query, all columns (Average Sentiment, Positive, Neutral, Negative) should display "NA".

        2. **Sheet: Sentiment Analysis Results**
            - Columns: Sentence, Rating, Confidence.
            - Include all sentences from the sentiment analysis results.

        3. **Sheet: Sentiment Resume**
            - Columns: General Sentiment, Average Confidence, Positive Sentences, Neutral Sentences, Negative Sentences.
            - Include a single row summarizing:
                - **General Sentiment**: Overall sentiment based on average confidence.
                - **Average Confidence**: The average of all confidence scores.
                - **Positive Sentences**: Total count of positive sentences across all queries.
                - **Neutral Sentences**: Total count of neutral sentences across all queries.
                - **Negative Sentences**: Total count of negative sentences across all queries.

        Your output must be a valid JSON object structured as follows:
        {
        "workbook": [
            {
            "name": "Queries",
            "data": [
                ["Scope", "Persona", "Query", "Average Sentiment", "Positive Sentences", "Negative Sentences", "Neutral Sentences"],
                ["drug", "Patient", "propensity to use this drug", "average_sentiment_value", "positive_count", "negative_count", "neutral_count"],
                ...
            ]
            },
            {
            "name": "Sentiment Analysis Results",
            "data": [
                ["Sentence", "Rating", "Confidence"],
                ["Example sentence 1", "5 stars", 98.2],
                ...
            ]
            },
            {
            "name": "Sentiment Resume",
            "data": [
                ["General Sentiment", "Average Confidence", "Positive Sentences", "Neutral Sentences", "Negative Sentences"],
                ["general_sentiment_value", "average_confidence_value", "positive_count", "neutral_count", "negative_count"]
            ]
            }
        ]
        }
        Do not include any text or comments outside the JSON object. The JSON must be complete and ready for processing.
        Never use the prefix "```json" or "```" in the response.
    """
    
    # Debugging: Log the final prompt
    print(f"FINAL PROMPT: {prompt}")

    try:
        # Call OpenAI API using the correct method
        response = client.chat.completions.create(
            model="gpt-4",
            temperature=0.0,
            messages=[
                {"role": "system", "content": "You are an AI that generates Excel reports from sentiment analysis data and queries."},
                {"role": "user", "content": prompt}
            ]
        )
        assistant_response = response.choices[0].message.content
        print(f"ASSISTANT RESPONSE: {assistant_response}")

        if assistant_response.startswith("{"):
            return json.loads(assistant_response)  # Parse JSON response directly
        else:
            return {"error": "Assistant response was not JSON."}
        
    except Exception as e:
        logging.error(f"Error in query_assistant: {e}")
        return json.dumps({"error": str(e)})

def parse_assistant_response(response_text, queries):
    """
    Parse the assistant's response to extract structured workbook data
    and add query insights based on sentiment analysis.
    """
    try:
        # Parse the response into a dictionary
        if isinstance(response_text, dict):
            data = response_text
        elif isinstance(response_text, str) and response_text.startswith("{"):
            data = json.loads(response_text)
        else:
            logging.error("Assistant response format is not recognized.")
            return {"error": "Assistant response was not JSON."}

        # Extract Sentiment Analysis Results
        sentiment_data = data.get("workbook", [])
        sentiment_sheet = next((sheet for sheet in sentiment_data if sheet["name"] == "Sentiment Analysis Results"), None)
        if not sentiment_sheet or "data" not in sentiment_sheet:
            raise ValueError("Sentiment Analysis Results sheet missing or invalid.")

        sentiment_rows = sentiment_sheet["data"]

        # Separate Summary rows and Detail rows
        summary_rows = [row for row in sentiment_rows if isinstance(row[0], str) and row[0].startswith("Sentiment analysis complete.")]
        detail_rows = [row for row in sentiment_rows if not (isinstance(row[0], str) and row[0].startswith("Sentiment analysis complete."))]

        # DEBUG: Log summary and detail rows
        logging.debug(f"Summary Rows: {summary_rows}")
        logging.debug(f"Detail Rows: {detail_rows}")

        # Check if there are any summary rows
        if not summary_rows:
            logging.warning("No summary rows found in Sentiment Analysis Results.")
        else:
            logging.info(f"Found {len(summary_rows)} summary rows.")

        # Create a new Sentiment Resume sheet
        resume_sheet = {
            "name": "Sentiment Resume",
            "data": [["Message", "Average Confidence", "Average Sentiment", "Negative Sentences", "Neutral Sentences", "Positive Sentences"]] + summary_rows
        }
        sentiment_data.append(resume_sheet)

        # Update Sentiment Analysis Results with only details
        sentiment_sheet["data"] = detail_rows

        # Process Queries to Add Calculated Insights
        insights_data = [["Query", "Average Sentiment Score", "Positive Sentences", "Neutral Sentences", "Negative Sentences", "Confidence"]]
        for query in queries:
            # Match segments for the current query
            matched_segments = [row for row in detail_rows if query.lower() in row[0].lower()]
            
            if matched_segments:
                # Calculate metrics if matched segments exist
                avg_sentiment_score = sum(float(row[2]) for row in matched_segments) / len(matched_segments)
                positive_count = sum(1 for row in matched_segments if "5 stars" in row[1])
                neutral_count = sum(1 for row in matched_segments if "3 stars" in row[1])
                negative_count = sum(1 for row in matched_segments if "1 star" in row[1])
                confidence = avg_sentiment_score
            else:
                # Fallback to NA if no segments match
                avg_sentiment_score = "NA"
                positive_count = "NA"
                neutral_count = "NA"
                negative_count = "NA"
                confidence = "NA"

            insights_data.append([query, avg_sentiment_score, positive_count, neutral_count, negative_count, confidence])

        # DEBUG: Log Insights Data
        logging.debug(f"Query Insights Data: {insights_data}")

        # Add Query Insights to Workbook
        query_sheet = next((sheet for sheet in sentiment_data if sheet["name"] == "Queries"), None)
        if query_sheet:
            query_sheet["data"][0].extend(["Average Sentiment Score", "Positive Sentences", "Neutral Sentences", "Negative Sentences", "Confidence"])
            for i, row in enumerate(query_sheet["data"][1:], start=1):
                if i < len(insights_data):
                    row.extend(insights_data[i][1:])
                else:
                    # Fallback for mismatched query rows
                    row.extend(["NA", "NA", "NA", "NA", "NA"])

        # Update workbook with new insights
        data["workbook"] = sentiment_data

        return data

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

    # Prepare query insights
    query_insights = [["Query", "Average Rating", "Positive Sentences", "Neutral Sentences", "Negative Sentences", "Confidence"]]
    print(f"QUERIES: {queries}")
    for query in queries:
        matched_segments = [
            segment for segment in sentiment_results["results"]["sentiment_analysis"]
            if query.lower() in segment[0].lower()  # Match query in text
        ]

        if matched_segments:
            avg_rating = sum(segment[2] for segment in matched_segments) / len(matched_segments)
            positive_count = sum(1 for segment in matched_segments if "5 stars" in segment[1])
            neutral_count = sum(1 for segment in matched_segments if "3 stars" in segment[1])
            negative_count = sum(1 for segment in matched_segments if "1 star" in segment[1])
            confidence = sum(segment[2] for segment in matched_segments) / len(matched_segments)
        else:
            avg_rating = 0
            positive_count = 0
            neutral_count = 0
            negative_count = 0
            confidence = 0

        query_insights.append([
            query,
            round(avg_rating, 2),
            positive_count,
            neutral_count,
            negative_count,
            round(confidence, 2),
        ])

    return {
        "Sentiment Analysis Summary": summary_data,
        "Sentiment Analysis Results": results_data,
        "Query Insights": query_insights,
    }
