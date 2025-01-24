from flask import Flask, request, jsonify, send_file
import os
import logging
from process_audio import process_file, convert_to_wav, detect_language_with_whisper  # Ensure this uses the updated process_audio.py
from functools import wraps
from dotenv import load_dotenv
import io
from datetime import datetime
import subprocess
import requests
# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = os.getenv('API_KEY')
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
DEEPGRAM_API_SENTIMENT_URL = os.getenv('DEEPGRAM_API_SENTIMENT_URL')
if not API_KEY:
    raise ValueError("API_KEY must be set in .env file")

if not DEEPGRAM_API_SENTIMENT_URL:
    raise ValueError("DEEPGRAM_API_SENTIMENT_URL must be set in .env file.")

if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY must be set in .env file.")

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
           
@app.route("/process", methods=["POST"])
@require_api_key
def process_audio():
    """
    API endpoint to process and transcribe audio files using OpenAI Whisper.
    """
    logging.debug("Received request to process audio")
    
    if "audio" not in request.files:
        logging.error("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400

    audio_file = request.files["audio"]
    input_path = os.path.join("/tmp", audio_file.filename)
    wav_path = os.path.join("/tmp", f"{os.path.splitext(audio_file.filename)[0]}.wav")

    try:
        # Save the uploaded file
        logging.debug(f"Saving uploaded file to {input_path}")
        audio_file.save(input_path)

        # Convert to WAV if not already a WAV file
        if not input_path.lower().endswith(".wav"):
            logging.debug(f"Converting {input_path} to WAV format")
            convert_to_wav(input_path, wav_path)
        else:
            wav_path = input_path  # If already a WAV file, use as is
            logging.debug(f"Using existing WAV file: {wav_path}")

        # Process the WAV file using OpenAI Whisper API
        logging.debug(f"Processing WAV file: {wav_path}")
        transcription = process_file(wav_path, "/tmp/temp")  # Ensure this uses the updated process_file

        # Check if transcription is valid
        if not transcription or not isinstance(transcription, str):
            logging.error("Transcription failed or returned invalid data")
            return jsonify({"error": "Transcription failed or returned invalid data"}), 500

        # Clean up uploaded and converted files
        if input_path != wav_path:  # Only delete input if converted
            logging.debug(f"Removing uploaded file: {input_path}")
            os.remove(input_path)
        logging.debug(f"Removing WAV file: {wav_path}")
        os.remove(wav_path)

        logging.info("Processing complete, returning transcription")
        return jsonify({"message": "Processing complete", "transcription": transcription})

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temporary files
        temp_dir = "/tmp/temp"
        if os.path.exists(temp_dir):
            logging.debug(f"Cleaning up temporary files in {temp_dir}")
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))

@app.route("/process-to-file", methods=["POST"])
@require_api_key
def process_audio_to_file():
    """
    API endpoint to process audio and return the transcription as a text file.
    """
    logging.debug("Received request to process audio to file")
    
    if "audio" not in request.files:
        logging.error("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400
    language = request.json.get("language", "en")
    audio_file = request.files["audio"]
    input_path = os.path.join("/tmp", audio_file.filename)
    wav_path = os.path.join("/tmp", f"{os.path.splitext(audio_file.filename)[0]}.wav")

    try:
        # Save the uploaded file
        audio_file.save(input_path)

        # Convert to WAV if needed
        if not input_path.lower().endswith(".wav"):
            convert_to_wav(input_path, wav_path)
        else:
            wav_path = input_path

        # Process the WAV file
        transcription = process_file(wav_path, "/tmp/temp", language)

        # Create text file in memory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcription_{timestamp}.txt"
        
        # Create file-like object in memory
        file_obj = io.BytesIO()
        file_obj.write(transcription.encode('utf-8'))
        file_obj.seek(0)

        # Clean up
        if input_path != wav_path:
            os.remove(input_path)
        os.remove(wav_path)

        # Return the file
        return send_file(
            file_obj,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logging.error(f"Error processing audio to file: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temporary files
        temp_dir = "/tmp/temp"
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))

@app.route("/text-to-file", methods=["POST"])
@require_api_key
def text_to_file():
    """
    API endpoint to create a text file from input text.
    """
    logging.debug("Received request to create text file")
    
    # Get JSON data from request
    data = request.get_json()
    if not data or 'text' not in data:
        logging.error("No text provided")
        return jsonify({"error": "No text provided"}), 400
    if not data or 'fileName' not in data:
        logging.error("No fileName provided")
        return jsonify({"error": "No fileName provided"}), 400
    try:
        text = data['text']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = data['fileName'] + f"_{timestamp}.txt"
        
        # Create file-like object in memory
        file_obj = io.BytesIO()
        file_obj.write(text.encode('utf-8'))
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

@app.route('/translate', methods=['POST'])
@require_api_key
def translate():
    # Your existing route code here
    pass


@app.route("/sentiment", methods=["POST"])
@require_api_key
def sentiment():
    """
    Endpoint to analyze sentiment using Deepgram's API.
    """
    try:
        # Validate request payload
        if "text" not in request.json:
            return jsonify({"error": "Text input is required."}), 400

        text = request.json["text"]
        language = request.json.get("language", "en")  # Default to English

        # Ensure only English is supported
        if language != "en":
            return jsonify({
                "error": f"Unsupported language '{language}'. Only English is supported."
            }), 400

        # Prepare request payload and headers
        payload = {
            "text": text
        }
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "sentiment": "true",
            "language": language
        }

        # Send request to Deepgram API
        response = requests.post(DEEPGRAM_API_SENTIMENT_URL, headers=headers, params=params, json=payload)
        response.raise_for_status()

        # Parse and return the response
        result = response.json()
        return jsonify({
            "message": "Sentiment analysis complete.",
            "data": result["results"]["sentiments"]
        })

    except requests.RequestException as e:
        return jsonify({"error": f"Deepgram API request failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)