"""Video processing client for URL and file-based video transcription."""

import os
import tempfile
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO
from functools import lru_cache

import yt_dlp
import whisper
from pydub import AudioSegment

from utils.config import get_app_config
from utils.exceptions import TranscriptionError

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Client for processing videos from URLs or files for transcription."""
    
    def __init__(self):
        """Initialize the video processor."""
        self._whisper_model = None
        self._model_size = "base"  # Default model size
        
    def process_video_url(self, video_url: str, language: Optional[str] = None, 
                         model_size: str = "base") -> Dict[str, Any]:
        """Process video from URL (YouTube, etc.) and transcribe.
        
        Args:
            video_url: URL of the video to process
            language: Language code for transcription (None for auto-detect)
            model_size: Whisper model size (tiny, base, small, medium, large)
            
        Returns:
            Transcription result with metadata
        """
        audio_file = None
        try:
            logger.info(f"Starting video URL processing: {video_url}")
            
            # Try to get metadata first (lighter operation)
            metadata = self._get_video_metadata(video_url)
            if metadata.get('metadata_error'):
                logger.warning(f"Metadata extraction had issues: {metadata['metadata_error']}")
            
            # Download audio from video URL
            audio_file = self._download_audio_from_url(video_url)
            
            # Transcribe audio
            result = self._transcribe_audio_file(audio_file, language, model_size)
            
            # Add metadata to result
            result.update({
                "source": "video_url",
                "video_url": video_url,
                "metadata": metadata,
                "video_duration": metadata.get('duration', result.get('duration_seconds', 0))
            })
            
            logger.info(f"Video URL processing completed: {len(result['transcript'])} characters")
            return result
            
        except TranscriptionError as e:
            # Add helpful suggestions for common YouTube issues
            error_msg = str(e)
            if "Video download blocked by YouTube" in error_msg:
                enhanced_msg = f"{error_msg}\n\n🔧 Troubleshooting steps:\n"
                enhanced_msg += "1. Update yt-dlp: ./scripts/update_ytdlp.sh\n"
                enhanced_msg += "2. Try a different video URL\n"
                enhanced_msg += "3. Upload the video file directly instead\n"
                enhanced_msg += "4. Check if video is publicly accessible\n\n"
                enhanced_msg += "📁 Alternative: Use file upload endpoint:\n"
                enhanced_msg += "POST /transcriptions/video with 'video' file field"
                raise TranscriptionError(enhanced_msg)
            else:
                raise
        except Exception as exc:
            logger.error(f"Video URL processing failed: {exc}")
            raise TranscriptionError(f"Video processing failed: {str(exc)}") from exc
        finally:
            # Cleanup temporary audio file
            if audio_file and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                    logger.debug(f"Cleaned up temporary audio file: {audio_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup audio file: {e}")
    
    def process_video_file(self, video_data: bytes, filename: str,
                          language: Optional[str] = None, model_size: str = "base") -> Dict[str, Any]:
        """Process uploaded video file and transcribe.
        
        Args:
            video_data: Raw video file bytes
            filename: Original filename
            language: Language code for transcription (None for auto-detect)
            model_size: Whisper model size
            
        Returns:
            Transcription result with metadata
        """
        video_file = None
        audio_file = None
        try:
            logger.info(f"Starting video file processing: {filename}")
            
            # Save video data to temporary file
            video_file = self._save_video_data(video_data, filename)
            
            # Extract audio from video file
            audio_file = self._extract_audio_from_video(video_file)
            
            # Transcribe audio
            result = self._transcribe_audio_file(audio_file, language, model_size)
            
            # Add file metadata to result
            result.update({
                "source": "video_file",
                "filename": filename,
                "file_size": len(video_data),
                "video_duration": self._get_audio_duration(audio_file)
            })
            
            logger.info(f"Video file processing completed: {len(result['transcript'])} characters")
            return result
            
        except Exception as exc:
            logger.error(f"Video file processing failed: {exc}")
            raise TranscriptionError(f"Video file processing failed: {str(exc)}") from exc
        finally:
            # Cleanup temporary files
            for temp_file in [video_file, audio_file]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug(f"Cleaned up temporary file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup file: {e}")
    
    def _download_audio_from_url(self, video_url: str) -> str:
        """Download audio from video URL using yt-dlp.
        
        Args:
            video_url: URL of the video
            
        Returns:
            Path to the downloaded audio file
        """
        # Create unique temporary filename
        temp_name = f"video_audio_{uuid.uuid4().hex[:8]}"
        output_path = os.path.join(tempfile.gettempdir(), temp_name)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            # Add more robust options for YouTube
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': '192',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {
                'http': lambda n: min(4 ** n, 60),
                'fragment': lambda n: min(4 ** n, 60),
                'extractor': lambda n: min(4 ** n, 60),
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.debug("Downloading audio from video URL")
                ydl.download([video_url])
                
            # yt-dlp adds .mp3 extension automatically
            audio_file = output_path + ".mp3"
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file not found after download: {audio_file}")
                
            return audio_file
            
        except yt_dlp.DownloadError as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                raise TranscriptionError(
                    "Video download blocked by YouTube. This can happen due to:\n"
                    "1. Video has restricted access\n"
                    "2. Geographic restrictions\n" 
                    "3. YouTube's anti-bot measures\n"
                    "4. Video requires login\n\n"
                    "Try: Updating yt-dlp, using a different video, or uploading the video file directly."
                )
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise TranscriptionError("Video not found. Please check the URL is correct and the video is publicly accessible.")
            else:
                raise TranscriptionError(f"Failed to download video: {str(e)}")
        except Exception as e:
            raise TranscriptionError(f"Unexpected error during download: {str(e)}")
    
    def _get_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """Get metadata from video URL without downloading.
        
        Args:
            video_url: URL of the video
            
        Returns:
            Video metadata dictionary
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_retries': 2,
            'retry_sleep_functions': {
                'extractor': lambda n: min(2 ** n, 30),
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", "Unknown"),
                    "view_count": info.get("view_count", 0),
                    "upload_date": info.get("upload_date", "Unknown")
                }
        except Exception as e:
            logger.warning(f"Failed to get video metadata: {e}")
            return {
                "title": "Unknown",
                "duration": 0,
                "uploader": "Unknown",
                "view_count": 0,
                "upload_date": "Unknown",
                "metadata_error": str(e)
            }
    
    def _save_video_data(self, video_data: bytes, filename: str) -> str:
        """Save video data to temporary file.
        
        Args:
            video_data: Raw video file bytes
            filename: Original filename for extension
            
        Returns:
            Path to the temporary video file
        """
        # Get file extension from original filename
        file_ext = Path(filename).suffix or '.mp4'
        
        # Create temporary file
        temp_name = f"upload_video_{uuid.uuid4().hex[:8]}{file_ext}"
        temp_path = os.path.join(tempfile.gettempdir(), temp_name)
        
        try:
            with open(temp_path, 'wb') as f:
                f.write(video_data)
            return temp_path
        except Exception as e:
            raise TranscriptionError(f"Failed to save video data: {str(e)}")
    
    def _extract_audio_from_video(self, video_file: str) -> str:
        """Extract audio from video file using pydub.
        
        Args:
            video_file: Path to the video file
            
        Returns:
            Path to the extracted audio file
        """
        try:
            # Create temporary audio file path
            audio_file = video_file.rsplit('.', 1)[0] + '_audio.mp3'
            
            # Extract audio using pydub
            logger.debug("Extracting audio from video file")
            video = AudioSegment.from_file(video_file)
            video.export(audio_file, format="mp3", bitrate="192k")
            
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio extraction failed: {audio_file}")
                
            return audio_file
            
        except Exception as e:
            raise TranscriptionError(f"Failed to extract audio from video: {str(e)}")
    
    def _get_audio_duration(self, audio_file: str) -> float:
        """Get audio duration in seconds.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            audio = AudioSegment.from_file(audio_file)
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 0.0
    
    def _transcribe_audio_file(self, audio_file: str, language: Optional[str] = None,
                              model_size: str = "base") -> Dict[str, Any]:
        """Transcribe audio file using Whisper.
        
        Args:
            audio_file: Path to the audio file
            language: Language code (None for auto-detect)
            model_size: Whisper model size
            
        Returns:
            Transcription result with metadata
        """
        try:
            # Load Whisper model
            if self._whisper_model is None or self._model_size != model_size:
                logger.info(f"Loading Whisper model: {model_size}")
                start_time = time.time()
                self._whisper_model = whisper.load_model(model_size)
                self._model_size = model_size
                load_time = time.time() - start_time
                logger.info(f"Whisper model loaded in {load_time:.1f} seconds")
            
            # Perform transcription
            logger.info("Starting Whisper transcription")
            transcribe_start = time.time()
            
            # Set up transcription options
            options = {"verbose": False}
            if language:
                options["language"] = language
            
            result = self._whisper_model.transcribe(audio_file, **options)
            transcribe_time = time.time() - transcribe_start
            
            logger.info(f"Whisper transcription completed in {transcribe_time:.1f} seconds")
            
            if not result or 'text' not in result:
                raise TranscriptionError("Whisper transcription produced no results")
            
            # Extract detected language if auto-detected
            detected_language = result.get('language', language or 'unknown')
            
            # Format result
            formatted_result = {
                "transcript": result["text"].strip(),
                "confidence": self._calculate_average_confidence(result),
                "detected_language": detected_language,
                "model": f"whisper-{model_size}",
                "service": "whisper",
                "transcription_time": transcribe_time,
                "word_count": len(result["text"].split()),
                "segments": self._format_segments(result.get("segments", []))
            }
            
            return formatted_result
            
        except Exception as e:
            raise TranscriptionError(f"Whisper transcription failed: {str(e)}")
    
    def _calculate_average_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate average confidence from Whisper segments.
        
        Args:
            result: Whisper transcription result
            
        Returns:
            Average confidence score (0.0-1.0)
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.0
        
        total_confidence = 0.0
        total_duration = 0.0
        
        for segment in segments:
            if "avg_logprob" in segment and "end" in segment and "start" in segment:
                duration = segment["end"] - segment["start"]
                # Convert log probability to confidence (approximate)
                confidence = max(0.0, min(1.0, (segment["avg_logprob"] + 1.0)))
                total_confidence += confidence * duration
                total_duration += duration
        
        return total_confidence / total_duration if total_duration > 0 else 0.0
    
    def _format_segments(self, segments: list) -> list:
        """Format Whisper segments for response.
        
        Args:
            segments: Raw Whisper segments
            
        Returns:
            Formatted segments list
        """
        formatted_segments = []
        for segment in segments:
            formatted_segment = {
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "text": segment.get("text", "").strip(),
            }
            if "avg_logprob" in segment:
                formatted_segment["confidence"] = max(0.0, min(1.0, (segment["avg_logprob"] + 1.0)))
            formatted_segments.append(formatted_segment)
        
        return formatted_segments


@lru_cache(maxsize=1)
def get_video_processor() -> VideoProcessor:
    """Get cached video processor instance."""
    return VideoProcessor()