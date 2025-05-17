import io
import datetime
import logging
from flask import Blueprint, request, jsonify, send_file

from ..auth import require_api_key
from audio_api.domain.process_audio import create_word_document

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/text-to-file', methods=['POST'])
def text_to_file():
    try:
        text = request.form.get('text') or (request.json or {}).get('text')
        file_name = request.form.get('fileName') or (request.json or {}).get('fileName')
        if not text or not file_name:
            return jsonify({'error': 'Missing text or fileName'}), 400

        filename = f"{file_name}_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
        file_obj = io.BytesIO()
        file_obj.write(text.encode('utf-8'))
        file_obj.seek(0)

        return send_file(
            file_obj,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logging.error(f"Error creating text file: {e}")
        return jsonify({'error': str(e)}), 500

@documents_bp.route('/generate-excel', methods=['POST'])
@require_api_key
def generate_excel():
    from openpyxl import Workbook
    data = request.json
    if not data or 'sheets' not in data:
        return jsonify({'error': 'Invalid JSON format'}), 400

    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_def in data['sheets']:
        name = sheet_def.get('name', 'Sheet')
        rows = sheet_def.get('data', [])
        sheet = workbook.create_sheet(title=name)
        for row in rows:
            sheet.append(row)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='data_analysis.xlsx'
    )

@documents_bp.route('/generate-word', methods=['POST'])
@require_api_key
def generate_word():
    try:
        text = request.form.get('text', '')
        file_name = request.form.get('fileName', 'file.docx')
        path = create_word_document(text, file_name)
        return send_file(path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error generating Word document: {e}")
        return jsonify({'error': str(e)}), 500