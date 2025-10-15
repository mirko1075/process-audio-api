"""Transcription services for various AI providers."""
import tempfile
import os
import logging
from typing import Dict, Any, BinaryIO
from werkzeug.datastructures import FileStorage

from flask_app.clients.deepgram import DeepgramClient
from flask_app.clients.openai import OpenAIClient  
from flask_app.clients.assemblyai import AssemblyAIClient
from utils.exceptions import TranscriptionError


logger = logging.getLogger(__name__)


class TranscriptionService:
    """Base transcription service with common functionality."""
    
    @staticmethod
    def save_temp_file(audio_file: FileStorage) -> str:
        """Save uploaded file to temporary location and return path."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        try:
            audio_file.save(temp_file.name)
            return temp_file.name
        except Exception as exc:
            # Clean up if save failed
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise TranscriptionError(f"Failed to save audio file: {str(exc)}") from exc
    
    @staticmethod
    def cleanup_temp_file(file_path: str) -> None:
        """Clean up temporary file safely."""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as exc:
            logger.warning(f"Failed to clean up temp file {file_path}: {exc}")


class DeepgramService(TranscriptionService):
    """Service for Deepgram transcription using Nova-2 model."""
    
    def __init__(self):
        self.client = DeepgramClient()
        logger.info("Deepgram transcription service initialized")
    
    def transcribe(self, audio_file: FileStorage, language: str = 'en', 
                  model: str = 'nova-2') -> Dict[str, Any]:
        """Transcribe audio file using Deepgram Nova-2.
        
        Args:
            audio_file: Uploaded audio file
            language: Language code (default: 'en')
            model: Deepgram model to use (default: 'nova-2')
            
        Returns:
            Transcription result with metadata
        """
        logger.info(f"Starting Deepgram transcription (language: {language}, model: {model})")
        
        try:
            # Read file content
            file_bytes = audio_file.read()
            audio_file.seek(0)  # Reset file pointer for potential reuse
            
            # Use client to transcribe
            result = self.client.transcribe(
                audio_data=file_bytes,
                language=language,
                model=model
            )
            
            logger.info("Deepgram transcription completed successfully")
            return result
            
        except Exception as exc:
            logger.error(f"Deepgram transcription failed: {exc}")
            raise TranscriptionError(f"Deepgram transcription failed: {str(exc)}") from exc


class WhisperService(TranscriptionService):
    """Service for OpenAI Whisper transcription with automatic chunking."""
    
    def __init__(self):
        self.client = OpenAIClient()
        logger.info("OpenAI Whisper transcription service initialized")
    
    def transcribe(self, audio_file: FileStorage, language: str = 'en') -> Dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper with automatic chunking.
        
        Args:
            audio_file: Uploaded audio file
            language: Language code (default: 'en')
            
        Returns:
            Transcription result with chunking metadata if applicable
        """
        logger.info(f"Starting Whisper transcription (language: {language})")
        
        temp_path = None
        try:
            # Save to temporary file (required for audio processing)
            temp_path = self.save_temp_file(audio_file)
            
            # Use client to transcribe with automatic chunking
            result = self.client.transcribe_with_chunking(
                audio_path=temp_path,
                language=language
            )
            
            logger.info("Whisper transcription completed successfully")
            return result
            
        except Exception as exc:
            logger.error(f"Whisper transcription failed: {exc}")
            raise TranscriptionError(f"Whisper transcription failed: {str(exc)}") from exc
        finally:
            # Always clean up temp file
            if temp_path:
                self.cleanup_temp_file(temp_path)


class AssemblyAIService(TranscriptionService):
    """Service for AssemblyAI transcription."""
    
    def __init__(self):
        self.client = AssemblyAIClient()
        logger.info("AssemblyAI transcription service initialized")
    
    def transcribe(self, audio_file: FileStorage, language: str = 'en') -> Dict[str, Any]:
        """Transcribe audio file using AssemblyAI.
        
        Args:
            audio_file: Uploaded audio file
            language: Language code (default: 'en')
            
        Returns:
            Transcription result with metadata
        """
        logger.info(f"Starting AssemblyAI transcription (language: {language})")
        
        temp_path = None
        try:
            # Save to temporary file
            temp_path = self.save_temp_file(audio_file)
            
            # Use client to transcribe
            result = self.client.transcribe(
                audio_path=temp_path,
                language=language
            )
            
            logger.info("AssemblyAI transcription completed successfully")
            return result
            
        except Exception as exc:
            logger.error(f"AssemblyAI transcription failed: {exc}")
            raise TranscriptionError(f"AssemblyAI transcription failed: {str(exc)}") from exc
        finally:
            # Always clean up temp file
            if temp_path:
                self.cleanup_temp_file(temp_path)