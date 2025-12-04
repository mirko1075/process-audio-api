"""Deepgram API client for transcription services."""
import logging
from typing import Dict, Any, List
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
                  model: str = 'nova-2', diarize: bool = False, 
                  punctuate: bool = True, paragraphs: bool = False) -> Dict[str, Any]:
        """Transcribe audio using Deepgram Nova-2 model with enhanced options.
        
        Args:
            audio_data: Raw audio file bytes
            language: Language code for transcription
            model: Deepgram model to use
            diarize: Enable speaker diarization (identifies different speakers)
            punctuate: Enable smart punctuation
            paragraphs: Enable paragraph detection
            
        Returns:
            Formatted transcription result with optional diarization data
        """
        logger.info(f"Starting Deepgram transcription: model={model}, language={language}, diarize={diarize}")
        
        try:
            # Configure transcription options with diarization support
            options = PrerecordedOptions(
                model=model,
                language=language,
                smart_format=True,
                punctuate=punctuate,
                paragraphs=paragraphs,
                utterances=diarize,  # Enable utterance boundaries when diarizing
                diarize=diarize,     # Speaker diarization
                alternatives=1,
                keywords=['medical', 'doctor', 'patient', 'diagnosis', 'treatment'] if not diarize else None
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
            result = self._format_transcript(response, diarize)
            
            logger.info(f"Deepgram transcription completed: {len(result['transcript'])} characters, diarize={diarize}")
            return result
            
        except TranscriptionError:
            # Re-raise our custom errors
            raise
        except Exception as exc:
            logger.error(f"Deepgram API error: {exc}")
            raise TranscriptionError(f"Deepgram transcription failed: {str(exc)}") from exc
    
    def _format_transcript(self, response, diarize: bool = False) -> Dict[str, Any]:
        """Format Deepgram response into standardized format with diarization support.
        
        Args:
            response: Deepgram API response object
            diarize: Whether diarization was enabled
            
        Returns:
            Formatted transcription result with optional speaker data
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
            
            # Build base response
            response_data = {
                "transcript": transcript,
                "confidence": confidence,
                "language": results.get('language', 'en'),
                "model": "nova-2",
                "service": "deepgram",
                **metadata
            }
            
            # Add diarization data if enabled
            if diarize:
                diarization_data = self._process_diarization(best_alternative, metadata.get('words', []))
                if diarization_data:
                    response_data["diarization"] = diarization_data
            
            # Add paragraphs if available
            paragraphs = best_alternative.get('paragraphs')
            if paragraphs:
                response_data["paragraphs"] = self._process_paragraphs(paragraphs)
            
            return response_data
            
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
    
    def _process_diarization(self, alternative: Dict[str, Any], words: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process speaker diarization data from Deepgram response.
        
        Args:
            alternative: The best alternative from Deepgram response
            words: List of word objects with speaker information
            
        Returns:
            Structured diarization data with speaker segments and statistics
        """
        try:
            if not words:
                logger.warning("No words available for diarization processing")
                return {"error": "No word-level data available for speaker detection"}
            
            speakers = {}
            speaker_segments = []
            current_speaker = None
            current_text = []
            start_time = None
            prev_end = 0
            
            for word_info in words:
                speaker = word_info.get('speaker', 0)
                word = word_info.get('word', '')
                word_start = word_info.get('start', 0)
                word_end = word_info.get('end', 0)
                word_confidence = word_info.get('confidence', 0.0)
                
                # Initialize speaker stats
                if speaker not in speakers:
                    speakers[speaker] = {
                        "speaker_id": f"Speaker_{speaker}",
                        "total_words": 0,
                        "total_duration": 0.0,
                        "average_confidence": 0.0,
                        "confidence_sum": 0.0
                    }
                
                # Update speaker statistics
                speakers[speaker]["total_words"] += 1
                speakers[speaker]["confidence_sum"] += word_confidence
                speakers[speaker]["average_confidence"] = (
                    speakers[speaker]["confidence_sum"] / speakers[speaker]["total_words"]
                )
                
                # Build speaker segments
                if current_speaker != speaker:
                    # Save previous segment
                    if current_speaker is not None and current_text:
                        segment_text = " ".join(current_text).strip()
                        segment_duration = prev_end - start_time if start_time else 0
                        
                        speaker_segments.append({
                            "speaker": f"Speaker_{current_speaker}",
                            "speaker_id": current_speaker,
                            "text": segment_text,
                            "start_time": start_time,
                            "end_time": prev_end,
                            "duration": round(segment_duration, 2),
                            "word_count": len(current_text)
                        })
                        
                        # Update speaker total duration
                        speakers[current_speaker]["total_duration"] += segment_duration
                    
                    # Start new segment
                    current_speaker = speaker
                    current_text = [word]
                    start_time = word_start
                else:
                    current_text.append(word)
                
                prev_end = word_end
            
            # Add final segment
            if current_speaker is not None and current_text:
                segment_text = " ".join(current_text).strip()
                segment_duration = prev_end - start_time if start_time else 0
                
                speaker_segments.append({
                    "speaker": f"Speaker_{current_speaker}",
                    "speaker_id": current_speaker,
                    "text": segment_text,
                    "start_time": start_time,
                    "end_time": prev_end,
                    "duration": round(segment_duration, 2),
                    "word_count": len(current_text)
                })
                
                speakers[current_speaker]["total_duration"] += segment_duration
            
            # Format speaker statistics
            speaker_stats = []
            for speaker_id, stats in speakers.items():
                speaker_stats.append({
                    "speaker_id": f"Speaker_{speaker_id}",
                    "total_words": stats["total_words"],
                    "total_duration": round(stats["total_duration"], 2),
                    "average_confidence": round(stats["average_confidence"], 3),
                    "speaking_percentage": round(
                        (stats["total_duration"] / max(prev_end, 1)) * 100, 1
                    ) if prev_end > 0 else 0.0
                })
            
            return {
                "speakers_detected": len(speakers),
                "total_duration": round(prev_end, 2),
                "speakers": speaker_stats,
                "segments": speaker_segments
            }
            
        except Exception as e:
            logger.error(f"Error processing diarization: {str(e)}")
            return {"error": f"Failed to process speaker diarization: {str(e)}"}
    
    def _process_paragraphs(self, paragraphs) -> List[Dict[str, Any]]:
        """Process paragraph data from Deepgram response.
        
        Args:
            paragraphs: Paragraphs data from Deepgram response
            
        Returns:
            List of formatted paragraph objects
        """
        try:
            if not paragraphs:
                return []
            
            # Handle different response formats
            if hasattr(paragraphs, 'to_dict'):
                paragraphs = paragraphs.to_dict()
            elif hasattr(paragraphs, '__dict__'):
                paragraphs = paragraphs.__dict__
            
            # Extract paragraph transcripts
            paragraph_transcripts = paragraphs.get('transcript', [])
            if not paragraph_transcripts:
                return []
            
            formatted_paragraphs = []
            for i, para in enumerate(paragraph_transcripts):
                if hasattr(para, 'to_dict'):
                    para_dict = para.to_dict()
                elif hasattr(para, '__dict__'):
                    para_dict = para.__dict__
                else:
                    para_dict = para
                
                formatted_paragraphs.append({
                    "paragraph_id": i + 1,
                    "text": para_dict.get('text', ''),
                    "start_time": para_dict.get('start', 0),
                    "end_time": para_dict.get('end', 0),
                    "duration": round((para_dict.get('end', 0) - para_dict.get('start', 0)), 2),
                    "word_count": len(para_dict.get('text', '').split()) if para_dict.get('text') else 0
                })
            
            return formatted_paragraphs
            
        except Exception as e:
            logger.error(f"Error processing paragraphs: {str(e)}")
            return []

    def _extract_metadata(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from Deepgram results.
        
        Args:
            results: Deepgram API response results
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            metadata = {}
            
            # Extract channel information
            channels = results.get('channels', [])
            if channels and len(channels) > 0:
                channel = channels[0]
                alternatives = channel.get('alternatives', [])
                if alternatives and len(alternatives) > 0:
                    alternative = alternatives[0]
                    
                    # Extract words for diarization
                    words = alternative.get('words', [])
                    metadata['words'] = words
                    
                    # Extract timing information
                    if words:
                        metadata['duration'] = words[-1].get('end', 0.0) if words else 0.0
                    
                    # Extract detected language
                    detected_language = alternative.get('detected_language')
                    if detected_language:
                        metadata['detected_language'] = detected_language
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {}


@lru_cache(maxsize=1)
def get_deepgram_client() -> DeepgramClient:
    """Get cached Deepgram client instance."""
    return DeepgramClient()