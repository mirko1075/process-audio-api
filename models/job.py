"""Job model for SaaS job persistence."""
from datetime import datetime, timezone
from models import db


class Job(db.Model):
    """Job model for tracking transcription/translation tasks."""

    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # 'transcription' or 'translation'
    status = db.Column(db.String(50), nullable=False, default='queued')  # queued, processing, done, failed
    input_ref = db.Column(db.Text, nullable=False)  # file key or text hash
    error_message = db.Column(db.Text, nullable=True)  # error details if failed
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationship to artifacts
    artifacts = db.relationship('Artifact', backref='job', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Convert job to dictionary representation."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'status': self.status,
            'input_ref': self.input_ref,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'artifacts': [artifact.to_dict() for artifact in self.artifacts]
        }

    def to_dict_minimal(self):
        """Lightweight representation for list view (GET /saas/jobs).

        Returns only essential fields for job listing.
        Used for performance optimization when listing many jobs.
        """
        # Extract filename from input_ref path
        file_name = self.input_ref.split('/')[-1] if self.input_ref else None

        return {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'fileName': file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def to_dict_metadata(self):
        """Full metadata including artifacts, but no content (GET /saas/jobs/{id}).

        Returns all job fields plus artifact metadata (storage refs, not content).
        Content is retrieved separately via signed download URLs.
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'status': self.status,
            'input_ref': self.input_ref,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'artifacts': [artifact.to_dict() for artifact in self.artifacts]
        }

    def __repr__(self):
        return f'<Job {self.id} user={self.user_id} type={self.type} status={self.status}>'
