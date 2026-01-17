"""SaaS Jobs API - Minimal job persistence and retrieval."""
from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from models import db
from models.job import Job
from models.artifact import Artifact

bp = Blueprint('saas_jobs', __name__)


@bp.route('/saas/jobs', methods=['POST'])
@jwt_required()
def create_job():
    """
    Create a new job.

    Request body:
    {
        "type": "transcription" or "translation",
        "input_ref": "file_key_or_text_hash"
    }

    Returns:
        201: Job created successfully
        400: Invalid request (missing/invalid fields)
        401: Unauthorized
    """
    user_id = get_jwt_identity()

    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()

    # Validate required fields
    job_type = data.get('type')
    input_ref = data.get('input_ref')

    if not job_type:
        return jsonify({'error': 'Missing required field: type'}), 400

    if job_type not in ['transcription', 'translation']:
        return jsonify({'error': 'Invalid type. Must be "transcription" or "translation"'}), 400

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
