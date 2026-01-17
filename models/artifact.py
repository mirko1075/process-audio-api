"""Artifact model for storing job output references."""
from models import db


class Artifact(db.Model):
    """Artifact model for storing references to job outputs."""

    __tablename__ = 'artifacts'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    kind = db.Column(db.String(50), nullable=False)  # transcript, translation, srt, json
    storage_ref = db.Column(db.Text, nullable=False)  # reference to stored artifact

    def to_dict(self):
        """Convert artifact to dictionary representation."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'kind': self.kind,
            'storage_ref': self.storage_ref
        }

    def __repr__(self):
        return f'<Artifact {self.id} job={self.job_id} kind={self.kind}>'
