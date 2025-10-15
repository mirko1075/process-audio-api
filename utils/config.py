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
class AppConfig:
    api_key: str
    deepgram: DeepgramSettings
    openai: OpenAISettings
    assemblyai: Optional[AssemblyAISettings] = None
    google_cloud: Optional[GoogleCloudSettings] = None
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
        allowed_origins=tuple(
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        ),
    )
