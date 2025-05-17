import os
import datetime
import logging
from flask import Blueprint, request, jsonify, send_file, after_this_request

from ..auth import require_api_key
from audio_api.domain.pdf_generator import PDFGenerator
from audio_api.domain.process_audio import (
    get_audio_duration_from_form_file,
    log_audio_processing,
    get_usage_data,
    RATE_PER_MINUTE,
)

reporting_bp = Blueprint('reporting', __name__)

@reporting_bp.route('/get-audio-duration', methods=['POST'])
@require_api_key
def get_audio_duration():
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'error': 'No audio file provided'}), 400
    duration, error = get_audio_duration_from_form_file(audio_file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Audio processed successfully', 'duration_minutes': duration}), 200

@reporting_bp.route('/log-audio-usage', methods=['POST'])
@require_api_key
def log_usage():
    try:
        user_code = request.form.get('user_code')
        filename = request.form.get('fileName')
        duration = request.form.get('duration')
        if not all([user_code, filename, duration]):
            return jsonify({'error': 'Missing user_code, fileName, or duration'}), 400

        result = log_audio_processing(user_code, filename, duration)
        if not result:
            return jsonify({'error': 'Error during logging'}), 500

        total_cost = float(duration) * RATE_PER_MINUTE
        return jsonify({
            'message': 'Logged successfully',
            'user_code': user_code,
            'filename': filename,
            'duration': duration,
            'cost_per_minute': f'{RATE_PER_MINUTE:.2f}',
            'total_cost': f'{total_cost:.2f}',
            'Billed': 'YES'
        }), 200
    except Exception as e:
        logging.error(f"Error in log_usage endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@reporting_bp.route('/generate-monthly-report', methods=['POST'])
@require_api_key
def generate_monthly_report():
    try:
        user_code = request.form.get('user_code')
        data = get_usage_data(user_code)
        billed = [r for r in data if r.get('Billed') == 'YES']
        current_month = datetime.datetime.now().month
        monthly = [
            r for r in billed
            if datetime.datetime.strptime(r['Data e ora'], '%Y-%m-%d %H:%M:%S').month == current_month
        ]

        pdf = PDFGenerator('Monthly Usage Report')
        pdf.add_table(monthly)
        filename = f'monthly_report_{current_month}.pdf'
        pdf.save_pdf(filename)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(filename)
            except Exception as ex:
                logging.error(f"Error deleting file: {ex}")
            return response

        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error in generate_monthly_report endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@reporting_bp.route('/generate-billing-document', methods=['POST'])
@require_api_key
def generate_billing_document():
    try:
        user_code = request.form.get('user_code')
        data = get_usage_data(user_code)
        current_month = datetime.datetime.now().month
        monthly = [
            r for r in data
            if datetime.datetime.strptime(r['Data e ora'], '%Y-%m-%d %H:%M:%S').month == current_month
        ]
        total_cost = sum(float(r['Costo Totale (€)'].replace(',', '.')) for r in monthly)

        pdf = PDFGenerator('Monthly Billing Document')
        pdf.add_table(monthly)
        pdf.pdf.ln(10)
        pdf.pdf.cell(0, 10, f'Total Cost: €{total_cost:.2f}', 0, 1, 'R')
        filename = f'billing_document_{current_month}.pdf'
        pdf.save_pdf(filename)
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error in generate_billing_document endpoint: {e}")
        return jsonify({'error': str(e)}), 500