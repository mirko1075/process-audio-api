"""OpenAI based translation support with automatic text chunking for long texts."""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, List

import openai
import tiktoken
from openai import AuthenticationError, APIError, RateLimitError

from utils.config import get_app_config
from utils.exceptions import TranslationError


PROMPT_TEMPLATE = (
    "You are an expert medical translator. Translate the following text from {source_language} to {target_language}. "
    "Preserve medical terminology, speaker intent, and maintain professional tone. "
    "Return only the translated text without any additional commentary."
)

# Model token limits (leaving buffer for prompt and response)
MODEL_TOKEN_LIMITS = {
    "gpt-4o-mini": 120000,  # 128k context, leaving buffer
    "gpt-4o": 120000,       # 128k context, leaving buffer
    "gpt-4-turbo": 120000,  # 128k context, leaving buffer
    "gpt-4": 7000,          # 8k context, leaving buffer
    "gpt-3.5-turbo": 15000, # 16k context, leaving buffer
}


class OpenAITranslator:
    def __init__(self) -> None:
        config = get_app_config()
        self._client = openai.OpenAI(api_key=config.openai.api_key)
        self._model = config.openai.model
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize tokenizer for the model
        try:
            self._tokenizer = tiktoken.encoding_for_model(self._model)
        except KeyError:
            # Fallback to cl100k_base for newer models
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
            self._logger.warning("Using fallback tokenizer for model %s", self._model)
        
        # Get token limit for the model
        self._max_tokens = MODEL_TOKEN_LIMITS.get(self._model, 7000)  # Conservative default
        self._logger.info("Initialized OpenAI translator with model %s (max tokens: %d)", 
                         self._model, self._max_tokens)

    def translate(self, text: str, source_language: str, target_language: str) -> Dict[str, str]:
        if not text.strip():
            raise TranslationError("Text cannot be empty")
        
        # Count tokens in the input text
        input_tokens = self._count_tokens(text)
        self._logger.info("Starting OpenAI translation: %s -> %s (text length: %d chars, %d tokens)", 
                         source_language, target_language, len(text), input_tokens)
        
        # Handle "auto" source language
        if source_language.lower() == "auto":
            source_language = "the detected language"
        
        # Check if chunking is needed
        prompt = PROMPT_TEMPLATE.format(
            source_language=source_language, 
            target_language=target_language
        )
        prompt_tokens = self._count_tokens(prompt)
        available_tokens = self._max_tokens - prompt_tokens - 1000  # Reserve 1000 for response
        
        if input_tokens <= available_tokens:
            self._logger.info("Text fits in single request (%d tokens available)", available_tokens)
            return self._translate_single(text, source_language, target_language)
        else:
            self._logger.info("Text too long, using chunked translation (%d tokens, %d available)", 
                            input_tokens, available_tokens)
            return self._translate_chunked(text, source_language, target_language, available_tokens)
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using the model's tokenizer."""
        try:
            return len(self._tokenizer.encode(text))
        except Exception as exc:
            self._logger.warning("Token counting failed, using character estimation: %s", exc)
            # Fallback: rough estimation (4 chars per token average)
            return len(text) // 4
    
    def _translate_single(self, text: str, source_language: str, target_language: str) -> Dict[str, str]:
        """Translate text in a single API call."""
        prompt = PROMPT_TEMPLATE.format(
            source_language=source_language, 
            target_language=target_language
        )
        
        try:
            self._logger.debug("Sending single translation request to OpenAI")
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,  # Low temperature for consistent translations
                max_tokens=4000,  # Sufficient for most translations
            )
            
            translated_text = completion.choices[0].message.content
            
            if not translated_text:
                raise TranslationError("OpenAI returned empty translation")
            
            self._logger.info("Single translation completed successfully (output length: %d)", len(translated_text))
            
            return {
                "translated_text": translated_text.strip(),
                "source_language": source_language,
                "target_language": target_language,
                "model_used": self._model
            }
            
        except openai.AuthenticationError as exc:
            self._logger.error("OpenAI authentication error: %s", exc)
            raise TranslationError("OpenAI authentication failed - check API key") from exc
        except openai.RateLimitError as exc:
            self._logger.error("OpenAI rate limit error: %s", exc)
            raise TranslationError("OpenAI rate limit exceeded") from exc
        except openai.APIError as exc:
            self._logger.error("OpenAI API error: %s", exc)
            raise TranslationError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            self._logger.error("Unexpected error during OpenAI translation: %s", exc, exc_info=True)
            raise TranslationError(f"OpenAI translation failed: {str(exc)}") from exc
    
    def _translate_chunked(self, text: str, source_language: str, target_language: str, max_chunk_tokens: int) -> Dict[str, str]:
        """Translate long text by splitting into chunks."""
        self._logger.info("Starting chunked translation")
        
        # Split text into chunks
        chunks = self._split_text_into_chunks(text, max_chunk_tokens)
        self._logger.info("Split text into %d chunks", len(chunks))
        
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            self._logger.info("Translating chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))
            
            try:
                chunk_result = self._translate_single(chunk, source_language, target_language)
                translated_chunks.append(chunk_result["translated_text"])
            except Exception as exc:
                self._logger.error("Error translating chunk %d: %s", i + 1, exc)
                # Continue with other chunks, mark failed chunk
                translated_chunks.append(f"[Error translating chunk {i + 1}]")
        
        # Combine all translated chunks
        full_translation = " ".join(translated_chunks)
        
        self._logger.info("Chunked translation completed: %d chunks processed, %d total characters", 
                         len(translated_chunks), len(full_translation))
        
        return {
            "translated_text": full_translation,
            "source_language": source_language,
            "target_language": target_language,
            "model_used": self._model,
            "chunks_processed": len(chunks),
            "total_chunks": len(chunks)
        }
    
    def _split_text_into_chunks(self, text: str, max_tokens_per_chunk: int) -> List[str]:
        """Split text into chunks that fit within token limits."""
        # First, try to split by sentences to maintain context
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence would exceed the limit
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if self._count_tokens(test_chunk) <= max_tokens_per_chunk:
                current_chunk = test_chunk
            else:
                # Current chunk is full, start a new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single sentence is too long, split it further
                if self._count_tokens(sentence) > max_tokens_per_chunk:
                    chunks.extend(self._split_long_sentence(sentence, max_tokens_per_chunk))
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Filter out empty chunks
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        return chunks
    
    def _split_long_sentence(self, sentence: str, max_tokens: int) -> List[str]:
        """Split a very long sentence into smaller parts."""
        # Split by commas first
        parts = sentence.split(', ')
        
        chunks = []
        current_chunk = ""
        
        for part in parts:
            test_chunk = current_chunk + (", " if current_chunk else "") + part
            
            if self._count_tokens(test_chunk) <= max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single part is still too long, split by words
                if self._count_tokens(part) > max_tokens:
                    chunks.extend(self._split_by_words(part, max_tokens))
                    current_chunk = ""
                else:
                    current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    def _split_by_words(self, text: str, max_tokens: int) -> List[str]:
        """Split text by words as a last resort."""
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            test_chunk = current_chunk + (" " if current_chunk else "") + word
            
            if self._count_tokens(test_chunk) <= max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]


@lru_cache(maxsize=1)
def get_openai_translator() -> OpenAITranslator:
    return OpenAITranslator()
