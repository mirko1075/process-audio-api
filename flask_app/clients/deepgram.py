"""Deepgram API client for transcription services."""
import logging
from typing import Dict, Any
from functools import lru_cache

from deepgram import (
    DeepgramClient as DGClient, 
    PrerecordedOptions
)
from utils.config import get_app_config
from utils.exceptions import TranscriptionError


logger = logging.getLogger(__name__)


class DeepgramClient:
    """Client for Deepgram Nova-2 transcription API."""
    
    def __init__(self):
        config = get_app_config()
        if not config.deepgram.api_key:
            raise TranscriptionError("Deepgram API key not configured")
            
        try:
            self._client = DGClient(config.deepgram.api_key)
            logger.info("Deepgram client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}")
            raise TranscriptionError(f"Deepgram client initialization failed: {str(e)}")
    
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
            # Configure transcription options with explicit typing
            options = PrerecordedOptions(
                model=model,
                language=language,
                smart_format=True,
                punctuate=True,
                paragraphs=True,
                utterances=True,
                keywords=['medical', 'doctor', 'patient', 'diagnosis', 'treatment']
            )
            
            # Create file source from bytes - use dict format for v3.10+
            payload = {"buffer": audio_data}
            
            # Perform transcription with error handling
            logger.debug("Sending transcription request to Deepgram API")
            
            # Use the updated API call format for v3.10+
            response = self._client.listen.rest.v("1").transcribe_file(
                payload, options
            )
            
            # Check if response is valid
            if not response:
                raise TranscriptionError("Empty response from Deepgram API")
            
            # Format and return result
            result = self._format_transcript(response)
            
            logger.info(f"Deepgram transcription completed: {len(result['transcript'])} characters")
            return result
            
        except TranscriptionError:
            # Re-raise our custom errors
            raise
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
            # Handle both response object and dict formats more safely
            if hasattr(response, 'results'):
                results = response.results
            elif hasattr(response, 'get'):
                results = response.get('results', {})
            else:
                logger.error(f"Unexpected response format: {type(response)}")
                raise TranscriptionError("Invalid response format from Deepgram")
            
            # Convert to dict if it's an object
            if hasattr(results, 'to_dict'):
                results = results.to_dict()
            elif hasattr(results, '__dict__'):
                results = results.__dict__
            
            # Extract transcript text
            channels = results.get('channels', [])
            if not channels:
                logger.warning("No channels found in Deepgram response")
                return {"transcript": "", "confidence": 0.0}
            
            alternatives = channels[0].get('alternatives', [])
            if not alternatives:
                logger.warning("No alternatives found in Deepgram response")
                return {"transcript": "", "confidence": 0.0}
            
            # Get the best alternative
            best_alternative = alternatives[0]
            transcript = best_alternative.get('transcript', '')
            confidence = best_alternative.get('confidence', 0.0)
            
            # Extract additional metadata safely
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
            raise TranscriptionError(f"Error formatting Deepgram response: {exc}")  from exc
    
            raise TranscriptionError(f"Error formatting Deepgram response: {exc}") from exc
        """Extract additional metadata from Deepgram response.
        
        Args:
            results: Deepgram results dictionary
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {}
        
        try:
            # Handle results conversion to dict if needed
            if hasattr(results, 'to_dict'):
                results_dict = results.to_dict()
            elif hasattr(results, '__dict__'):
                results_dict = results.__dict__
            else:
                results_dict = results
            
            # Extract basic metadata
            metadata_section = results_dict.get('metadata', {})
            if metadata_section:
                if hasattr(metadata_section, 'to_dict'):
                    metadata_section = metadata_section.to_dict()
                elif hasattr(metadata_section, '__dict__'):
                    metadata_section = metadata_section.__dict__
                
                metadata.update({
                    "duration": metadata_section.get('duration'),
                    "channels": metadata_section.get('channels'),
                    "model_info": metadata_section.get('model_info', {}),
                    "request_id": metadata_section.get('request_id')
                })
            
            # Extract channels metadata
            channels = results_dict.get('channels', [])
            if channels and len(channels) > 0:
                channel = channels[0]
                if hasattr(channel, 'to_dict'):
                    channel = channel.to_dict()
                elif hasattr(channel, '__dict__'):
                    channel = channel.__dict__
                
                alternatives = channel.get('alternatives', [])
                if alternatives and len(alternatives) > 0:
                    alternative = alternatives[0]
                    if hasattr(alternative, 'to_dict'):
                        alternative = alternative.to_dict()
                    elif hasattr(alternative, '__dict__'):
                        alternative = alternative.__dict__
                    
                    words = alternative.get('words', [])
                    if words:
                        # Convert word objects to dicts and extract timing info
                        word_list = []
                        for word in words:
                            if hasattr(word, 'to_dict'):
                                word_dict = word.to_dict()
                            elif hasattr(word, '__dict__'):
                                word_dict = word.__dict__
                            else:
                                word_dict = word
                            word_list.append(word_dict)
                        
                        metadata['word_count'] = len(word_list)
                        metadata['words'] = word_list
                        
                        # Calculate duration from first to last word
                        if word_list:
                            start_time = word_list[0].get('start', 0)
                            end_time = word_list[-1].get('end', 0)
                            metadata['duration_seconds'] = end_time - start_time
                
                # Extract language detection info
                metadata.update({
                    "detected_language": channel.get('detected_language'),
                    "language_confidence": channel.get('language_confidence')
                })

                return metadata
            
        except Exception as exc:
            logger.warning(f"Could not extract metadata: {exc}")
        
        return metadata


@lru_cache(maxsize=1)
def get_deepgram_client() -> DeepgramClient:
    """Get cached Deepgram client instance."""
    return DeepgramClient()