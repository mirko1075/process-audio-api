"""Deepgram API client for transcription services."""
import logging
from typing import Dict, Any, Union
from functools import lru_cache

from deepgram import DeepgramClient as DGClient, PrerecordedOptions, FileSource
from utils.config import get_app_config
from utils.exceptions import TranscriptionError


logger = logging.getLogger(__name__)


class DeepgramClient:
    """Client for Deepgram Nova-2 transcription API."""
    
    def __init__(self):
        config = get_app_config()
        if not config.deepgram.api_key:
            raise TranscriptionError("Deepgram API key not configured")
            
        self._client = DGClient(config.deepgram.api_key)
        logger.info("Deepgram client initialized successfully")
    
    def transcribe(self, audio_data: bytes, language: str = 'en', 
                  model: str = 'nova-2') -> Dict[str, Any]:
        """Transcribe audio using Deepgram Nova-2 model.
        
        Args:
            audio_data: Raw audio file bytes
            language: Language code for transcription
            model: Deepgram model to use
            
        Returns:
            Formatted transcription result
        """
        logger.info(f"Starting Deepgram transcription with model {model}, language {language}")
        
        try:
            # Configure transcription options
            options = PrerecordedOptions(
                model=model,
                language=language,
                smart_format=True,
                punctuate=True,
                paragraphs=True,
                utterances=True,
                keywords=['medical', 'doctor', 'patient', 'diagnosis', 'treatment']
            )
            
            # Create file source from bytes
            payload = FileSource(audio_data)
            
            # Perform transcription
            response = self._client.listen.prerecorded.v('1').transcribe_file(
                payload, options
            )
            
            # Format and return result
            result = self._format_transcript(response)
            
            logger.info(f"Deepgram transcription completed: {len(result['transcript'])} characters")
            return result
            
        except Exception as exc:
            logger.error(f"Deepgram API error: {exc}")
            raise TranscriptionError(f"Deepgram transcription failed: {str(exc)}") from exc
    
    def _format_transcript(self, response) -> Dict[str, Any]:
        """Format Deepgram response into standardized format.
        
        Args:
            response: Deepgram API response object
            
        Returns:
            Formatted transcription result
        """
        try:
            # Handle both response object and dict formats
            if hasattr(response, 'results'):
                results = response.results
            else:
                results = response.get('results', {})
            
            # Extract transcript text
            channels = results.get('channels', [])
            if not channels:
                return {"transcript": "", "confidence": 0.0}
            
            alternatives = channels[0].get('alternatives', [])
            if not alternatives:
                return {"transcript": "", "confidence": 0.0}
            
            # Get the best alternative
            best_alternative = alternatives[0]
            transcript = best_alternative.get('transcript', '')
            confidence = best_alternative.get('confidence', 0.0)
            
            # Extract additional metadata
            metadata = self._extract_metadata(results)
            
            return {
                "transcript": transcript,
                "confidence": confidence,
                "language": results.get('language', 'en'),
                "model": "nova-2",
                "service": "deepgram",
                **metadata
            }
            
        except Exception as exc:
            logger.error(f"Error formatting Deepgram response: {exc}")
            raise TranscriptionError(f"Failed to format Deepgram response: {str(exc)}") from exc
    
    def _extract_metadata(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract additional metadata from Deepgram response."""
        metadata = {}
        
        try:
            # Get audio duration and word count
            channels = results.get('channels', [])
            if channels:
                alternatives = channels[0].get('alternatives', [])
                if alternatives:
                    words = alternatives[0].get('words', [])
                    metadata['word_count'] = len(words)
                    
                    if words:
                        # Calculate duration from first to last word
                        start_time = words[0].get('start', 0)
                        end_time = words[-1].get('end', 0)
                        metadata['duration_seconds'] = end_time - start_time
        except Exception as exc:
            logger.warning(f"Could not extract metadata: {exc}")
        
        return metadata


@lru_cache(maxsize=1)
def get_deepgram_client() -> DeepgramClient:
    """Get cached Deepgram client instance."""
    return DeepgramClient()