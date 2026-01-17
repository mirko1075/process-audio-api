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
    """
    Create a new job with optional file upload.

    Supports two modes:
    1. JSON mode (existing input_ref):
       Content-Type: application/json
       Body: {"type": "transcription" or "translation", "input_ref": "storage_path"}

    2. File upload mode (upload new file):
       Content-Type: multipart/form-data
       Fields: type (form field), file (file upload)

    Returns:
        201: Job created successfully
        400: Invalid request (missing/invalid fields, file too large, invalid type)
        401: Unauthorized
        500: Storage upload failed
    """
    user_id = get_jwt_identity()

    # Detect request mode: JSON or multipart/form-data
    is_json = request.is_json
    is_multipart = request.content_type and 'multipart/form-data' in request.content_type

    if not is_json and not is_multipart:
        return jsonify({
            'error': 'Content-Type must be application/json or multipart/form-data'
        }), 400

    # Extract job type based on request mode
    if is_json:
        data = request.get_json()
        job_type = data.get('type')
        input_ref = data.get('input_ref')
    else:  # multipart/form-data
        job_type = request.form.get('type')
        input_ref = None  # Will be set after file upload

    # Validate job type
    if not job_type:
        return jsonify({'error': 'Missing required field: type'}), 400

    if job_type not in ['transcription', 'translation']:
        return jsonify({'error': 'Invalid type. Must be "transcription" or "translation"'}), 400

    # Handle file upload mode
    if is_multipart:
        if 'file' not in request.files:
            return jsonify({'error': 'Missing file upload'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Create job first to get job_id for storage path
        job = Job(
            user_id=user_id,
            type=job_type,
            status='queued',
            input_ref='pending'  # Temporary, will be updated after upload
        )
        db.session.add(job)
        db.session.flush()  # Get job.id without committing

        try:
            # Upload file to Supabase Storage
            storage_service = get_storage_service()
            storage_path = storage_service.upload_input(
                user_id=user_id,
                job_id=job.id,
                file=file,
                original_filename=file.filename
            )

            # Update job with actual storage path
            job.input_ref = storage_path
            db.session.commit()

            logger.info(f"Created job {job.id} with uploaded file: {storage_path}")
            return jsonify(job.to_dict()), 201

        except ValueError as e:
            # Validation error (file too large, invalid type)
            db.session.rollback()
            logger.warning(f"File upload validation failed: {e}")
            return jsonify({'error': str(e)}), 400

        except RuntimeError as e:
            # Storage upload error
            db.session.rollback()
            logger.error(f"Storage upload failed: {e}")
            return jsonify({'error': 'File upload failed', 'details': str(e)}), 500

        except Exception as e:
            # Unexpected error
            db.session.rollback()
            logger.error(f"Unexpected error during file upload: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # Handle JSON mode (existing behavior)
    else:
        if not input_ref:
            return jsonify({'error': 'Missing required field: input_ref'}), 400

        # Create job
        job = Job(
            user_id=user_id,
            type=job_type,
            status='queued',
            input_ref=input_ref
        )

        db.session.add(job)
        db.session.commit()

        logger.info(f"Created job {job.id} with input_ref: {input_ref}")
        return jsonify(job.to_dict()), 201


@bp.route('/saas/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    """
    List all jobs for the authenticated user.

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

    # Build query
    query = Job.query.filter_by(user_id=user_id)

    # Apply filters
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter_by(status=status_filter)

    type_filter = request.args.get('type')
    if type_filter:
        query = query.filter_by(type=type_filter)

    # Pagination
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = int(request.args.get('offset', 0))

    # Order by created_at descending (newest first)
    query = query.order_by(Job.created_at.desc())

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    jobs = query.limit(limit).offset(offset).all()

    return jsonify({
        'jobs': [job.to_dict() for job in jobs],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@bp.route('/saas/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """
    Get a specific job by ID.

    Ownership is enforced - users can only retrieve their own jobs.

    Returns:
        200: Job details
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

    return jsonify(job.to_dict()), 200


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
