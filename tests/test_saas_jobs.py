"""Tests for SaaS Jobs API endpoints."""
import pytest
from flask_jwt_extended import create_access_token
from models import db
from models.job import Job
from models.artifact import Artifact


@pytest.fixture
def auth_headers(app):
    """Create valid JWT tokens for testing."""
    with app.app_context():
        access_token_user1 = create_access_token(identity='user_1')
        access_token_user2 = create_access_token(identity='user_2')
        return {
            'user1': {'Authorization': f'Bearer {access_token_user1}'},
            'user2': {'Authorization': f'Bearer {access_token_user2}'}
        }


@pytest.fixture
def sample_jobs(app):
    """Create sample jobs for testing."""
    with app.app_context():
        # Jobs for user_1
        job1 = Job(
            user_id='user_1',
            type='transcription',
            status='done',
            input_ref='s3://bucket/audio1.wav'
        )
        job2 = Job(
            user_id='user_1',
            type='translation',
            status='queued',
            input_ref='s3://bucket/text1.txt'
        )

        # Job for user_2
        job3 = Job(
            user_id='user_2',
            type='transcription',
            status='processing',
            input_ref='s3://bucket/audio2.wav'
        )

        db.session.add_all([job1, job2, job3])
        db.session.commit()

        # Add artifact to job1
        artifact1 = Artifact(
            job_id=job1.id,
            kind='transcript',
            storage_ref='s3://bucket/outputs/transcript1.txt'
        )
        db.session.add(artifact1)
        db.session.commit()

        return {
            'user1_job1': job1.id,
            'user1_job2': job2.id,
            'user2_job1': job3.id
        }


class TestCreateJob:
    """Test POST /saas/jobs - Create new job."""

    def test_create_transcription_job_success(self, client, auth_headers):
        """Test successfully creating a transcription job."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json={
                'type': 'transcription',
                'input_ref': 's3://bucket/new_audio.wav'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['type'] == 'transcription'
        assert data['status'] == 'queued'
        assert data['input_ref'] == 's3://bucket/new_audio.wav'
        assert data['user_id'] == 'user_1'
        assert 'id' in data
        assert 'created_at' in data
        assert data['artifacts'] == []

    def test_create_translation_job_success(self, client, auth_headers):
        """Test successfully creating a translation job."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json={
                'type': 'translation',
                'input_ref': 'text_hash_abc123'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['type'] == 'translation'
        assert data['status'] == 'queued'
        assert data['input_ref'] == 'text_hash_abc123'

    def test_create_job_without_auth(self, client):
        """Test creating job without authentication returns 401."""
        response = client.post(
            '/saas/jobs',
            json={
                'type': 'transcription',
                'input_ref': 's3://bucket/audio.wav'
            }
        )

        assert response.status_code == 401

    def test_create_job_missing_type(self, client, auth_headers):
        """Test creating job without type field returns 400."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json={
                'input_ref': 's3://bucket/audio.wav'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'type' in data['error']

    def test_create_job_missing_input_ref(self, client, auth_headers):
        """Test creating job without input_ref field returns 400."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json={
                'type': 'transcription'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'input_ref' in data['error']

    def test_create_job_invalid_type(self, client, auth_headers):
        """Test creating job with invalid type returns 400."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json={
                'type': 'invalid_type',
                'input_ref': 's3://bucket/audio.wav'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'transcription' in data['error'] or 'translation' in data['error']

    def test_create_job_non_json_request(self, client, auth_headers):
        """Test creating job with non-JSON request returns 400."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data='not json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestListJobs:
    """Test GET /saas/jobs - List jobs for authenticated user."""

    def test_list_jobs_success(self, client, auth_headers, sample_jobs):
        """Test successfully listing jobs for a user."""
        response = client.get(
            '/saas/jobs',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'jobs' in data
        assert 'total' in data
        assert 'limit' in data
        assert 'offset' in data

        # User 1 should see 2 jobs
        assert data['total'] == 2
        assert len(data['jobs']) == 2

        # Verify job data includes all fields
        job = data['jobs'][0]
        assert 'id' in job
        assert 'user_id' in job
        assert 'type' in job
        assert 'status' in job
        assert 'input_ref' in job
        assert 'created_at' in job
        assert 'artifacts' in job

    def test_list_jobs_empty(self, client, auth_headers):
        """Test listing jobs when user has no jobs."""
        # Create a new user token that has no jobs
        with client.application.app_context():
            new_user_token = create_access_token(identity='user_3')

        response = client.get(
            '/saas/jobs',
            headers={'Authorization': f'Bearer {new_user_token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 0
        assert len(data['jobs']) == 0

    def test_list_jobs_filter_by_status(self, client, auth_headers, sample_jobs):
        """Test filtering jobs by status."""
        response = client.get(
            '/saas/jobs?status=done',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['jobs'][0]['status'] == 'done'

    def test_list_jobs_filter_by_type(self, client, auth_headers, sample_jobs):
        """Test filtering jobs by type."""
        response = client.get(
            '/saas/jobs?type=transcription',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['jobs'][0]['type'] == 'transcription'

    def test_list_jobs_pagination_limit(self, client, auth_headers, sample_jobs):
        """Test pagination with limit parameter."""
        response = client.get(
            '/saas/jobs?limit=1',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['limit'] == 1
        assert len(data['jobs']) == 1
        assert data['total'] == 2  # Total count unchanged

    def test_list_jobs_pagination_offset(self, client, auth_headers, sample_jobs):
        """Test pagination with offset parameter."""
        response = client.get(
            '/saas/jobs?limit=1&offset=1',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['limit'] == 1
        assert data['offset'] == 1
        assert len(data['jobs']) == 1

    def test_list_jobs_max_limit_enforced(self, client, auth_headers, sample_jobs):
        """Test that maximum limit of 500 is enforced."""
        response = client.get(
            '/saas/jobs?limit=1000',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['limit'] == 500  # Should be capped at 500

    def test_list_jobs_without_auth(self, client):
        """Test listing jobs without authentication returns 401."""
        response = client.get('/saas/jobs')

        assert response.status_code == 401

    def test_list_jobs_user_isolation(self, client, auth_headers, sample_jobs):
        """Test that users can only see their own jobs."""
        # User 2 should only see their own job
        response = client.get(
            '/saas/jobs',
            headers=auth_headers['user2']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['jobs'][0]['user_id'] == 'user_2'

        # Verify user 2 doesn't see user 1's jobs
        job_ids = [job['id'] for job in data['jobs']]
        assert sample_jobs['user1_job1'] not in job_ids
        assert sample_jobs['user1_job2'] not in job_ids


class TestGetJobById:
    """Test GET /saas/jobs/{job_id} - Get specific job by ID."""

    def test_get_job_success(self, client, auth_headers, sample_jobs):
        """Test successfully retrieving a job by ID."""
        job_id = sample_jobs['user1_job1']
        response = client.get(
            f'/saas/jobs/{job_id}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == job_id
        assert data['user_id'] == 'user_1'
        assert data['type'] == 'transcription'
        assert data['status'] == 'done'
        assert 'artifacts' in data
        assert len(data['artifacts']) == 1
        assert data['artifacts'][0]['kind'] == 'transcript'

    def test_get_job_without_auth(self, client, sample_jobs):
        """Test getting job without authentication returns 401."""
        job_id = sample_jobs['user1_job1']
        response = client.get(f'/saas/jobs/{job_id}')

        assert response.status_code == 401

    def test_get_job_not_found(self, client, auth_headers):
        """Test getting non-existent job returns 404."""
        response = client.get(
            '/saas/jobs/99999',
            headers=auth_headers['user1']
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_job_forbidden_access(self, client, auth_headers, sample_jobs):
        """Test accessing another user's job returns 403."""
        # User 1 trying to access User 2's job
        job_id = sample_jobs['user2_job1']
        response = client.get(
            f'/saas/jobs/{job_id}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Forbidden' in data['error'] or 'access' in data['error'].lower()


class TestJobModel:
    """Test Job model functionality."""

    def test_job_to_dict(self, app):
        """Test Job.to_dict() method."""
        with app.app_context():
            job = Job(
                user_id='test_user',
                type='transcription',
                status='done',
                input_ref='s3://test/file.wav'
            )
            db.session.add(job)
            db.session.commit()

            job_dict = job.to_dict()
            assert job_dict['user_id'] == 'test_user'
            assert job_dict['type'] == 'transcription'
            assert job_dict['status'] == 'done'
            assert job_dict['input_ref'] == 's3://test/file.wav'
            assert 'id' in job_dict
            assert 'created_at' in job_dict
            assert isinstance(job_dict['artifacts'], list)

    def test_job_artifact_relationship(self, app):
        """Test Job-Artifact relationship."""
        with app.app_context():
            job = Job(
                user_id='test_user',
                type='transcription',
                status='done',
                input_ref='s3://test/file.wav'
            )
            db.session.add(job)
            db.session.commit()

            # Add artifacts
            artifact1 = Artifact(
                job_id=job.id,
                kind='transcript',
                storage_ref='s3://outputs/transcript.txt'
            )
            artifact2 = Artifact(
                job_id=job.id,
                kind='srt',
                storage_ref='s3://outputs/subtitles.srt'
            )
            db.session.add_all([artifact1, artifact2])
            db.session.commit()

            # Refresh job to load artifacts
            db.session.refresh(job)

            assert len(job.artifacts) == 2
            job_dict = job.to_dict()
            assert len(job_dict['artifacts']) == 2

    def test_job_cascade_delete(self, app):
        """Test that deleting a job also deletes its artifacts."""
        with app.app_context():
            job = Job(
                user_id='test_user',
                type='transcription',
                status='done',
                input_ref='s3://test/file.wav'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Add artifact
            artifact = Artifact(
                job_id=job.id,
                kind='transcript',
                storage_ref='s3://outputs/transcript.txt'
            )
            db.session.add(artifact)
            db.session.commit()
            artifact_id = artifact.id

            # Delete job
            db.session.delete(job)
            db.session.commit()

            # Verify both job and artifact are deleted
            assert Job.query.get(job_id) is None
            assert Artifact.query.get(artifact_id) is None


class TestArtifactModel:
    """Test Artifact model functionality."""

    def test_artifact_to_dict(self, app):
        """Test Artifact.to_dict() method."""
        with app.app_context():
            job = Job(
                user_id='test_user',
                type='transcription',
                status='done',
                input_ref='s3://test/file.wav'
            )
            db.session.add(job)
            db.session.commit()

            artifact = Artifact(
                job_id=job.id,
                kind='transcript',
                storage_ref='s3://outputs/transcript.txt'
            )
            db.session.add(artifact)
            db.session.commit()

            artifact_dict = artifact.to_dict()
            assert artifact_dict['job_id'] == job.id
            assert artifact_dict['kind'] == 'transcript'
            assert artifact_dict['storage_ref'] == 's3://outputs/transcript.txt'
            assert 'id' in artifact_dict
