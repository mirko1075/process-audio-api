import logging
from flask import Blueprint, request, jsonify, send_file

from ..auth import require_api_key
from audio_api.domain.process_audio import (
    load_excel_file,
    process_queries,
    create_sentiment_details_df,
    create_sentiment_summary_df,
    generate_multi_sheet_excel,
)
from audio_api.domain.sentiment_analysis import run_sentiment_analysis

sentiment_bp = Blueprint('sentiment', __name__)

@sentiment_bp.route('/sentiment-analysis', methods=['POST'])
@require_api_key
def sentiment_analysis():
    try:
        excel_file = request.files.get('file')
        text = request.form.get('text')
        if not excel_file or not text:
            return jsonify({'error': 'Missing file or text'}), 400

        df_queries = load_excel_file(excel_file)
        responses = process_queries(df_queries, text)
        df_queries['Response'] = responses

        sentiment_results = run_sentiment_analysis(text)
        df_details = create_sentiment_details_df(sentiment_results)
        df_summary = create_sentiment_summary_df(df_details)

        output = generate_multi_sheet_excel(df_queries, df_details, df_summary)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='analyzed_data.xlsx'
        )
    except Exception as e:
        logging.error(f"Error in sentiment_analysis endpoint: {e}")
        return jsonify({'error': str(e)}), 500