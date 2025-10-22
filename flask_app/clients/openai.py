"""OpenAI API client for Whisper transcription and GPT translation with user API keys."""
import logging
import os
from typing import Dict, Any, Optional
from functools import lru_cache

import openai
from pydub import AudioSegment
import tiktoken

from utils.exceptions import TranscriptionError, TranslationError


logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI Whisper and GPT APIs using user's API key."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client with user's API key.
        
        Args:
            api_key: User's OpenAI API key
            model: GPT model to use for translation
            
        Raises:
            TranscriptionError: If API key is invalid or client initialization fails
        """
        if not api_key or not api_key.strip():
            raise TranscriptionError("OpenAI API key is required")
            
        try:
            self._client = openai.OpenAI(api_key=api_key.strip())
            self._model = model
            
            # Initialize tokenizer for text chunking
            try:
                self._tokenizer = tiktoken.encoding_for_model(self._model)
            except KeyError:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.warning(f"Using fallback tokenizer for model {self._model}")
            
            logger.info(f"OpenAI client initialized with user API key, model {self._model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise TranscriptionError(f"OpenAI client initialization failed: {str(e)}")
    
    def transcribe_with_chunking(self, audio_path: str, language: str = 'en') -> Dict[str, Any]:
        """Transcribe audio with automatic chunking for large files.
        
        Args:
            audio_path: Path to audio file
            language: Language code for transcription
            
        Returns:
            Transcription result with chunking metadata if applicable
        """
        logger.info(f"Starting Whisper transcription for {audio_path}")
        
        try:
            # Get file size
            file_size = os.path.getsize(audio_path)
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Audio file size: {size_mb:.1f}MB")
            
            # Use chunking for files over 20MB
            if size_mb > 20:
                return self._transcribe_with_chunking(audio_path, language)
            else:
                return self._transcribe_single(audio_path, language)
                
        except Exception as exc:
            logger.error(f"Whisper transcription failed: {exc}")
            raise TranscriptionError(f"Whisper transcription failed: {str(exc)}") from exc
    
    def _transcribe_single(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcribe single audio file without chunking."""
        logger.info("Processing as single file (no chunking needed)")
        
        with open(audio_path, 'rb') as audio_file:
            response = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="text"
            )
        
        transcript = response.strip() if response else ""
        
        logger.info(f"Single file transcription completed: {len(transcript)} characters")
        
        return {
            "transcript": transcript,
            "language": language,
            "model": "whisper-1",
            "service": "openai_whisper",
            "file_size_mb": os.path.getsize(audio_path) / (1024 * 1024),
            "processing_method": "single_file"
        }
    
    def _transcribe_with_chunking(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcribe large audio file using chunking strategy."""
        logger.info("Processing with chunking strategy")
        
        # Load and compress audio
        audio = AudioSegment.from_file(audio_path)
        compressed_audio = self._compress_audio(audio)
        
        # Calculate optimal chunk duration
        duration_minutes = len(compressed_audio) / (1000 * 60)
        chunk_duration = self._calculate_optimal_chunk_duration(compressed_audio)
        
        logger.info(f"Audio duration: {duration_minutes:.1f} minutes, chunk duration: {chunk_duration} minutes")
        
        # Create chunks
        chunks = self._create_audio_chunks(compressed_audio, chunk_duration)
        
        # Transcribe each chunk
        transcripts = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Save chunk temporarily
            chunk_path = f"{audio_path}_chunk_{i}.wav"
            try:
                chunk.export(chunk_path, format="wav")
                
                # Transcribe chunk
                with open(chunk_path, 'rb') as chunk_file:
                    response = self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=chunk_file,
                        language=language,
                        response_format="text"
                    )
                
                transcript = response.strip() if response else ""
                transcripts.append(transcript)
                
            finally:
                # Clean up chunk file
                if os.path.exists(chunk_path):
                    os.unlink(chunk_path)
        
        # Combine all transcripts
        full_transcript = " ".join(transcripts)
        
        logger.info(f"Chunked transcription completed: {len(chunks)} chunks, {len(full_transcript)} characters")
        
        return {
            "transcript": full_transcript,
            "language": language,
            "model": "whisper-1", 
            "service": "openai_whisper",
            "file_size_mb": os.path.getsize(audio_path) / (1024 * 1024),
            "processing_method": "chunked",
            "total_chunks": len(chunks),
            "chunk_duration_minutes": chunk_duration
        }
    
    def _compress_audio(self, audio: AudioSegment) -> AudioSegment:
        """Compress audio to reduce file size."""
        return audio.set_channels(1).set_frame_rate(16000)
    
    def _calculate_optimal_chunk_duration(self, audio: AudioSegment) -> int:
        """Calculate optimal chunk duration based on audio properties."""
        duration_minutes = len(audio) / (1000 * 60)
        
        if duration_minutes <= 30:
            return 5
        elif duration_minutes <= 60:
            return 7
        else:
            return 10
    
    def _create_audio_chunks(self, audio: AudioSegment, chunk_duration_minutes: int) -> list:
        """Split audio into chunks of specified duration."""
        chunk_length_ms = chunk_duration_minutes * 60 * 1000
        chunks = []
        
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            chunks.append(chunk)
        
        return chunks
    
    def translate_text(self, text: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Translate text using GPT with automatic chunking for long texts.
        
        Args:
            text: Text to translate
            source_language: Source language
            target_language: Target language
            
        Returns:
            Translation result with chunking metadata if applicable
        """
        logger.info(f"Starting GPT translation: {source_language} -> {target_language}")
        
        # Count tokens and determine if chunking is needed
        token_count = len(self._tokenizer.encode(text))
        max_tokens = 120000  # Conservative limit for gpt-4o-mini
        
        if token_count <= max_tokens - 2000:  # Leave buffer for prompt and response
            return self._translate_single(text, source_language, target_language)
        else:
            return self._translate_chunked(text, source_language, target_language)
    
    def _translate_single(self, text: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Translate text in single request."""
        prompt = (
            f"You are an expert medical translator. Translate the following text from {source_language} to {target_language}. "
            "Preserve medical terminology, speaker intent, and maintain professional tone. "
            "Return only the translated text without any additional commentary."
        )
        
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        translated_text = response.choices[0].message.content.strip()
        
        return {
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
            "model_used": self._model,
            "service": "openai_gpt"
        }
    
    def _translate_chunked(self, text: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """Translate long text using chunking strategy."""
        # Implementation similar to the one we created earlier
        # Split by sentences, translate each chunk, combine results
        chunks = self._split_text_for_translation(text)
        translated_chunks = []
        
        for chunk in chunks:
            result = self._translate_single(chunk, source_language, target_language)
            translated_chunks.append(result["translated_text"])
        
        full_translation = " ".join(translated_chunks)
        
        return {
            "translated_text": full_translation,
            "source_language": source_language,
            "target_language": target_language,
            "model_used": self._model,
            "service": "openai_gpt",
            "chunks_processed": len(chunks),
            "total_chunks": len(chunks)
        }
    
    def _split_text_for_translation(self, text: str) -> list:
        """Split text into chunks suitable for translation."""
        # Simple sentence-based splitting for now
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        max_chunk_tokens = 15000
        
        for sentence in sentences:
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(self._tokenizer.encode(test_chunk)) <= max_chunk_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    """Get cached OpenAI client instance."""
    return OpenAIClient()