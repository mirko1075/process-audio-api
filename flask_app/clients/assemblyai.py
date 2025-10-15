"""AssemblyAI API client for transcription services."""
import logging
import time
from typing import Dict, Any
from functools import lru_cache

import assemblyai as aai
from utils.config import get_app_config
from utils.exceptions import TranscriptionError


logger = logging.getLogger(__name__)


class AssemblyAIClient:
    """Client for AssemblyAI transcription API."""
    
    def __init__(self):
        config = get_app_config()
        if not config.assemblyai.api_key:
            raise TranscriptionError("AssemblyAI API key not configured")
            
        aai.settings.api_key = config.assemblyai.api_key
        self._transcriber = aai.Transcriber()
        logger.info("AssemblyAI client initialized successfully")
    
    def transcribe(self, audio_path: str, language: str = 'en') -> Dict[str, Any]:
        """Transcribe audio file using AssemblyAI.
        
        Args:
            audio_path: Path to audio file
            language: Language code for transcription
            
        Returns:
            Formatted transcription result
        """
        logger.info(f"Starting AssemblyAI transcription for {audio_path}")
        
        try:
            # Configure transcription settings
            config = aai.TranscriptionConfig(
                language_code=language,
                punctuate=True,
                format_text=True,
                speaker_labels=True,
                auto_highlights=True
            )
            
            # Start transcription
            transcript = self._transcriber.transcribe(audio_path, config=config)
            
            # Wait for completion
            while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
                time.sleep(1)
                logger.debug("Waiting for AssemblyAI transcription to complete...")
            
            if transcript.status == aai.TranscriptStatus.error:
                raise TranscriptionError(f"AssemblyAI transcription failed: {transcript.error}")
            
            # Format result
            result = self._format_transcript(transcript)
            
            logger.info(f"AssemblyAI transcription completed: {len(result['transcript'])} characters")
            return result
            
        except Exception as exc:
            logger.error(f"AssemblyAI API error: {exc}")
            raise TranscriptionError(f"AssemblyAI transcription failed: {str(exc)}") from exc
    
    def _format_transcript(self, transcript) -> Dict[str, Any]:
        """Format AssemblyAI transcript into standardized format."""
        try:
            result = {
                "transcript": transcript.text or "",
                "confidence": transcript.confidence or 0.0,
                "language": "en",  # AssemblyAI returns language code
                "model": "assemblyai",
                "service": "assemblyai"
            }
            
            # Add speaker information if available
            if hasattr(transcript, 'utterances') and transcript.utterances:
                result["speakers"] = len(set(u.speaker for u in transcript.utterances))
            
            # Add highlights if available
            if hasattr(transcript, 'auto_highlights') and transcript.auto_highlights:
                result["highlights"] = [h.text for h in transcript.auto_highlights.results]
            
            return result
            
        except Exception as exc:
            logger.error(f"Error formatting AssemblyAI response: {exc}")
            raise TranscriptionError(f"Failed to format AssemblyAI response: {str(exc)}") from exc


@lru_cache(maxsize=1)
def get_assemblyai_client() -> AssemblyAIClient:
    """Get cached AssemblyAI client instance."""
    return AssemblyAIClient()