from flask import Flask, request, jsonify, send_file
import os
import logging
from process_audio import perform_sentiment_analysis, process_file, convert_to_wav, transcribe_audio_assemblyai # Ensure this uses the updated process_audio.py
from functools import wraps
from dotenv import load_dotenv
import io
from datetime import datetime

from sentiment_analysis import allowed_file, generate_excel_from_data, query_assistant


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

    double_model = request.form.get("double_model")
    language = request.form.get("language", "en")
    sentiment_analysis = request.form.get("sentiment_analysis", False)
    best_model = request.form.get("best_model", False)
    if sentiment_analysis == "true":
        sentiment_analysis = True
    else:
        sentiment_analysis = False
    if double_model:
        double_model = True
    else:
        double_model = False

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
            
        logging.debug(f"Transcripting WAV file whith assemblyai: {wav_path}")
        assemblyai_transcription = transcribe_audio_assemblyai(wav_path, best_model)
        logging.debug(f"AssemblyAI transcription: {assemblyai_transcription}")
        if double_model:
            # Process the WAV file using OpenAI Whisper API
            logging.debug(f"Transcripting WAV file whith whisper: {wav_path}")
            whisper_transcription = process_file(wav_path, "/tmp/temp", language)  # Ensure this uses the updated process_file

            # Check if transcription is valid
            if not whisper_transcription or not isinstance(whisper_transcription, str):
                logging.error("Transcription failed or returned invalid data")
                return jsonify({"error": "Transcription failed or returned invalid data"}), 500
            logging.debug(f"Whisper transcription: {whisper_transcription}")


        # Clean up uploaded and converted files
        if input_path != wav_path:  # Only delete input if converted
            logging.debug(f"Removing uploaded file: {input_path}")
            os.remove(input_path)
        logging.debug(f"Removing WAV file: {wav_path}")
        os.remove(wav_path)

        logging.info("Processing complete, returning transcription")

        result = {"message": "Processing complete", "model1_transcription": assemblyai_transcription}
        if double_model:
            result["model2_transcription"] = whisper_transcription
        return jsonify(result)

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
    best_model = request.json.get("best_model", False)
    audio_file = request.files["audio"]
    input_path = os.path.join("/tmp", audio_file.filename)
    wav_path = os.path.join("/tmp", f"{os.path.splitext(audio_file.filename)[0]}.wav")

    try:
        # Save the uploaded file
        audio_file.save(input_path)
        logging.debug(f"Saved uploaded file to {input_path}")

        # Convert to WAV if needed
        if not input_path.lower().endswith(".wav"):
            convert_to_wav(input_path, wav_path)
        else:
            wav_path = input_path
        logging.debug(f"Converted to WAV: {wav_path}")

        # Process the WAV file
        transcription = transcribe_audio_assemblyai(wav_path, best_model)
        logging.debug(f"Processed file: {transcription}")

        # Create text file in memory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcription_{timestamp}.txt"
        logging.debug(f"Creating file: {filename}")

        # Create file-like object in memory
        file_obj = io.BytesIO()
        file_obj.write(transcription.encode('utf-8'))
        file_obj.seek(0)
        logging.debug(f"File created: {file_obj}")

        # Clean up
        if input_path != wav_path:
            os.remove(input_path)
        os.remove(wav_path)
        logging.debug(f"Files removed: {input_path}, {wav_path}")

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
    """
    API endpoint to process audio and return the translation as a text file.
    """
    pass

@app.route('/sentiment-analysis', methods=['POST'])
@require_api_key
def sentiment_analysis():
    try:
        logging.debug("Received request to perform sentiment analysis")

        # Save the uploaded file to a temporary location
        text = request.json.get("text", "")
        best_model = request.json.get("best_model", False)

        # Perform sentiment analysis
        sentiment_results = perform_sentiment_analysis(text, best_model)
        logging.debug(f"Sentiment analysis complete: {sentiment_results}")

        # Return the sentiment analysis results
        return jsonify({
            "message": "Sentiment analysis complete.",
            "results": sentiment_results
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/process-sentiment", methods=["POST"])
@require_api_key
def process_sentiment():
    """
    Endpoint to process sentiment analysis and generate Excel files.
    """
    try:
        # Validate the request files
        if 'queries' not in request.files or 'sentiment_json' not in request.form:
            return jsonify({"error": "Missing required files: queries and/or sentiment_json"}), 400

        queries_file = request.files['queries']
        sentiment_json = request.form.get('sentiment_json')

        # Validate file formats
        if not (queries_file and allowed_file(queries_file.filename)):
            return jsonify({"error": "Invalid queries file format. Only .xls or .xlsx are allowed."}), 400

        assistant_response = query_assistant(queries_file, sentiment_json)
       # DEBUG: Log the assistant response
        print(f"Assistant Response: {assistant_response}")

        
        # Check if the assistant returned a direct Excel binary
        if "EXCEL_BINARY:" in assistant_response:
            # Extract binary data from the response
            excel_binary = assistant_response.split("EXCEL_BINARY:")[1].strip()
            return send_file(
                io.BytesIO(bytes.fromhex(excel_binary)),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="sentiment_analysis.xlsx"
            )
        else:
            # Assistant returned structured data, generate the Excel in the backend
            return generate_excel_from_data(assistant_response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)