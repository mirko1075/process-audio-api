"""Post-processing API blueprint - Flask best practices style."""
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.exceptions import BadRequest

from flask_app.services.postprocessing import SentimentService, DocumentService
from utils.auth import require_api_key
from utils.exceptions import TranslationError


bp = Blueprint('postprocessing', __name__)
logger = logging.getLogger(__name__)


@bp.route('/sentiment', methods=['POST'])
@require_api_key
def sentiment_analysis():
    """Analyze sentiment of text.
    
    Accepts JSON with:
    - text: Text to analyze
    """
    logger.info("Sentiment analysis request received")
    
    # Validate JSON request
    if not request.is_json:
        raise BadRequest('Request must be JSON')
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        raise BadRequest('Missing required field: text')
    
    text = data['text']
    
    # Validate text is not empty
    if not text.strip():
        raise BadRequest('Text cannot be empty')
    
    logger.info(f"Processing sentiment analysis (text length: {len(text)})")
    
    try:
        # Use service to analyze sentiment
        service = SentimentService()
        result = service.analyze(text)
        
        logger.info("Sentiment analysis completed successfully")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/documents/<format>', methods=['POST'])
@require_api_key
def generate_document(format):
    """Generate document in specified format.
    
    Accepts JSON with:
    - text: Text content for document
    - title: Document title (optional)
    
    Supported formats: word, pdf
    """
    logger.info(f"Document generation request received: format={format}")
    
    # Validate format
    if format not in ['word', 'pdf']:
        raise BadRequest('Unsupported format. Use: word, pdf')
    
    # Validate JSON request
    if not request.is_json:
        raise BadRequest('Request must be JSON')
    
    data = request.get_json()
    
    # Validate required fields
    if 'text' not in data:
        raise BadRequest('Missing required field: text')
    
    text = data['text']
    title = data.get('title', 'Transcription Report')
    
    # Validate text is not empty
    if not text.strip():
        raise BadRequest('Text cannot be empty')
    
    logger.info(f"Generating {format} document: {title}")
    
    try:
        # Use service to generate document
        service = DocumentService()
        
        if format == 'word':
            file_path = service.generate_word(text, title)
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = f"{title.replace(' ', '_')}.docx"
        elif format == 'pdf':
            file_path = service.generate_pdf(text, title)
            mimetype = 'application/pdf'
            filename = f"{title.replace(' ', '_')}.pdf"
        
        logger.info(f"Document generated successfully: {filename}")
        
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Document generation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/reports/<format>', methods=['POST'])
@require_api_key
def generate_report(format):
    """Generate analysis report in specified format.
    
    Accepts JSON with:
    - transcript: Transcript text
    - analysis: Analysis data (sentiment, keywords, etc.)
    - title: Report title (optional)
    
    Supported formats: excel
    """
    logger.info(f"Report generation request received: format={format}")
    
    # Validate format
    if format not in ['excel']:
        raise BadRequest('Unsupported format. Use: excel')
    
    # Validate JSON request
    if not request.is_json:
        raise BadRequest('Request must be JSON')
    
    data = request.get_json()
    
    # Validate required fields
    if 'transcript' not in data:
        raise BadRequest('Missing required field: transcript')
    
    transcript = data['transcript']
    analysis = data.get('analysis', {})
    title = data.get('title', 'Transcription Analysis Report')
    
    # Validate transcript is not empty
    if not transcript.strip():
        raise BadRequest('Transcript cannot be empty')
    
    logger.info(f"Generating {format} report: {title}")
    
    try:
        # Use service to generate report
        service = DocumentService()
        file_path = service.generate_excel_report(transcript, analysis, title)
        
        filename = f"{title.replace(' ', '_')}.xlsx"
        
        logger.info(f"Report generated successfully: {filename}")
        
        return send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Error handlers specific to this blueprint
@bp.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {error.description}")
    return jsonify({'error': error.description}), 400