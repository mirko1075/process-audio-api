from flask import Flask, request, jsonify
import os
import subprocess
import logging
from process_audio import process_file, convert_to_wav  # Ensure this uses the updated process_audio.py
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY must be set in .env file")

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        logging.error("Invalid or missing API key")
        return jsonify({"error": "Invalid or missing API key"}), 401
    return decorated

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

@app.route('/transcribe', methods=['POST'])
@require_api_key
def transcribe():
    # Your existing route code here
    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
