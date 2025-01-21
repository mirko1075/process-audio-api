from flask import Flask, request, jsonify
import os
import subprocess
from groq import Groq  # Import Groq library for transcription
from process_audio import process_file, convert_to_wav
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route("/process", methods=["POST"])
def process_audio():
    """
    API endpoint to process and transcribe audio files using Groq Whisper.
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

        # Ensure Groq API key is available
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            logging.error("GROQ_API_KEY not set in environment")
            return jsonify({"error": "GROQ_API_KEY not set in environment"}), 500

        # Initialize Groq client
        client = Groq(api_key=groq_api_key)

        # Process the WAV file
        logging.debug(f"Processing WAV file: {wav_path}")
        transcription = process_file(client, wav_path, "/tmp/temp")

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
