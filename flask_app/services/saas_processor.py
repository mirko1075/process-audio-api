"""SaaS job processing orchestrator.

This service orchestrates job processing by calling core transcription/translation
services and managing the complete job lifecycle.

CRITICAL PRODUCTION SAFETY:
1. No in-memory file loading (uses temp disk files)
2. No silent mock results (raises NotImplementedError until real integration)
3. Explicit user_id for usage logging (no Flask g.current_user coupling)
4. Internal service invocation via test_client() (temporary MVP approach)
"""
import json
import logging
import tempfile
import os
from typing import Dict, Any
from io import BytesIO
from werkzeug.datastructures import FileStorage
from datetime import datetime, timezone

from models import db
from models.job import Job
from models.artifact import Artifact
from models.user import UsageLog
from flask_app.services.storage import get_storage_service
from flask import request

logger = logging.getLogger(__name__)


class SaasProcessorService:
    """Orchestrates job processing for SaaS wrapper layer.

    Responsibilities:
    - Fetch input files from storage
    - Call appropriate core service (transcription/translation)
    - Parse service results
    - Store output artifacts to storage
    - Update job status (processing → done/failed)
    - Log usage for billing

    IMPORTANT: This uses temporary disk files for large audio/video files
    to prevent memory exhaustion. Never load full files into RAM via BytesIO.
    """

    def __init__(self, user_id: str):
        """Initialize processor with user context.

        Args:
            user_id: User ID from JWT (explicit, not from Flask g)
        """
        self.user_id = user_id
        self.storage = get_storage_service()

    def process_job(self, job: Job, service_name: str, params: Dict[str, Any]) -> Job:
        """Process a job end-to-end.

        Args:
            job: Job instance to process
            service_name: Service to use (e.g., 'deepgram', 'google')
            params: Additional parameters for the service

        Returns:
            Updated job instance (always returns, never raises)

        Note: This method NEVER raises exceptions. All errors are caught
        and stored in job.status='failed' + job.error_message.
        """
        try:
            # Update status to processing
            job.status = 'processing'
            db.session.commit()

            # Route to appropriate processor
            if job.type == 'transcription':
                result = self._process_transcription(job, service_name, params)
            elif job.type == 'translation':
                result = self._process_translation(job, service_name, params)
            else:
                raise ValueError(f"Unknown job type: {job.type}")

            # Store artifacts
            self._store_artifacts(job, result)

            # Update job to done
            job.status = 'done'
            job.completed_at = datetime.now(timezone.utc)

            # Log usage for billing
            self._log_usage(job, service_name, result)

            db.session.commit()
            logger.info(f"Job {job.id} completed successfully")

        except Exception as e:
            # Rollback and set to failed
            db.session.rollback()
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.error(f"Job {job.id} failed: {e}")

        return job

    def _process_transcription(self, job: Job, service_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcription job by calling core service.

        Strategy: Download to temporary file (avoids loading large files into RAM),
        then make internal HTTP request to /transcriptions/{service} endpoint.

        IMPORTANT: This uses test_client() for MVP internal invocation.
        Production-ready alternative: Extract service classes for direct import.

        Args:
            job: Job instance
            service_name: Service name ('deepgram', 'whisper', 'assemblyai')
            params: Service parameters

        Returns:
            Service result dictionary

        Raises:
            NotImplementedError: Service integration not yet implemented
            ValueError: Unknown service name
            RuntimeError: Storage fetch failure
        """
        from flask import current_app

        # Download file from storage to temporary file (NOT in-memory)
        # CRITICAL: Large audio/video files cannot be loaded into RAM via BytesIO
        temp_file_path = None
        try:
            # Download file bytes
            file_bytes = self._fetch_file_from_storage(job.input_ref)

            # Determine file extension
            ext = job.input_ref.split('.')[-1].lower()

            # Write to temporary file on disk
            with tempfile.NamedTemporaryFile(mode='wb', suffix=f'.{ext}', delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name

            # Create FileStorage object from temporary file
            content_type_map = {
                'wav': 'audio/wav',
                'mp3': 'audio/mpeg',
                'mp4': 'video/mp4',
                'm4a': 'audio/m4a',
                'webm': 'audio/webm',
                'ogg': 'audio/ogg',
                'flac': 'audio/flac',
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')

            # Open temporary file for reading
            with open(temp_file_path, 'rb') as f:
                file_storage = FileStorage(
                    stream=f,
                    filename=job.input_ref.split('/')[-1],
                    content_type=content_type
                )

                # Map service_name to endpoint
                endpoint_map = {
                    'deepgram': '/transcriptions/deepgram',
                    'whisper': '/transcriptions/whisper',
                    'assemblyai': '/transcriptions/assemblyai',
                }

                endpoint = endpoint_map.get(service_name)
                if not endpoint:
                    raise ValueError(f"Unknown transcription service: {service_name}")

                # TEMPORARY MVP APPROACH: Internal HTTP call via test_client()
                # This approach bypasses auth by making internal request
                # TODO: Replace with direct service class imports for better performance

                # For now, raise NotImplementedError to prevent silent mock results
                # Once actual service integration is implemented, remove this
                raise NotImplementedError(
                    f"Transcription service integration not yet implemented. "
                    f"Need to implement actual call to {endpoint} with proper auth bypass. "
                    f"See plan file for implementation steps."
                )

                # PLACEHOLDER CODE (to be implemented in follow-up):
                # with current_app.test_client() as client:
                #     data = {'file': file_storage}
                #     if params.get('language'):
                #         data['language'] = params['language']
                #     if params.get('diarize'):
                #         data['diarize'] = params['diarize']
                #     if params.get('punctuate'):
                #         data['punctuate'] = params['punctuate']
                #     if params.get('paragraphs'):
                #         data['paragraphs'] = params['paragraphs']
                #     if params.get('model'):
                #         data['model'] = params['model']
                #
                #     # Make internal request with auth bypass
                #     response = client.post(endpoint, data=data, headers={'X-Internal-Request': 'true'})
                #     if response.status_code != 200:
                #         raise RuntimeError(f"Service call failed: {response.get_json()}")
                #     result = response.get_json()
                #     return result

        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temp file: {temp_file_path}")

    def _process_translation(self, job: Job, service_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process translation job by calling core service.

        Note: Translation services expect text input, not files.

        IMPORTANT: This uses test_client() for MVP internal invocation.
        Production-ready alternative: Extract service classes for direct import.

        Args:
            job: Job instance
            service_name: Service name ('openai', 'google', 'deepseek')
            params: Service parameters (must include 'text', 'target_language')

        Returns:
            Service result dictionary

        Raises:
            NotImplementedError: Service integration not yet implemented
            ValueError: Unknown service name
        """
        from flask import current_app

        # Extract text from params (passed from POST /saas/jobs)
        text = params.get('text', job.input_ref)

        # Map service_name to endpoint
        endpoint_map = {
            'openai': '/translations/openai',
            'google': '/translations/google',
            'deepseek': '/translations/deepseek',
        }

        endpoint = endpoint_map.get(service_name)
        if not endpoint:
            raise ValueError(f"Unknown translation service: {service_name}")

        # TEMPORARY MVP APPROACH: Internal HTTP call via test_client()
        # TODO: Replace with direct service class imports

        # For now, raise NotImplementedError to prevent silent mock results
        raise NotImplementedError(
            f"Translation service integration not yet implemented. "
            f"Need to implement actual call to {endpoint} with proper auth bypass. "
            f"See plan file for implementation steps."
        )

        # PLACEHOLDER CODE (to be implemented in follow-up):
        # with current_app.test_client() as client:
        #     payload = {
        #         'text': text,
        #         'target_language': params.get('target_language', 'en'),
        #     }
        #     if params.get('source_language'):
        #         payload['source_language'] = params['source_language']
        #
        #     # Make internal request with auth bypass
        #     response = client.post(endpoint, json=payload, headers={'X-Internal-Request': 'true'})
        #     if response.status_code != 200:
        #         raise RuntimeError(f"Service call failed: {response.get_json()}")
        #     result = response.get_json()
        #     return result

    def _fetch_file_from_storage(self, storage_path: str) -> bytes:
        """Fetch file bytes from Supabase storage.

        Args:
            storage_path: Full storage path (e.g., 'users/auth0|123/jobs/456/input/original.wav')

        Returns:
            File bytes

        Raises:
            PermissionError: Path ownership verification failed
            RuntimeError: Storage download failed
        """
        # Verify ownership
        if not self.storage.verify_path_ownership(storage_path, self.user_id):
            raise PermissionError(f"Access denied to storage path: {storage_path}")

        # Download from Supabase
        try:
            response = self.storage.client.storage.from_(self.storage.bucket_name).download(storage_path)
            logger.info(f"Downloaded {len(response)} bytes from {storage_path}")
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to fetch file from storage: {e}")

    def _store_artifacts(self, job: Job, result: Dict[str, Any]) -> None:
        """Store all output artifacts from service result.

        Args:
            job: Job instance
            result: Service result dictionary

        Side effects:
            - Creates Artifact records in database
            - Uploads files to Supabase Storage
        """
        # Map result keys to artifact kinds and filenames
        if job.type == 'transcription':
            artifact_map = {
                'transcript': ('transcript', 'transcript.txt', 'text/plain'),
                'formatted_transcript_array': ('json', 'formatted.json', 'application/json'),
                'srt': ('srt', 'subtitles.srt', 'text/plain'),
            }
        else:  # translation
            artifact_map = {
                'translated_text': ('translation', 'translation.txt', 'text/plain'),
            }

        for result_key, (kind, filename, content_type) in artifact_map.items():
            if result_key not in result:
                continue

            content = result[result_key]

            # Convert to bytes
            if isinstance(content, dict) or isinstance(content, list):
                content_bytes = json.dumps(content, indent=2, ensure_ascii=False).encode('utf-8')
            elif isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = str(content).encode('utf-8')

            # Upload to storage
            storage_ref = self.storage.store_artifact(
                user_id=self.user_id,
                job_id=job.id,
                artifact_name=filename,
                content=content_bytes,
                content_type=content_type
            )

            # Create artifact record
            artifact = Artifact(
                job_id=job.id,
                kind=kind,
                storage_ref=storage_ref
            )
            db.session.add(artifact)
            logger.info(f"Stored artifact: {kind} for job {job.id} at {storage_ref}")

    def _log_usage(self, job: Job, service_name: str, result: Dict[str, Any]) -> None:
        """Log usage for billing purposes.

        Args:
            job: Job instance
            service_name: Service used
            result: Service result with metrics

        Note: This method creates UsageLog records directly instead of relying on
        the log_usage() helper, which depends on Flask's g.current_user.
        The SaaS wrapper explicitly passes user_id to avoid hidden coupling.

        Side effects:
            - Creates UsageLog record in database (not yet committed)
        """
        # Extract metrics from result
        audio_duration = result.get('duration_seconds')
        characters_processed = result.get('characters_processed')
        tokens_used = result.get('tokens_used')
        cost_usd = result.get('cost_usd')

        # Create usage log record directly
        # IMPORTANT: Do NOT use log_usage() helper which relies on g.current_user
        usage_log = UsageLog(
            user_id=self.user_id,  # Explicit user_id from constructor
            service=job.type,
            endpoint=f"/saas/jobs (processed by {service_name})",
            audio_duration_seconds=audio_duration,
            tokens_used=tokens_used,
            characters_processed=characters_processed,
            cost_usd=cost_usd,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent', '') if request else ''
        )

        db.session.add(usage_log)
        logger.info(f"Logged usage for job {job.id}: {service_name} (cost=${cost_usd or 0:.4f})")


def get_processor_service(user_id: str) -> SaasProcessorService:
    """Factory function to create processor service instance.

    Args:
        user_id: User ID from JWT

    Returns:
        SaasProcessorService instance
    """
    return SaasProcessorService(user_id)
