"""Supabase Storage service for SaaS file uploads and artifact management."""
import os
import logging
from typing import BinaryIO, Optional
from supabase import create_client, Client
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)


class SupabaseStorageService:
    """Service for managing file storage in Supabase Storage.

    Responsibilities:
    - Upload input files (audio/video/text)
    - Store output artifacts (transcripts, translations, SRT, JSON)
    - Generate short-lived signed URLs for downloads

    Path structure:
    - users/{user_id}/jobs/{job_id}/input/original.{ext}
    - users/{user_id}/jobs/{job_id}/output/{artifact_name}.{ext}
    """

    def __init__(self):
        """Initialize Supabase client with service role key (backend-only access)."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.bucket_name = os.getenv('SUPABASE_STORAGE_BUCKET', 'saas-files')

        # Configuration
        self.max_upload_size_mb = int(os.getenv('MAX_UPLOAD_SIZE_MB', '100'))
        self.allowed_upload_types = os.getenv(
            'ALLOWED_UPLOAD_TYPES',
            'audio/mpeg,audio/wav,audio/webm,audio/ogg,audio/m4a,audio/flac,'
            'video/mp4,video/webm,video/quicktime,video/x-msvideo,'
            'text/plain,application/json'
        ).split(',')
        self.signed_url_ttl_seconds = int(os.getenv('SIGNED_URL_TTL_SECONDS', '300'))

        # Validate required env vars
        if not self.supabase_url:
            raise RuntimeError("SUPABASE_URL environment variable is required")
        if not self.supabase_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

        # Initialize Supabase client
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"Supabase Storage initialized (bucket: {self.bucket_name})")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Supabase initialization failed: {e}")

    def upload_input(
        self,
        user_id: str,
        job_id: int,
        file: FileStorage,
        original_filename: str
    ) -> str:
        """Upload input file to Supabase Storage.

        Args:
            user_id: User ID from JWT (e.g., 'auth0|123')
            job_id: Job ID from database
            file: File upload from request
            original_filename: Original filename with extension

        Returns:
            str: Storage path (e.g., 'users/auth0|123/jobs/456/input/original.wav')

        Raises:
            ValueError: If file is too large or invalid type
            RuntimeError: If upload fails
        """
        # Validate file size
        file.seek(0, os.SEEK_END)
        file_size_bytes = file.tell()
        file.seek(0)  # Reset to beginning

        max_size_bytes = self.max_upload_size_mb * 1024 * 1024
        if file_size_bytes > max_size_bytes:
            raise ValueError(
                f"File size ({file_size_bytes / 1024 / 1024:.2f}MB) exceeds "
                f"maximum allowed ({self.max_upload_size_mb}MB)"
            )

        # Validate content type
        content_type = file.content_type
        if content_type not in self.allowed_upload_types:
            raise ValueError(
                f"File type '{content_type}' not allowed. "
                f"Allowed types: {', '.join(self.allowed_upload_types)}"
            )

        # Extract file extension from original filename
        ext = os.path.splitext(original_filename)[1] or ''

        # Construct storage path
        # Path: users/{user_id}/jobs/{job_id}/input/original.{ext}
        storage_path = f"users/{user_id}/jobs/{job_id}/input/original{ext}"

        try:
            # Upload to Supabase Storage
            file_bytes = file.read()

            response = self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )

            logger.info(
                f"Uploaded input file: {storage_path} "
                f"({file_size_bytes / 1024:.2f}KB, {content_type})"
            )

            return storage_path

        except Exception as e:
            logger.error(f"Failed to upload input file: {e}")
            raise RuntimeError(f"Storage upload failed: {e}")

    def store_artifact(
        self,
        user_id: str,
        job_id: int,
        artifact_name: str,
        content: bytes,
        content_type: str = 'text/plain'
    ) -> str:
        """Store output artifact to Supabase Storage.

        Args:
            user_id: User ID from JWT
            job_id: Job ID from database
            artifact_name: Filename for artifact (e.g., 'transcript.txt', 'result.json')
            content: File content as bytes
            content_type: MIME type (default: text/plain)

        Returns:
            str: Storage path (e.g., 'users/auth0|123/jobs/456/output/transcript.txt')

        Raises:
            RuntimeError: If upload fails
        """
        # Construct storage path
        # Path: users/{user_id}/jobs/{job_id}/output/{artifact_name}
        storage_path = f"users/{user_id}/jobs/{job_id}/output/{artifact_name}"

        try:
            response = self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": content_type}
            )

            logger.info(
                f"Stored artifact: {storage_path} "
                f"({len(content) / 1024:.2f}KB, {content_type})"
            )

            return storage_path

        except Exception as e:
            logger.error(f"Failed to store artifact: {e}")
            raise RuntimeError(f"Artifact storage failed: {e}")

    def generate_signed_url(self, storage_path: str) -> str:
        """Generate short-lived signed URL for downloading a file.

        Args:
            storage_path: Full path in storage (e.g., 'users/auth0|123/jobs/456/output/transcript.txt')

        Returns:
            str: Signed URL valid for SIGNED_URL_TTL_SECONDS (default: 5 minutes)

        Raises:
            RuntimeError: If URL generation fails
        """
        try:
            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=storage_path,
                expires_in=self.signed_url_ttl_seconds
            )

            # The response should contain 'signedURL' key
            if isinstance(response, dict) and 'signedURL' in response:
                signed_url = response['signedURL']
            else:
                # Fallback if response structure is different
                signed_url = str(response)

            logger.info(f"Generated signed URL for: {storage_path} (TTL: {self.signed_url_ttl_seconds}s)")

            return signed_url

        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise RuntimeError(f"Signed URL generation failed: {e}")

    def verify_path_ownership(self, storage_path: str, user_id: str) -> bool:
        """Verify that a storage path belongs to the specified user.

        Ownership is enforced by path structure: users/{user_id}/...

        Args:
            storage_path: Full storage path
            user_id: User ID to verify against

        Returns:
            bool: True if path belongs to user, False otherwise
        """
        expected_prefix = f"users/{user_id}/"
        return storage_path.startswith(expected_prefix)


def get_storage_service() -> SupabaseStorageService:
    """Get singleton instance of SupabaseStorageService.

    Returns:
        SupabaseStorageService instance

    Raises:
        RuntimeError: If required environment variables are missing
    """
    if not hasattr(get_storage_service, '_instance'):
        get_storage_service._instance = SupabaseStorageService()
    return get_storage_service._instance
