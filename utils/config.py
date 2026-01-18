"""Application configuration utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class DeepgramSettings:
    api_key: str
    model: str = "nova-2"
    language: str = "en"


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str
    model: str = "gpt-4o-mini"


@dataclass(frozen=True)
class AssemblyAISettings:
    api_key: str
    upload_url: str = "https://api.assemblyai.com/v2/upload"
    transcript_url: str = "https://api.assemblyai.com/v2/transcript"


@dataclass(frozen=True)
class GoogleCloudSettings:
    credentials_path: str


@dataclass(frozen=True)
class SupabaseSettings:
    """Supabase Storage configuration for SaaS file uploads."""
    url: str
    service_role_key: str
    storage_bucket: str = "saas-files"
    max_upload_size_mb: int = 100
    signed_url_ttl_seconds: int = 300
    allowed_upload_types: tuple[str, ...] = field(default_factory=lambda: (
        'audio/mpeg', 'audio/wav', 'audio/webm', 'audio/ogg', 'audio/m4a', 'audio/flac',
        'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo',
        'text/plain', 'application/json'
    ))


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    deepgram: DeepgramSettings
    openai: OpenAISettings
    assemblyai: Optional[AssemblyAISettings] = None
    google_cloud: Optional[GoogleCloudSettings] = None
    supabase: Optional[SupabaseSettings] = None
    allowed_origins: tuple[str, ...] = field(default_factory=lambda: ("*",))


@lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    missing = [
        name
        for name in ("API_KEY", "DEEPGRAM_API_KEY", "OPENAI_API_KEY")
        if not os.getenv(name)
    ]
    if missing:
        raise ValueError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
    google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # Supabase Storage (optional - will fail fast in storage service if used without config)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    return AppConfig(
        api_key=os.environ["API_KEY"],
        deepgram=DeepgramSettings(
            api_key=os.environ["DEEPGRAM_API_KEY"],
            model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
            language=os.getenv("DEEPGRAM_LANGUAGE", "en"),
        ),
        openai=OpenAISettings(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ),
        assemblyai=(
            AssemblyAISettings(api_key=assemblyai_key)
            if assemblyai_key
            else None
        ),
        google_cloud=(
            GoogleCloudSettings(credentials_path=google_credentials)
            if google_credentials
            else None
        ),
        supabase=(
            SupabaseSettings(
                url=supabase_url,
                service_role_key=supabase_key,
                storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "saas-files"),
                max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "100")),
                signed_url_ttl_seconds=int(os.getenv("SIGNED_URL_TTL_SECONDS", "300")),
            )
            if supabase_url and supabase_key
            else None
        ),
        allowed_origins=tuple(
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        ),
    )
