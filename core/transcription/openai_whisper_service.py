"""OpenAI Whisper transcription utilities with automatic chunking for large files."""
from __future__ import annotations

import logging
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List
import math
import io

import openai
from openai import AuthenticationError, APIError, RateLimitError
from pydub import AudioSegment

from utils.config import get_app_config
from utils.exceptions import TranscriptionError


class WhisperTranscriber:
    def __init__(self) -> None:
        config = get_app_config()
        self._client = openai.OpenAI(api_key=config.openai.api_key)
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Chunking configuration
        self.max_file_size_mb = 20  # More conservative limit with 5MB buffer
        self.max_file_size_bytes = self.max_file_size_mb * 1024 * 1024
        self.chunk_length_minutes = 5  # Smaller chunks for high-quality audio
        self.target_chunk_size_mb = 15  # Target chunk size with buffer
        
    def transcribe_file(self, file_path: Path, language: str | None = None) -> Dict[str, str]:
        self._logger.info("Starting Whisper transcription for file: %s (language: %s)", file_path, language)
        
        # Validate file exists and is readable
        if not file_path.exists():
            self._logger.error("Audio file does not exist: %s", file_path)
            raise TranscriptionError(f"Audio file does not exist: {file_path}")
        
        if not file_path.is_file():
            self._logger.error("Path is not a file: %s", file_path)
            raise TranscriptionError(f"Path is not a file: {file_path}")
        
        file_size = file_path.stat().st_size
        self._logger.info("File size: %d bytes (%.1f MB)", file_size, file_size / (1024*1024))
        
        if file_size == 0:
            self._logger.error("Audio file is empty: %s", file_path)
            raise TranscriptionError("Audio file is empty")
        
        # Determine if chunking is needed (more conservative threshold)
        if file_size <= self.max_file_size_bytes:
            self._logger.info("File is small enough for direct processing")
            return self._transcribe_single_file(file_path, language)
        else:
            self._logger.info("File is too large, using chunking approach")
            return self._transcribe_with_chunking(file_path, language)
    
    def _transcribe_single_file(self, file_path: Path, language: str | None = None) -> Dict[str, str]:
        """Transcribe a single file that fits within size limits."""
        try:
            with file_path.open("rb") as audio_fp:
                self._logger.debug("Sending request to OpenAI Whisper API")
                response = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_fp,
                    language=language,
                    response_format="text",
                )
                self._logger.info("Whisper API response received")
        except openai.APIError as exc:
            if exc.status_code == 413:
                self._logger.error("Audio file too large for OpenAI Whisper: %d bytes (max %dMB)", 
                                 file_path.stat().st_size, self.max_file_size_mb)
                raise TranscriptionError(
                    f"Audio file too large ({file_path.stat().st_size / (1024*1024):.1f}MB). "
                    f"This should have been chunked automatically."
                ) from exc
            else:
                self._logger.error("OpenAI API error: %s", exc)
                raise TranscriptionError(f"OpenAI API error: {exc}") from exc
        except openai.AuthenticationError as exc:
            self._logger.error("OpenAI authentication error: %s", exc)
            raise TranscriptionError("OpenAI authentication failed - check API key") from exc
        except openai.RateLimitError as exc:
            self._logger.error("OpenAI rate limit error: %s", exc)
            raise TranscriptionError("OpenAI rate limit exceeded") from exc
        except Exception as exc:
            self._logger.error("Unexpected error during Whisper transcription: %s", exc, exc_info=True)
            raise TranscriptionError(f"Whisper transcription failed: {str(exc)}") from exc

        # Handle response format
        if isinstance(response, str):
            text = response
        elif hasattr(response, "text"):
            text = response.text
        else:
            self._logger.error("Unexpected response format from Whisper API: %s", type(response))
            raise TranscriptionError("Unexpected response format from Whisper API")
        
        self._logger.debug("Whisper transcription completed, text length: %d", len(text))
        return {"transcript": text}
    
    def _transcribe_with_chunking(self, file_path: Path, language: str | None = None) -> Dict[str, str]:
        """Transcribe a large file by splitting it into chunks."""
        self._logger.info("Starting chunked transcription for large file")
        
        try:
            # Load audio file
            self._logger.debug("Loading audio file with pydub")
            audio = AudioSegment.from_file(str(file_path))
            
            # Get original audio properties
            original_duration_ms = len(audio)
            original_file_size = file_path.stat().st_size
            
            # Compress audio to reduce chunk sizes
            self._logger.info("Compressing audio for chunking (mono, 16kHz)")
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.set_frame_rate(16000)  # Lower sample rate (still good for speech)
            
            # Calculate dynamic chunk duration based on file size
            chunk_length_ms = self._calculate_optimal_chunk_duration(original_file_size, original_duration_ms)
            chunk_length_minutes = chunk_length_ms / (60 * 1000)
            
            total_chunks = math.ceil(original_duration_ms / chunk_length_ms)
            
            self._logger.info("Audio duration: %.2f minutes, compressed for processing", 
                            original_duration_ms / (60 * 1000))
            self._logger.info("Using dynamic chunk size: %.1f minutes, will create %d chunks", 
                            chunk_length_minutes, total_chunks)
            
            # Process each chunk
            transcripts = []
            for i in range(total_chunks):
                start_time = i * chunk_length_ms
                end_time = min(start_time + chunk_length_ms, original_duration_ms)
                
                self._logger.info("Processing chunk %d/%d (%.1f-%.1f minutes)", 
                                i + 1, total_chunks, 
                                start_time / (60 * 1000), end_time / (60 * 1000))
                
                # Extract chunk
                chunk = audio[start_time:end_time]
                
                # Create temporary file for this chunk
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    chunk_path = Path(temp_file.name)
                
                try:
                    # Export chunk with compression settings
                    chunk.export(
                        str(chunk_path), 
                        format="wav",
                        parameters=["-ar", "16000", "-ac", "1", "-b:a", "128k"]  # Additional compression
                    )
                    
                    # Verify chunk size
                    chunk_size = chunk_path.stat().st_size
                    chunk_size_mb = chunk_size / (1024*1024)
                    self._logger.debug("Chunk %d size: %d bytes (%.1f MB)", 
                                     i + 1, chunk_size, chunk_size_mb)
                    
                    # If chunk is still too large, try further compression
                    if chunk_size > self.max_file_size_bytes:
                        self._logger.warning("Chunk %d still too large (%.1f MB), applying additional compression", 
                                           i + 1, chunk_size_mb)
                        chunk_path = self._compress_chunk_further(chunk, chunk_path)
                        chunk_size = chunk_path.stat().st_size
                        chunk_size_mb = chunk_size / (1024*1024)
                        self._logger.info("After additional compression: %.1f MB", chunk_size_mb)
                    
                    # Transcribe chunk
                    chunk_result = self._transcribe_single_file(chunk_path, language)
                    chunk_text = chunk_result["transcript"].strip()
                    
                    if chunk_text:
                        transcripts.append(chunk_text)
                        self._logger.debug("Chunk %d transcribed: %d characters", i + 1, len(chunk_text))
                    else:
                        self._logger.warning("Chunk %d produced empty transcript", i + 1)
                        
                except Exception as exc:
                    self._logger.error("Error processing chunk %d: %s", i + 1, exc)
                    # Continue with other chunks rather than failing completely
                    transcripts.append(f"[Error transcribing chunk {i + 1}]")
                finally:
                    # Clean up temporary chunk file
                    if chunk_path.exists():
                        chunk_path.unlink()
            
            # Combine all transcripts
            if not transcripts:
                raise TranscriptionError("No chunks were successfully transcribed")
            
            full_transcript = " ".join(transcripts)
            self._logger.info("Chunked transcription completed: %d chunks processed, %d total characters", 
                            len(transcripts), len(full_transcript))
            
            return {
                "transcript": full_transcript,
                "chunks_processed": len(transcripts),
                "total_chunks": total_chunks,
                "chunk_duration_minutes": chunk_length_minutes
            }
            
        except Exception as exc:
            if isinstance(exc, TranscriptionError):
                raise
            self._logger.error("Error during chunked transcription: %s", exc, exc_info=True)
            raise TranscriptionError(f"Chunked transcription failed: {str(exc)}") from exc
    
    def _calculate_optimal_chunk_duration(self, file_size_bytes: int, duration_ms: int) -> int:
        """Calculate optimal chunk duration based on file size and audio duration."""
        file_size_mb = file_size_bytes / (1024 * 1024)
        duration_minutes = duration_ms / (60 * 1000)
        
        # Estimate MB per minute
        mb_per_minute = file_size_mb / duration_minutes
        
        # Calculate chunk duration to stay under target size
        # After compression (mono + 16kHz), size should reduce by ~75%
        compression_factor = 0.25
        estimated_mb_per_minute_compressed = mb_per_minute * compression_factor
        
        # Target chunk size with safety margin
        target_chunk_duration = self.target_chunk_size_mb / estimated_mb_per_minute_compressed
        
        # Clamp between 2 and 8 minutes for practical reasons
        target_chunk_duration = max(2, min(8, target_chunk_duration))
        
        self._logger.info("Calculated optimal chunk duration: %.1f minutes (based on %.1f MB/min compressed)", 
                         target_chunk_duration, estimated_mb_per_minute_compressed)
        
        return int(target_chunk_duration * 60 * 1000)  # Convert to milliseconds
    
    def _compress_chunk_further(self, chunk: AudioSegment, chunk_path: Path) -> Path:
        """Apply additional compression if chunk is still too large."""
        # Try with lower bitrate and sample rate
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            compressed_path = Path(temp_file.name)
        
        # More aggressive compression
        chunk.export(
            str(compressed_path),
            format="wav",
            parameters=["-ar", "8000", "-ac", "1", "-b:a", "64k"]  # Very aggressive compression
        )
        
        # Clean up original chunk
        if chunk_path.exists():
            chunk_path.unlink()
            
        return compressed_path


@lru_cache(maxsize=1)
def get_whisper_transcriber() -> WhisperTranscriber:
    return WhisperTranscriber()
