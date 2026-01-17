"""Tests for SaaS Jobs API endpoints."""
import pytest
import io
from unittest.mock import patch, MagicMock
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


class TestFileUpload:
    """Test POST /saas/jobs with file upload (multipart/form-data mode)."""

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_job_with_file_upload_success(self, mock_get_storage, client, auth_headers):
        """Test successfully creating a job with file upload."""
        # Mock storage service
        mock_storage = MagicMock()
        mock_storage.upload_input.return_value = 'users/user_1/jobs/1/input/original.wav'
        mock_get_storage.return_value = mock_storage

        # Create a fake audio file
        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake audio content'), 'test_audio.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        response_data = response.get_json()

        # Verify job created
        assert response_data['type'] == 'transcription'
        assert response_data['status'] == 'queued'
        assert response_data['user_id'] == 'user_1'
        assert response_data['input_ref'] == 'users/user_1/jobs/1/input/original.wav'
        assert 'id' in response_data

        # Verify upload_input was called
        mock_storage.upload_input.assert_called_once()
        call_args = mock_storage.upload_input.call_args
        assert call_args[1]['user_id'] == 'user_1'
        assert call_args[1]['original_filename'] == 'test_audio.wav'

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_job_with_file_upload_translation(self, mock_get_storage, client, auth_headers):
        """Test creating a translation job with file upload."""
        # Mock storage service
        mock_storage = MagicMock()
        mock_storage.upload_input.return_value = 'users/user_1/jobs/1/input/original.txt'
        mock_get_storage.return_value = mock_storage

        data = {
            'type': 'translation',
            'file': (io.BytesIO(b'fake text content'), 'document.txt')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        response_data = response.get_json()
        assert response_data['type'] == 'translation'
        assert response_data['input_ref'] == 'users/user_1/jobs/1/input/original.txt'

    def test_create_job_file_upload_missing_type(self, client, auth_headers):
        """Test file upload without type field returns 400."""
        data = {
            'file': (io.BytesIO(b'fake audio content'), 'test_audio.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'type' in response_data['error']

    def test_create_job_file_upload_missing_file(self, client, auth_headers):
        """Test file upload without file returns 400."""
        data = {'type': 'transcription'}

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'file' in response_data['error'].lower()

    def test_create_job_file_upload_empty_filename(self, client, auth_headers):
        """Test file upload with empty filename returns 400."""
        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake audio content'), '')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'file' in response_data['error'].lower() or 'selected' in response_data['error'].lower()

    def test_create_job_file_upload_invalid_type(self, client, auth_headers):
        """Test file upload with invalid job type returns 400."""
        data = {
            'type': 'invalid_type',
            'file': (io.BytesIO(b'fake audio content'), 'test_audio.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'transcription' in response_data['error'] or 'translation' in response_data['error']

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_job_file_too_large(self, mock_get_storage, client, auth_headers):
        """Test file upload with file too large returns 400."""
        # Mock storage service to raise ValueError for file too large
        mock_storage = MagicMock()
        mock_storage.upload_input.side_effect = ValueError('File size (150.00MB) exceeds maximum allowed (100MB)')
        mock_get_storage.return_value = mock_storage

        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake large file'), 'large_audio.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert '150' in response_data['error'] or 'exceeds' in response_data['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_job_invalid_content_type(self, mock_get_storage, client, auth_headers):
        """Test file upload with invalid content type returns 400."""
        # Mock storage service to raise ValueError for invalid content type
        mock_storage = MagicMock()
        mock_storage.upload_input.side_effect = ValueError("File type 'application/exe' not allowed")
        mock_get_storage.return_value = mock_storage

        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake file'), 'malware.exe')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'not allowed' in response_data['error'].lower() or 'exe' in response_data['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_job_storage_upload_failure(self, mock_get_storage, client, auth_headers):
        """Test file upload with storage failure returns 500."""
        # Mock storage service to raise RuntimeError for storage failure
        mock_storage = MagicMock()
        mock_storage.upload_input.side_effect = RuntimeError('Supabase Storage connection failed')
        mock_get_storage.return_value = mock_storage

        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake audio content'), 'test_audio.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 500
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'upload failed' in response_data['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_job_unexpected_error(self, mock_get_storage, client, auth_headers):
        """Test file upload with unexpected error returns 500."""
        # Mock storage service to raise unexpected exception
        mock_storage = MagicMock()
        mock_storage.upload_input.side_effect = Exception('Unexpected database error')
        mock_get_storage.return_value = mock_storage

        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake audio content'), 'test_audio.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 500
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'internal server error' in response_data['error'].lower()

    def test_create_job_invalid_content_type_header(self, client, auth_headers):
        """Test creating job with invalid Content-Type returns 400."""
        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data='plain text data',
            content_type='text/plain'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data
        assert 'Content-Type' in response_data['error'] or 'application/json' in response_data['error']


class TestGetJobArtifacts:
    """Test GET /saas/jobs/{job_id}/artifacts - Get artifacts for a job."""

    def test_get_artifacts_success(self, client, auth_headers, sample_jobs):
        """Test successfully retrieving artifacts for a job."""
        job_id = sample_jobs['user1_job1']

        response = client.get(
            f'/saas/jobs/{job_id}/artifacts',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'job_id' in data
        assert 'artifacts' in data
        assert data['job_id'] == job_id

        # Verify artifacts list
        artifacts = data['artifacts']
        assert len(artifacts) == 1
        assert artifacts[0]['kind'] == 'transcript'
        assert artifacts[0]['storage_ref'] == 's3://bucket/outputs/transcript1.txt'
        assert 'id' in artifacts[0]
        assert 'job_id' in artifacts[0]

    def test_get_artifacts_empty_list(self, client, auth_headers, sample_jobs):
        """Test retrieving artifacts for job with no artifacts."""
        job_id = sample_jobs['user1_job2']  # Job with no artifacts

        response = client.get(
            f'/saas/jobs/{job_id}/artifacts',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['job_id'] == job_id
        assert data['artifacts'] == []

    def test_get_artifacts_without_auth(self, client, sample_jobs):
        """Test getting artifacts without authentication returns 401."""
        job_id = sample_jobs['user1_job1']

        response = client.get(f'/saas/jobs/{job_id}/artifacts')

        assert response.status_code == 401

    def test_get_artifacts_job_not_found(self, client, auth_headers):
        """Test getting artifacts for non-existent job returns 404."""
        response = client.get(
            '/saas/jobs/99999/artifacts',
            headers=auth_headers['user1']
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_artifacts_forbidden_access(self, client, auth_headers, sample_jobs):
        """Test accessing another user's job artifacts returns 403."""
        # User 1 trying to access User 2's job artifacts
        job_id = sample_jobs['user2_job1']

        response = client.get(
            f'/saas/jobs/{job_id}/artifacts',
            headers=auth_headers['user1']
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Forbidden' in data['error'] or 'access' in data['error'].lower()

    def test_get_artifacts_multiple_artifacts(self, app, client, auth_headers, sample_jobs):
        """Test retrieving multiple artifacts for a job."""
        job_id = sample_jobs['user1_job1']

        # Add more artifacts to the job
        with app.app_context():
            artifact2 = Artifact(
                job_id=job_id,
                kind='srt',
                storage_ref='users/user_1/jobs/1/output/subtitles.srt'
            )
            artifact3 = Artifact(
                job_id=job_id,
                kind='json',
                storage_ref='users/user_1/jobs/1/output/metadata.json'
            )
            db.session.add_all([artifact2, artifact3])
            db.session.commit()

        response = client.get(
            f'/saas/jobs/{job_id}/artifacts',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['artifacts']) == 3

        # Verify all artifact kinds are present
        kinds = {artifact['kind'] for artifact in data['artifacts']}
        assert kinds == {'transcript', 'srt', 'json'}


class TestDownloadArtifact:
    """Test GET /saas/artifacts/{artifact_id}/download - Download artifact via signed URL."""

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_download_artifact_success(self, mock_get_storage, client, auth_headers, sample_jobs, app):
        """Test successfully generating download URL for artifact."""
        # Mock storage service
        mock_storage = MagicMock()
        mock_storage.verify_path_ownership.return_value = True
        mock_storage.generate_signed_url.return_value = 'https://supabase.co/storage/signed-url-abc123?expires=300'
        mock_storage.signed_url_ttl_seconds = 300
        mock_get_storage.return_value = mock_storage

        # Get artifact ID from sample_jobs
        with app.app_context():
            job_id = sample_jobs['user1_job1']
            artifact = Artifact.query.filter_by(job_id=job_id).first()
            artifact_id = artifact.id

        response = client.get(
            f'/saas/artifacts/{artifact_id}/download',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'artifact_id' in data
        assert 'job_id' in data
        assert 'kind' in data
        assert 'download_url' in data
        assert 'expires_in_seconds' in data

        assert data['artifact_id'] == artifact_id
        assert data['kind'] == 'transcript'
        assert data['download_url'] == 'https://supabase.co/storage/signed-url-abc123?expires=300'
        assert data['expires_in_seconds'] == 300

        # Verify mocks were called
        mock_storage.verify_path_ownership.assert_called_once()
        mock_storage.generate_signed_url.assert_called_once()

    def test_download_artifact_without_auth(self, client, app, sample_jobs):
        """Test downloading artifact without authentication returns 401."""
        with app.app_context():
            job_id = sample_jobs['user1_job1']
            artifact = Artifact.query.filter_by(job_id=job_id).first()
            artifact_id = artifact.id

        response = client.get(f'/saas/artifacts/{artifact_id}/download')

        assert response.status_code == 401

    def test_download_artifact_not_found(self, client, auth_headers):
        """Test downloading non-existent artifact returns 404."""
        response = client.get(
            '/saas/artifacts/99999/download',
            headers=auth_headers['user1']
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_download_artifact_forbidden_access(self, mock_get_storage, client, auth_headers, sample_jobs, app):
        """Test accessing another user's artifact returns 403."""
        # Mock storage service
        mock_storage = MagicMock()
        mock_storage.verify_path_ownership.return_value = True
        mock_get_storage.return_value = mock_storage

        # User 1 trying to access User 2's artifact
        with app.app_context():
            # Create artifact for user 2's job
            job_id = sample_jobs['user2_job1']
            artifact = Artifact(
                job_id=job_id,
                kind='transcript',
                storage_ref='users/user_2/jobs/3/output/transcript.txt'
            )
            db.session.add(artifact)
            db.session.commit()
            artifact_id = artifact.id

        response = client.get(
            f'/saas/artifacts/{artifact_id}/download',
            headers=auth_headers['user1']
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Forbidden' in data['error'] or 'access' in data['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_download_artifact_path_ownership_mismatch(self, mock_get_storage, client, auth_headers, sample_jobs, app):
        """Test downloading artifact with path ownership mismatch returns 403."""
        # Mock storage service with path ownership verification failing
        mock_storage = MagicMock()
        mock_storage.verify_path_ownership.return_value = False
        mock_get_storage.return_value = mock_storage

        with app.app_context():
            job_id = sample_jobs['user1_job1']
            artifact = Artifact.query.filter_by(job_id=job_id).first()
            artifact_id = artifact.id

        response = client.get(
            f'/saas/artifacts/{artifact_id}/download',
            headers=auth_headers['user1']
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Forbidden' in data['error'] or 'Invalid storage path' in data['error']

        # Verify verify_path_ownership was called
        mock_storage.verify_path_ownership.assert_called_once()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_download_artifact_signed_url_failure(self, mock_get_storage, client, auth_headers, sample_jobs, app):
        """Test downloading artifact with signed URL generation failure returns 500."""
        # Mock storage service with signed URL generation failure
        mock_storage = MagicMock()
        mock_storage.verify_path_ownership.return_value = True
        mock_storage.generate_signed_url.side_effect = RuntimeError('Supabase Storage connection failed')
        mock_get_storage.return_value = mock_storage

        with app.app_context():
            job_id = sample_jobs['user1_job1']
            artifact = Artifact.query.filter_by(job_id=job_id).first()
            artifact_id = artifact.id

        response = client.get(
            f'/saas/artifacts/{artifact_id}/download',
            headers=auth_headers['user1']
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Failed to generate download URL' in data['error'] or 'download URL' in data['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_download_artifact_unexpected_error(self, mock_get_storage, client, auth_headers, sample_jobs, app):
        """Test downloading artifact with unexpected error returns 500."""
        # Mock storage service with unexpected exception
        mock_storage = MagicMock()
        mock_storage.verify_path_ownership.return_value = True
        mock_storage.generate_signed_url.side_effect = Exception('Unexpected error')
        mock_get_storage.return_value = mock_storage

        with app.app_context():
            job_id = sample_jobs['user1_job1']
            artifact = Artifact.query.filter_by(job_id=job_id).first()
            artifact_id = artifact.id

        response = client.get(
            f'/saas/artifacts/{artifact_id}/download',
            headers=auth_headers['user1']
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Internal server error' in data['error'] or 'internal' in data['error'].lower()
