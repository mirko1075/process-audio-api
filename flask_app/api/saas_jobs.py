"""SaaS Jobs API - Minimal job persistence and retrieval."""
from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
import logging
from models import db
from models.job import Job
from models.artifact import Artifact
from flask_app.services.storage import get_storage_service

bp = Blueprint('saas_jobs', __name__)
logger = logging.getLogger(__name__)


@bp.route('/saas/jobs', methods=['POST'])
@jwt_required()
def create_job():
    """Create and process a new job.

    Supports two modes:
    1. Transcription: multipart/form-data with file upload
       Required: type='transcription', service='deepgram|whisper|assemblyai', file
       Optional: language, diarize, punctuate, paragraphs, model

    2. Translation: application/json with text
       Required: type='translation', service='openai|google|deepseek', text, target_language
       Optional: source_language

    Returns:
        201: Job created and processed (or processing started)
        400: Invalid request
        401: Unauthorized
        500: Processing failed
    """
    user_id = get_jwt_identity()

    # Detect request mode
    is_json = request.is_json
    is_multipart = request.content_type and 'multipart/form-data' in request.content_type

    if not is_json and not is_multipart:
        return jsonify({'error': 'Content-Type must be application/json or multipart/form-data'}), 400

    # Extract parameters
    if is_json:
        data = request.get_json()
        job_type = data.get('type')
        service = data.get('service')
        input_ref = data.get('text', '')  # For translation
    else:  # multipart
        job_type = request.form.get('type')
        service = request.form.get('service')
        input_ref = None  # Will be set after upload

    # Validate required fields
    if not job_type:
        return jsonify({'error': 'Missing required field: type'}), 400
    if job_type not in ['transcription', 'translation']:
        return jsonify({'error': 'Invalid type. Must be "transcription" or "translation"'}), 400
    if not service:
        return jsonify({'error': 'Missing required field: service'}), 400

    # Validate service based on type
    valid_transcription_services = ['deepgram', 'whisper', 'assemblyai']
    valid_translation_services = ['openai', 'google', 'deepseek']

    if job_type == 'transcription' and service not in valid_transcription_services:
        return jsonify({'error': f'Invalid transcription service. Must be one of: {", ".join(valid_transcription_services)}'}), 400
    if job_type == 'translation' and service not in valid_translation_services:
        return jsonify({'error': f'Invalid translation service. Must be one of: {", ".join(valid_translation_services)}'}), 400

    # Handle file upload (transcription mode)
    if is_multipart:
        if 'file' not in request.files:
            return jsonify({'error': 'Missing file upload'}), 400

        file = request.files['file']
        if not file.filename or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Additional validation: Check for suspiciously long filenames
        if len(file.filename) > 255:
            return jsonify({'error': 'Filename too long (max 255 characters)'}), 400

        # Create job
        job = Job(
            user_id=user_id,
            type=job_type,
            status='queued',
            input_ref='pending'
        )
        db.session.add(job)
        db.session.flush()

        try:
            # Upload file to storage
            storage_service = get_storage_service()
            storage_path = storage_service.upload_input(
                user_id=user_id,
                job_id=job.id,
                file=file,
                original_filename=file.filename
            )
            job.input_ref = storage_path
            db.session.commit()

            # Extract optional parameters
            params = {
                'language': request.form.get('language', 'en'),
                'diarize': request.form.get('diarize', 'false'),
                'punctuate': request.form.get('punctuate', 'true'),
                'paragraphs': request.form.get('paragraphs', 'false'),
                'model': request.form.get('model'),
            }

            # Process job
            from flask_app.services.saas_processor import get_processor_service
            processor = get_processor_service(user_id)
            job = processor.process_job(job, service, params)

            logger.info(f"Job {job.id} processed with service {service}, status={job.status}")
            return jsonify(job.to_dict()), 201

        except ValueError as e:
            db.session.rollback()
            logger.warning(f"Validation failed: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Job processing failed: {e}")
            return jsonify({'error': 'Job processing failed', 'details': str(e)}), 500

    # Handle JSON mode (translation)
    else:
        if not data.get('text'):
            return jsonify({'error': 'Missing required field: text'}), 400
        if not data.get('target_language'):
            return jsonify({'error': 'Missing required field: target_language'}), 400

        # Create job
        job = Job(
            user_id=user_id,
            type=job_type,
            status='queued',
            input_ref=data['text'][:500]  # Store first 500 chars as reference
        )
        db.session.add(job)
        db.session.commit()

        # Extract parameters
        params = {
            'text': data['text'],
            'target_language': data['target_language'],
            'source_language': data.get('source_language', 'auto'),
        }

        # Process job
        from flask_app.services.saas_processor import get_processor_service
        processor = get_processor_service(user_id)
        job = processor.process_job(job, service, params)

        logger.info(f"Translation job {job.id} processed with service {service}, status={job.status}")
        return jsonify(job.to_dict()), 201


@bp.route('/saas/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    """List all jobs for the authenticated user (lightweight).

    Returns minimal job data (id, type, status, fileName, created_at).
    Excludes jobs with status='deleted'.

    Query parameters:
    - status: Filter by status (optional)
    - type: Filter by type (optional)
    - limit: Max number of results (default: 100, max: 500)
    - offset: Pagination offset (default: 0)

    Returns:
        200: List of jobs
        401: Unauthorized
    """
    user_id = get_jwt_identity()

    # Build query - exclude deleted jobs
    query = Job.query.filter_by(user_id=user_id).filter(Job.status != 'deleted')

    # Apply filters with validation
    status_filter = request.args.get('status')
    if status_filter:
        # Validate status against allowed values to prevent SQL injection
        allowed_statuses = ['queued', 'processing', 'done', 'failed']
        if status_filter not in allowed_statuses:
            return jsonify({'error': f'Invalid status filter. Must be one of: {", ".join(allowed_statuses)}'}), 400
        query = query.filter_by(status=status_filter)

    type_filter = request.args.get('type')
    if type_filter:
        # Validate type against allowed values to prevent SQL injection
        allowed_types = ['transcription', 'translation']
        if type_filter not in allowed_types:
            return jsonify({'error': f'Invalid type filter. Must be one of: {", ".join(allowed_types)}'}), 400
        query = query.filter_by(type=type_filter)

    # Pagination with input validation
    try:
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = int(request.args.get('offset', 0))
        if limit < 1 or offset < 0:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid pagination parameters: limit and offset must be integers'}), 400

    # Order by created_at descending (newest first)
    query = query.order_by(Job.created_at.desc())

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    jobs = query.limit(limit).offset(offset).all()

    return jsonify({
        'jobs': [job.to_dict_minimal() for job in jobs],  # Changed from to_dict()
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@bp.route('/saas/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """Get job metadata (no content).

    Returns job fields and artifact metadata (storage refs), but not actual
    transcript/translation content. Content is retrieved separately via
    signed download URLs.

    Ownership is enforced - users can only retrieve their own jobs.

    Returns:
        200: Job metadata
        401: Unauthorized
        403: Forbidden (job belongs to another user)
        404: Job not found (or deleted)
    """
    user_id = get_jwt_identity()

    job = Job.query.filter_by(id=job_id).first()

    if not job or job.status == 'deleted':
        return jsonify({'error': 'Job not found'}), 404

    # Enforce ownership
    if job.user_id != user_id:
        return jsonify({'error': 'Forbidden: You do not have access to this job'}), 403

    return jsonify(job.to_dict_metadata()), 200  # Changed from to_dict()


@bp.route('/saas/jobs/<int:job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    """Soft-delete a job (set status to 'deleted').

    Idempotent operation - returns success even if already deleted.

    Ownership is enforced - users can only delete their own jobs.

    Returns:
        200: Job deleted successfully
        401: Unauthorized
        403: Forbidden (job belongs to another user)
        404: Job not found
    """
    user_id = get_jwt_identity()

    job = Job.query.filter_by(id=job_id).first()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Enforce ownership
    if job.user_id != user_id:
        return jsonify({'error': 'Forbidden: You do not have access to this job'}), 403

    # Soft delete (idempotent)
    if job.status != 'deleted':
        job.status = 'deleted'
        db.session.commit()
        logger.info(f"Job {job_id} deleted by user {user_id}")

    return jsonify({
        'message': 'Job deleted successfully',
        'job_id': job_id
    }), 200


@bp.route('/saas/jobs/<int:job_id>/artifacts', methods=['GET'])
@jwt_required()
def get_job_artifacts(job_id):
    """
    Get all artifacts for a specific job.

    Ownership is enforced - users can only retrieve artifacts for their own jobs.

    Returns:
        200: List of artifacts
        401: Unauthorized
        403: Forbidden (job belongs to another user)
        404: Job not found
    """
    user_id = get_jwt_identity()

    # Fetch job and verify ownership
    job = Job.query.filter_by(id=job_id).first()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job.user_id != user_id:
        return jsonify({'error': 'Forbidden: You do not have access to this job'}), 403

    # Get all artifacts for this job
    artifacts = Artifact.query.filter_by(job_id=job_id).all()

    return jsonify({
        'job_id': job_id,
        'artifacts': [artifact.to_dict() for artifact in artifacts]
    }), 200


@bp.route('/saas/artifacts/<int:artifact_id>/download', methods=['GET'])
@jwt_required()
def download_artifact(artifact_id):
    """
    Generate a short-lived signed URL for downloading an artifact.

    Ownership is enforced - users can only download artifacts from their own jobs.

    Returns:
        200: Signed URL (valid for 5 minutes by default)
        401: Unauthorized
        403: Forbidden (artifact belongs to another user)
        404: Artifact not found
        500: Failed to generate signed URL
    """
    user_id = get_jwt_identity()

    # Fetch artifact
    artifact = Artifact.query.filter_by(id=artifact_id).first()

    if not artifact:
        return jsonify({'error': 'Artifact not found'}), 404

    # Fetch associated job to verify ownership
    job = Job.query.filter_by(id=artifact.job_id).first()

    if not job:
        return jsonify({'error': 'Associated job not found'}), 404

    if job.user_id != user_id:
        return jsonify({'error': 'Forbidden: You do not have access to this artifact'}), 403

    # Generate signed URL
    try:
        storage_service = get_storage_service()

        # Verify path ownership as additional security check
        if not storage_service.verify_path_ownership(artifact.storage_ref, user_id):
            logger.warning(f"Path ownership mismatch for artifact {artifact_id}: {artifact.storage_ref}")
            return jsonify({'error': 'Forbidden: Invalid storage path'}), 403

        signed_url = storage_service.generate_signed_url(artifact.storage_ref)

        logger.info(f"Generated download URL for artifact {artifact_id} (job {job.id})")

        return jsonify({
            'artifact_id': artifact_id,
            'job_id': artifact.job_id,
            'kind': artifact.kind,
            'download_url': signed_url,
            'expires_in_seconds': storage_service.signed_url_ttl_seconds
        }), 200

    except RuntimeError as e:
        logger.error(f"Failed to generate signed URL for artifact {artifact_id}: {e}")
        return jsonify({'error': 'Failed to generate download URL', 'details': str(e)}), 500

    except Exception as e:
        logger.error(f"Unexpected error generating download URL: {e}")
        return jsonify({'error': 'Internal server error'}), 500
