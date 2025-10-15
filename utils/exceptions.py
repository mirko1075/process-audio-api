"""Custom exception classes used across the service."""


class ServiceError(RuntimeError):
    """Base class for domain-specific exceptions."""


class TranscriptionError(ServiceError):
    """Raised when audio transcription fails."""


class TranslationError(ServiceError):
    """Raised when translation fails."""
