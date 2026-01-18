"""Tests for STEP 4: API SaaS Wrapper Layer.

Tests cover the four main endpoints with service processing:
- POST /saas/jobs (with service parameter and processing)
- GET /saas/jobs (lightweight list, filters deleted)
- GET /saas/jobs/{id} (metadata-only, filters deleted)
- DELETE /saas/jobs/{id} (soft delete)
"""
import pytest
import io
from unittest.mock import patch, MagicMock
from flask_jwt_extended import create_access_token
from models import db
from models.job import Job
from models.artifact import Artifact


@pytest.fixture
def auth_headers(app):
    """Create JWT tokens for test users."""
    with app.app_context():
        user1_token = create_access_token(identity='user_1')
        user2_token = create_access_token(identity='user_2')

    return {
        'user1': {'Authorization': f'Bearer {user1_token}'},
        'user2': {'Authorization': f'Bearer {user2_token}'}
    }


@pytest.fixture
def sample_jobs_step4(app):
    """Create sample jobs for STEP 4 testing."""
    with app.app_context():
        # User 1 jobs
        job1 = Job(
            user_id='user_1',
            type='transcription',
            status='done',
            input_ref='users/user_1/jobs/1/input/original.wav'
        )
        job2 = Job(
            user_id='user_1',
            type='translation',
            status='queued',
            input_ref='users/user_1/jobs/2/input/original.txt'
        )
        job3 = Job(
            user_id='user_1',
            type='transcription',
            status='deleted',  # Soft deleted
            input_ref='users/user_1/jobs/3/input/original.wav'
        )

        # User 2 jobs
        job4 = Job(
            user_id='user_2',
            type='transcription',
            status='done',
            input_ref='users/user_2/jobs/4/input/original.wav'
        )

        db.session.add_all([job1, job2, job3, job4])
        db.session.commit()

        # Add artifact to job1 for metadata testing
        artifact1 = Artifact(
            job_id=job1.id,
            kind='transcript',
            storage_ref='users/user_1/jobs/1/output/transcript.txt'
        )
        db.session.add(artifact1)
        db.session.commit()

        return {
            'user1_job1': job1.id,  # done
            'user1_job2': job2.id,  # queued
            'user1_job3': job3.id,  # deleted
            'user2_job1': job4.id,  # user2's job
        }


class TestJobModelMethods:
    """Test new Job model methods added in STEP 4."""

    def test_to_dict_minimal(self, app, sample_jobs_step4):
        """Test to_dict_minimal() returns only 5 fields."""
        with app.app_context():
            job = Job.query.get(sample_jobs_step4['user1_job1'])
            minimal_dict = job.to_dict_minimal()

            # Verify only minimal fields present
            assert set(minimal_dict.keys()) == {'id', 'type', 'status', 'fileName', 'created_at'}
            assert minimal_dict['id'] == job.id
            assert minimal_dict['type'] == 'transcription'
            assert minimal_dict['status'] == 'done'
            assert minimal_dict['fileName'] == 'original.wav'
            assert minimal_dict['created_at'] is not None

    def test_to_dict_metadata(self, app, sample_jobs_step4):
        """Test to_dict_metadata() returns metadata with artifacts but no content."""
        with app.app_context():
            job = Job.query.get(sample_jobs_step4['user1_job1'])
            metadata_dict = job.to_dict_metadata()

            # Verify all job fields present
            assert 'id' in metadata_dict
            assert 'user_id' in metadata_dict
            assert 'type' in metadata_dict
            assert 'status' in metadata_dict
            assert 'input_ref' in metadata_dict
            assert 'error_message' in metadata_dict
            assert 'created_at' in metadata_dict
            assert 'completed_at' in metadata_dict
            assert 'artifacts' in metadata_dict

            # Verify artifacts are included as metadata
            assert len(metadata_dict['artifacts']) == 1
            assert metadata_dict['artifacts'][0]['kind'] == 'transcript'
            assert 'storage_ref' in metadata_dict['artifacts'][0]


class TestPostJobsWithService:
    """Test POST /saas/jobs with service parameter (STEP 4)."""

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_transcription_job_missing_service(self, mock_storage, client, auth_headers):
        """POST /saas/jobs without service parameter should return 400."""
        mock_storage_instance = MagicMock()
        mock_storage_instance.upload_input.return_value = 'users/user_1/jobs/1/input/test.wav'
        mock_storage.return_value = mock_storage_instance

        data = {
            'type': 'transcription',
            'file': (io.BytesIO(b'fake audio'), 'test.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        assert 'service' in response.get_json()['error'].lower()

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_transcription_job_invalid_service(self, mock_storage, client, auth_headers):
        """POST /saas/jobs with invalid service should return 400."""
        mock_storage_instance = MagicMock()
        mock_storage_instance.upload_input.return_value = 'users/user_1/jobs/1/input/test.wav'
        mock_storage.return_value = mock_storage_instance

        data = {
            'type': 'transcription',
            'service': 'invalid_service',
            'file': (io.BytesIO(b'fake audio'), 'test.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'Invalid transcription service' in response_data['error']
        assert 'deepgram' in response_data['error']
        assert 'whisper' in response_data['error']
        assert 'assemblyai' in response_data['error']

    @patch('flask_app.api.saas_jobs.get_storage_service')
    def test_create_transcription_job_with_deepgram_service(self, mock_storage, client, auth_headers, app):
        """POST /saas/jobs with deepgram service processes job (fails with NotImplementedError)."""
        mock_storage_instance = MagicMock()
        mock_storage_instance.upload_input.return_value = 'users/user_1/jobs/1/input/test.wav'
        mock_storage.return_value = mock_storage_instance

        data = {
            'type': 'transcription',
            'service': 'deepgram',
            'language': 'en',
            'diarize': 'true',
            'file': (io.BytesIO(b'fake audio'), 'test.wav')
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        response_data = response.get_json()

        # Job should be created and processed (fails due to NotImplementedError)
        assert response_data['type'] == 'transcription'
        assert response_data['status'] == 'failed'  # NotImplementedError causes failure
        assert 'not yet implemented' in response_data['error_message'].lower()

    def test_create_translation_job_missing_text(self, client, auth_headers):
        """POST /saas/jobs translation without text should return 400."""
        data = {
            'type': 'translation',
            'service': 'google',
            'target_language': 'es'
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json=data
        )

        assert response.status_code == 400
        assert 'text' in response.get_json()['error'].lower()

    def test_create_translation_job_missing_target_language(self, client, auth_headers):
        """POST /saas/jobs translation without target_language should return 400."""
        data = {
            'type': 'translation',
            'service': 'google',
            'text': 'Hello world'
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json=data
        )

        assert response.status_code == 400
        assert 'target_language' in response.get_json()['error'].lower()

    def test_create_translation_job_invalid_service(self, client, auth_headers):
        """POST /saas/jobs translation with invalid service should return 400."""
        data = {
            'type': 'translation',
            'service': 'invalid_service',
            'text': 'Hello world',
            'target_language': 'es'
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json=data
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'Invalid translation service' in response_data['error']
        assert 'openai' in response_data['error']
        assert 'google' in response_data['error']
        assert 'deepseek' in response_data['error']

    def test_create_translation_job_with_google_service(self, client, auth_headers):
        """POST /saas/jobs with google service processes job (fails with NotImplementedError)."""
        data = {
            'type': 'translation',
            'service': 'google',
            'text': 'Hello world',
            'target_language': 'es',
            'source_language': 'en'
        }

        response = client.post(
            '/saas/jobs',
            headers=auth_headers['user1'],
            json=data
        )

        assert response.status_code == 201
        response_data = response.get_json()

        # Job should be created and processed (fails due to NotImplementedError)
        assert response_data['type'] == 'translation'
        assert response_data['status'] == 'failed'  # NotImplementedError causes failure
        assert 'not yet implemented' in response_data['error_message'].lower()


class TestListJobsLightweight:
    """Test GET /saas/jobs returns lightweight data and filters deleted."""

    def test_list_jobs_uses_minimal_response(self, client, auth_headers, sample_jobs_step4):
        """GET /saas/jobs should return minimal fields only."""
        response = client.get(
            '/saas/jobs',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should have at least one job
        assert len(data['jobs']) > 0

        # Verify minimal fields only
        for job in data['jobs']:
            assert set(job.keys()) == {'id', 'type', 'status', 'fileName', 'created_at'}
            assert 'user_id' not in job
            assert 'input_ref' not in job
            assert 'artifacts' not in job

    def test_list_jobs_excludes_deleted(self, client, auth_headers, sample_jobs_step4):
        """GET /saas/jobs should not include deleted jobs."""
        response = client.get(
            '/saas/jobs',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()

        # User 1 has 2 active jobs (job1='done', job2='queued') and 1 deleted (job3)
        assert data['total'] == 2
        assert len(data['jobs']) == 2

        # Verify deleted job is not in list
        job_ids = [job['id'] for job in data['jobs']]
        assert sample_jobs_step4['user1_job3'] not in job_ids
        assert sample_jobs_step4['user1_job1'] in job_ids
        assert sample_jobs_step4['user1_job2'] in job_ids

    def test_list_jobs_status_filter_works(self, client, auth_headers, sample_jobs_step4):
        """GET /saas/jobs with status filter should work correctly."""
        response = client.get(
            '/saas/jobs?status=done',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()

        # Only job1 has status='done'
        assert data['total'] == 1
        assert data['jobs'][0]['status'] == 'done'


class TestGetJobMetadata:
    """Test GET /saas/jobs/{id} returns metadata-only and filters deleted."""

    def test_get_job_uses_metadata_response(self, client, auth_headers, sample_jobs_step4):
        """GET /saas/jobs/{id} should return metadata with artifacts but no content."""
        response = client.get(
            f'/saas/jobs/{sample_jobs_step4["user1_job1"]}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify all metadata fields present
        assert 'id' in data
        assert 'user_id' in data
        assert 'type' in data
        assert 'status' in data
        assert 'input_ref' in data
        assert 'error_message' in data
        assert 'created_at' in data
        assert 'completed_at' in data
        assert 'artifacts' in data

        # Verify artifacts are metadata-only (no content)
        assert len(data['artifacts']) == 1
        assert data['artifacts'][0]['kind'] == 'transcript'
        assert 'storage_ref' in data['artifacts'][0]
        # No 'content' field should exist
        assert 'content' not in data['artifacts'][0]

    def test_get_deleted_job_returns_404(self, client, auth_headers, sample_jobs_step4):
        """GET /saas/jobs/{id} for deleted job should return 404."""
        response = client.get(
            f'/saas/jobs/{sample_jobs_step4["user1_job3"]}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 404
        assert 'not found' in response.get_json()['error'].lower()

    def test_get_other_user_job_returns_403(self, client, auth_headers, sample_jobs_step4):
        """GET /saas/jobs/{id} for another user's job should return 403."""
        # User 1 trying to access User 2's job
        response = client.get(
            f'/saas/jobs/{sample_jobs_step4["user2_job1"]}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 403
        assert 'Forbidden' in response.get_json()['error']


class TestDeleteJob:
    """Test DELETE /saas/jobs/{id} soft deletion."""

    def test_delete_job_success(self, client, auth_headers, sample_jobs_step4, app):
        """DELETE /saas/jobs/{id} should soft delete job."""
        job_id = sample_jobs_step4['user1_job2']

        response = client.delete(
            f'/saas/jobs/{job_id}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Job deleted successfully'
        assert data['job_id'] == job_id

        # Verify job status is 'deleted' in database
        with app.app_context():
            job = Job.query.get(job_id)
            assert job.status == 'deleted'

    def test_delete_job_idempotent(self, client, auth_headers, sample_jobs_step4):
        """DELETE /saas/jobs/{id} should be idempotent (safe to call twice)."""
        job_id = sample_jobs_step4['user1_job2']

        # First delete
        response1 = client.delete(
            f'/saas/jobs/{job_id}',
            headers=auth_headers['user1']
        )
        assert response1.status_code == 200

        # Second delete (should still return success)
        response2 = client.delete(
            f'/saas/jobs/{job_id}',
            headers=auth_headers['user1']
        )
        assert response2.status_code == 200
        assert response2.get_json()['message'] == 'Job deleted successfully'

    def test_delete_other_user_job_returns_403(self, client, auth_headers, sample_jobs_step4):
        """DELETE /saas/jobs/{id} for another user's job should return 403."""
        # User 1 trying to delete User 2's job
        response = client.delete(
            f'/saas/jobs/{sample_jobs_step4["user2_job1"]}',
            headers=auth_headers['user1']
        )

        assert response.status_code == 403
        assert 'Forbidden' in response.get_json()['error']

    def test_delete_nonexistent_job_returns_404(self, client, auth_headers):
        """DELETE /saas/jobs/{id} for non-existent job should return 404."""
        response = client.delete(
            '/saas/jobs/99999',
            headers=auth_headers['user1']
        )

        assert response.status_code == 404
        assert 'not found' in response.get_json()['error'].lower()

    def test_deleted_job_excluded_from_list(self, client, auth_headers, sample_jobs_step4):
        """After DELETE, job should be excluded from GET /saas/jobs."""
        job_id = sample_jobs_step4['user1_job1']

        # Delete job
        delete_response = client.delete(
            f'/saas/jobs/{job_id}',
            headers=auth_headers['user1']
        )
        assert delete_response.status_code == 200

        # List jobs
        list_response = client.get(
            '/saas/jobs',
            headers=auth_headers['user1']
        )
        assert list_response.status_code == 200

        # Verify deleted job not in list
        jobs_data = list_response.get_json()
        job_ids = [job['id'] for job in jobs_data['jobs']]
        assert job_id not in job_ids
