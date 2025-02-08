import json
from flask import Flask, request, jsonify, send_file
import os
import logging
import sys
from openpyxl import Workbook
import pandas as pd
from process_audio import delete_from_gcs, perform_sentiment_analysis, process_audio_file, transcribe_audio, translate_text, upload_to_gcs # Ensure this uses the updated process_audio.py
from functools import wraps
from dotenv import load_dotenv
import io
from datetime import datetime


from sentiment_analysis import process_sentiment_analysis_results

# Load environment variables
load_dotenv()

# Check for Google Cloud credentials at startup
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not GOOGLE_CREDENTIALS_PATH:
    print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
    sys.exit(1)  # Exit if credentials are not set

if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    print(f"ERROR: Credentials file not found at {GOOGLE_CREDENTIALS_PATH}")
    sys.exit(1)  # Exit if file does not exist

print(f"Google Cloud credentials found at {GOOGLE_CREDENTIALS_PATH}")

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY must be set in .env file")

def is_valid_json(json_string):
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        logging.error("Invalid or missing API key")
        return jsonify({"error": "Invalid or missing API key"}), 401
    return decorated

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Hello, World!"})

@app.route('/transcribe_and_translate', methods=['POST'])
def transcribe_and_translate():
    """Handles audio transcription and translation"""
    try:
        logging.info("Received request to transcribe and translate audio")
        
        audio_file = request.files.get("audio")
        language = request.form.get("language", "en")
        target_language = request.form.get("target_language", "en")

        if not audio_file:
            return jsonify({"error": "No file uploaded"}), 400

        # Process and transcribe audio
        formatted_transcript = process_audio_file(audio_file, language)

        # Send transcript for translation
        translated_text = translate_text(formatted_transcript, target_language)

        # Return JSON response
        return jsonify({
            "formatted_transcript": "\n".join(formatted_transcript),
            "translated_text": translated_text
        })

    except Exception as e:
        logging.error(f"Error in transcribe_and_translate: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/translate', methods=['POST'])
def translate_text_endpoint():
    """Translates text to the target language"""
    try:
        logging.info("Received request to translate text")

        data = request.get_json()
        if not data or "text" not in data or "target_language" not in data:
            return jsonify({'error': 'Missing text or target_language in request'}), 400
        
        text = data['text']
        target_language = data['target_language'] or "en"

        # Ensure text is a list
        if not isinstance(text, list):
            text = [text]

        translated_text_response = translate_text(text, target_language)
        translated_text = translated_text_response["joined_translated_text"]
        translated_text_list = translated_text_response["translated_text_list"]
        return jsonify({'translated_text': translated_text, 'translated_text_list': translated_text_list})

    except Exception as e:
        logging.error(f"Error in translate_text: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route("/transcribe-google", methods=["POST"])
def transcribe_endpoint():
    """API endpoint to transcribe an audio file."""
    try:
        file = request.files.get("file")
        gcs_uri = request.form.get("gcs_uri")  # Optional GCS URI
        language_code = request.form.get("language", "en-US")

        if not file and not gcs_uri:
            return jsonify({"error": "No file or GCS URI provided"}), 400

        if file:
            # Save the file temporarily
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)

            # Upload to GCS
            bucket_name = "your-gcs-bucket"  # Replace with your actual bucket
            gcs_uri = upload_to_gcs(temp_path, bucket_name, file.filename)

        # Perform transcription
        transcription = transcribe_audio(gcs_uri, language_code)
        return jsonify({"transcription": transcription})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            os.remove(temp_path)
            #delete from bucket
            delete_from_gcs(gcs_uri)
    

@app.route("/text-to-file", methods=["POST"])
def text_to_file():
    """
    API endpoint to create a text file from input text.
    """
    logging.debug("Received request to create text file")
    
    try:
        # Get JSON data from request safely
        data = request.get_data(as_text=True)
        logging.debug(f"Raw request data: {data}")

        try:
            parsed_data = json.loads(data)  # Handle cases where raw text may cause issues
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
            return jsonify({"error": "Invalid JSON format"}), 400

        # Validate required fields
        if 'text' not in parsed_data or not parsed_data['text']:
            logging.error("No text provided")
            return jsonify({"error": "No text provided"}), 400
        
        if 'fileName' not in parsed_data or not parsed_data['fileName']:
            logging.error("No fileName provided")
            return jsonify({"error": "No fileName provided"}), 400

        text = parsed_data['text']
        filename = f"{parsed_data['fileName']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        # Create file-like object in memory
        file_obj = io.BytesIO()
        file_obj.write(text.encode('utf-8'))  # Ensure proper UTF-8 encoding
        file_obj.seek(0)

        # Return the file
        return send_file(
            file_obj,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logging.error(f"Error creating text file: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/sentiment-analysis', methods=['POST'])
@require_api_key
def sentiment_analysis():
    try:
        logging.debug("Received request to perform sentiment analysis")

        # Save the uploaded file to a temporary location
        excel_file = request.files['file']
        if not excel_file:
            return jsonify({"error": "No file uploaded."}), 400

        # Read the Excel file
        queries_df = pd.read_excel(excel_file, sheet_name="Queries")

        # Perform sentiment analysis (assuming text and model are provided in the request)
        text = request.form.get("text", "")
        best_model = request.form.get("best_model", False)
        sentiment_results = perform_sentiment_analysis(text, best_model)
        logging.debug(f"Sentiment analysis complete: {sentiment_results}")

        # Process the sentiment results and queries
        output_json = process_sentiment_analysis_results(sentiment_results, queries_df)

        # Create Excel file from the JSON structure
        workbook = Workbook()
        workbook.remove(workbook.active)

        for sheet_data in output_json["sheets"]:
            sheet_name = sheet_data["name"]
            sheet = workbook.create_sheet(title=sheet_name)

            for row in sheet_data["data"]:
                sheet.append(row)

        # Save workbook to a BytesIO stream
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        # Return the Excel file
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name="sentiment_analysis.xlsx")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    
@app.route('/generate-excel', methods=['POST'])
@require_api_key
def generate_excel():
    try:
        # Parse the incoming JSON
        data = request.json
        if not data or not is_valid_json(request.data.decode('utf-8')):
            return jsonify({"error": "Invalid JSON format 1"}), 400
        if "sheets" not in data:
            return jsonify({"error": "Invalid JSON format 2"}), 400

        print(f"DATA: {data}")

        # Create a new Excel workbook
        workbook = Workbook()
        # Remove default sheet
        workbook.remove(workbook.active)

        # Process each sheet in the JSON
        for sheet_data in data["sheets"]:
            sheet_name = sheet_data.get("name", "Sheet")
            sheet_data_rows = sheet_data.get("data", [])

            # Create a new sheet
            sheet = workbook.create_sheet(title=sheet_name)

            # Write the rows directly to the sheet
            for row in sheet_data_rows:
                sheet.append(row)

        # Save workbook to a BytesIO stream
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        # Return the Excel file
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name="data_analysis.xlsx")

    except Exception as e:
        # Log the full exception stack trace for debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)