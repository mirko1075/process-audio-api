"""Utilities API blueprint - Flask best practices style."""
import logging
import os
import tempfile
import subprocess
import json
from flask import Blueprint, request, jsonify, send_file
from werkzeug.exceptions import BadRequest
from io import BytesIO
import datetime

from utils.auth import require_api_key

# Optional Google Sheets integration
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    gspread = None
    ServiceAccountCredentials = None


bp = Blueprint('utilities', __name__)
logger = logging.getLogger(__name__)

# Google Sheets configuration
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google/google-credentials.json")
RATE_PER_MINUTE = 12 / 60  # €12 per hour = €0.20 per minute

# Initialize Google Sheets client if available
google_client = None
if GOOGLE_SHEETS_AVAILABLE:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_PATH, scope)
        google_client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized successfully")
    except Exception as e:
        logger.warning(f"Google Sheets client initialization failed: {e}")
        google_client = None
else:
    logger.warning("Google Sheets functionality not available - gspread module not installed")


@bp.route('/audio-duration', methods=['POST'])
@require_api_key
def get_audio_duration():
    """Get the duration of an uploaded audio file.
    
    Accepts multipart/form-data with:
    - audio: Audio file
    
    Returns:
    - duration_minutes: Duration in minutes
    """
    logger.info("Audio duration request received")
    
    # Validate audio file
    if 'audio' not in request.files:
        raise BadRequest('No audio file provided')
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        raise BadRequest('No audio file selected')
    
    try:
        # Save uploaded audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
            audio_file.seek(0)  # Reset file pointer
            temp_file.write(audio_file.read())
            temp_file_path = temp_file.name

        # Use ffprobe to get the duration
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                temp_file_path
            ],
            capture_output=True,
            text=True
        )

        # Clean up temp file
        os.remove(temp_file_path)

        if result.returncode != 0:
            logger.error(f"FFprobe failed: {result.stderr}")
            return jsonify({"error": "Failed to analyze audio file"}), 400

        duration_data = json.loads(result.stdout)
        seconds = float(duration_data["format"]["duration"])
        minutes = round(seconds / 60, 2)

        logger.info(f"Audio duration calculated: {minutes} minutes")
        return jsonify({
            "message": "Audio processed successfully",
            "duration_minutes": minutes
        })

    except Exception as e:
        logger.error(f"Error calculating audio duration: {e}")
        return jsonify({"error": f"Error reading audio duration: {str(e)}"}), 500


@bp.route('/log-usage', methods=['POST'])
@require_api_key
def log_audio_usage():
    """Log audio usage for billing purposes.
    
    Accepts form data with:
    - user_code: User identifier
    - fileName: Name of the processed file
    - duration: Duration in minutes
    
    Returns:
    - Billing information
    """
    logger.info("Audio usage logging request received")
    
    # Get required parameters
    user_code = request.form.get("user_code")
    filename = request.form.get("fileName")
    duration = request.form.get("duration")

    if not user_code or not filename or not duration:
        raise BadRequest("Missing required parameters: user_code, fileName, or duration")

    try:
        # Validate duration
        try:
            duration_float = float(duration)
        except ValueError:
            raise BadRequest(f"Invalid duration value: {duration}")

        # Log the data to Google Sheets
        result = _log_audio_processing(user_code, filename, duration_float)

        if result is None:
            logger.warning("Google Sheets logging failed - continuing without logging")
            # Continue without failing if Google Sheets is not available

        # Calculate costs
        cost_per_minute = RATE_PER_MINUTE
        total_cost = duration_float * cost_per_minute

        logger.info(f"Usage logged: {filename} - {duration_float} min - €{total_cost:.2f}")
        
        return jsonify({
            "message": "File processed successfully",
            "user_code": user_code,
            "filename": filename,
            "duration": duration_float,
            "cost_per_minute": f"{cost_per_minute:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "Billed": 'YES'
        })

    except Exception as e:
        logger.error(f"Error logging audio usage: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route('/text-file', methods=['POST'])
def create_text_file():
    """Create a text file from input text.
    
    Accepts form data with:
    - text: Text content
    - filename: Desired filename (optional, default: 'output.txt')
    
    Returns:
    - Text file download
    """
    logger.info("Text file creation request received")
    
    # Get parameters
    text = request.form.get('text', '')
    filename = request.form.get('filename', 'output.txt')
    
    if not text:
        raise BadRequest('No text content provided')
    
    # Ensure filename has .txt extension
    if not filename.endswith('.txt'):
        filename += '.txt'
    
    try:
        # Create text file in memory
        file_obj = BytesIO()
        file_obj.write(text.encode('utf-8'))
        file_obj.seek(0)

        logger.info(f"Text file created: {filename}")
        
        # Return the file
        return send_file(
            file_obj,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error creating text file: {e}")
        return jsonify({"error": str(e)}), 500


def _get_or_create_sheet(user_code: str):
    """Get or create a Google Sheet for the user."""
    if not GOOGLE_SHEETS_AVAILABLE or not google_client:
        logger.warning("Google Sheets not available")
        return None
        
    sheet_name = f"{user_code}_usage_audio_translate"
    logger.info(f"Getting/creating sheet: {sheet_name}")

    try:
        # Try to open existing sheet
        sheet = google_client.open(sheet_name).sheet1
        logger.info(f"Found existing sheet: {sheet_name}")
    except gspread.exceptions.SpreadsheetNotFound:
        try:
            # Create new sheet
            logger.info(f"Creating new sheet: {sheet_name}")
            sheet = google_client.create(sheet_name).sheet1
            # Add headers
            sheet.append_row(["Data e Ora", "Nome File", "Durata (minuti)", "Costo Unitario (€)", "Costo Totale (€)", "Billed"])
            logger.info(f"Created new sheet with headers: {sheet_name}")
        except Exception as e:
            logger.error(f"Error creating sheet: {e}")
            return None

    return sheet


def _log_audio_processing(user_code: str, filename: str, duration: float):
    """Log audio processing to Google Sheets."""
    try:
        sheet = _get_or_create_sheet(user_code)
        if not sheet:
            return None

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cost_per_minute = RATE_PER_MINUTE
        total_cost = duration * cost_per_minute

        # Log to Google Sheets
        logger.info(f"Logging to Google Sheets: {now}, {filename}, {duration}, {cost_per_minute}, {total_cost}")
        sheet.append_row([now, filename, duration, f"{cost_per_minute:.2f}", f"{total_cost:.2f}", 'YES'])
        
        logger.info(f"Successfully logged to Google Sheets: {filename} - {duration} min - €{total_cost:.2f}")
        return True

    except Exception as e:
        logger.error(f"Error logging to Google Sheets: {e}")
        return None


# Error handlers specific to this blueprint
@bp.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {error.description}")
    return jsonify({'error': error.description}), 400