"""Custom exception classes used across the service."""


class ServiceError(RuntimeError):
    """Base class for domain-specific exceptions."""


class TranscriptionError(ServiceError):
    """Raised when audio transcription fails."""


class TranslationError(ServiceError):
    """Raised when translation fails."""


class InvalidRequestError(ServiceError):
    """Raised when request validation fails."""


class ProcessingError(ServiceError):
    """Raised when video/audio processing fails."""


class ConfigurationError(ServiceError):
    """Raised when user configuration is missing or invalid - SaaS specific."""
