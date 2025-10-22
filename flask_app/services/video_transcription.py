"""Video transcription service using Whisper with video processing capabilities."""

import logging
from typing import Dict, Any, Optional
from werkzeug.datastructures import FileStorage

from flask_app.clients.video_processor import get_video_processor
from utils.exceptions import TranscriptionError

logger = logging.getLogger(__name__)


class VideoTranscriptionService:
    """Service for transcribing videos from URLs or files."""
    
    def __init__(self):
        """Initialize the video transcription service."""
        self.video_processor = get_video_processor()
        logger.info("Video transcription service initialized")
    
    def transcribe_from_url(self, video_url: str, language: Optional[str] = None,
                           model_size: str = "base") -> Dict[str, Any]:
        """Transcribe video from URL using Whisper.
        
        Args:
            video_url: URL of the video to transcribe
            language: Language code (None for auto-detect)
            model_size: Whisper model size
            
        Returns:
            Transcription result with video metadata
        """
        try:
            logger.info(f"Starting video URL transcription (model: {model_size}, language: {language or 'auto'})")
            
            # Validate URL
            if not video_url or not video_url.strip():
                raise TranscriptionError("Video URL cannot be empty")
            
            # Validate model size
            valid_models = ["tiny", "base", "small", "medium", "large"]
            if model_size not in valid_models:
                raise TranscriptionError(f"Invalid model size. Must be one of: {', '.join(valid_models)}")
            
            # Process video URL
            result = self.video_processor.process_video_url(
                video_url=video_url.strip(),
                language=language,
                model_size=model_size
            )
            
            # Format response for API consistency
            formatted_result = self._format_response(result)
            
            logger.info("Video URL transcription completed successfully")
            return formatted_result
            
        except TranscriptionError:
            # Re-raise our custom errors
            raise
        except Exception as exc:
            logger.error(f"Video URL transcription failed: {exc}")
            raise TranscriptionError(f"Video URL transcription failed: {str(exc)}") from exc
    
    def transcribe_from_file(self, video_file: FileStorage, language: Optional[str] = None,
                            model_size: str = "base") -> Dict[str, Any]:
        """Transcribe uploaded video file using Whisper.
        
        Args:
            video_file: Uploaded video file
            language: Language code (None for auto-detect)
            model_size: Whisper model size
            
        Returns:
            Transcription result with file metadata
        """
        try:
            logger.info(f"Starting video file transcription (model: {model_size}, language: {language or 'auto'})")
            
            # Validate file
            if not video_file or video_file.filename == '':
                raise TranscriptionError("No video file provided")
            
            # Validate model size
            valid_models = ["tiny", "base", "small", "medium", "large"]
            if model_size not in valid_models:
                raise TranscriptionError(f"Invalid model size. Must be one of: {', '.join(valid_models)}")
            
            # Read file data
            video_data = video_file.read()
            if not video_data:
                raise TranscriptionError("Video file is empty")
            
            # Validate file size (limit to 100MB for uploaded files)
            max_size = 100 * 1024 * 1024  # 100MB
            if len(video_data) > max_size:
                raise TranscriptionError(f"Video file too large. Maximum size: {max_size // (1024*1024)}MB")
            
            # Process video file
            result = self.video_processor.process_video_file(
                video_data=video_data,
                filename=video_file.filename,
                language=language,
                model_size=model_size
            )
            
            # Format response for API consistency
            formatted_result = self._format_response(result)
            
            logger.info("Video file transcription completed successfully")
            return formatted_result
            
        except TranscriptionError:
            # Re-raise our custom errors
            raise
        except Exception as exc:
            logger.error(f"Video file transcription failed: {exc}")
            raise TranscriptionError(f"Video file transcription failed: {str(exc)}") from exc
    
    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the transcription result for API response.
        
        Args:
            result: Raw transcription result from video processor
            
        Returns:
            Formatted API response
        """
        # Base response structure
        formatted = {
            "transcript": result.get("transcript", ""),
            "confidence": result.get("confidence", 0.0),
            "detected_language": result.get("detected_language", "unknown"),
            "model": result.get("model", "whisper"),
            "service": "whisper-video",
            "word_count": result.get("word_count", 0),
            "transcription_time": result.get("transcription_time", 0.0)
        }
        
        # Add source-specific metadata
        if result.get("source") == "video_url":
            formatted.update({
                "source": "video_url",
                "video_url": result.get("video_url"),
                "video_title": result.get("video_title"),
                "video_duration": result.get("video_duration", 0),
                "video_uploader": result.get("video_uploader")
            })
        elif result.get("source") == "video_file":
            formatted.update({
                "source": "video_file",
                "filename": result.get("filename"),
                "file_size": result.get("file_size", 0),
                "video_duration": result.get("video_duration", 0)
            })
        
        # Add segments if available
        if "segments" in result:
            formatted["segments"] = result["segments"]
        
        # Add formatted transcript array for consistency with other endpoints
        if result.get("transcript"):
            # Split transcript into sentences for formatted array
            import re
            sentences = re.split(r'[.!?]+', result["transcript"])
            formatted["formatted_transcript_array"] = [
                {"text": sentence.strip()} 
                for sentence in sentences 
                if sentence.strip()
            ]
        else:
            formatted["formatted_transcript_array"] = []
        
        return formatted