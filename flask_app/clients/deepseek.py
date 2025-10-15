"""DeepSeek translation client."""
import logging
import os
import requests
from typing import Dict, Any

from utils.exceptions import TranslationError


logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API client for translation services."""
    
    def __init__(self):
        """Initialize DeepSeek client with API credentials."""
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
        
        self.endpoint = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
        """Translate text using DeepSeek API.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
            
        Raises:
            TranslationError: If translation fails
        """
        try:
            logger.info(f"Translating from {source_lang} to {target_lang} using DeepSeek")
            
            # Split text into chunks if needed
            text_chunks = self._split_text_into_chunks(text, source_lang)
            translated_chunks = []
            
            for i, chunk in enumerate(text_chunks, 1):
                if not chunk.strip():
                    continue
                    
                logger.info(f"Translating chunk {i} of {len(text_chunks)}")
                
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": self._get_system_prompt(source_lang, target_lang)
                        },
                        {
                            "role": "user",
                            "content": self._get_user_prompt(chunk, source_lang, target_lang)
                        }
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 4000,
                }
                
                response = requests.post(
                    self.endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                
                if response.status_code != 200:
                    raise TranslationError(f"DeepSeek API error: {response.text}")
                
                translated_text = response.json()['choices'][0]['message']['content']
                translated_chunks.append(translated_text)
            
            return "\n".join(translated_chunks)
            
        except Exception as e:
            logger.error(f"DeepSeek translation error: {e}")
            if isinstance(e, TranslationError):
                raise
            raise TranslationError(f"DeepSeek translation failed: {str(e)}")
    
    def _split_text_into_chunks(self, text: str, language_hint: str = "th", max_tokens: int = 500) -> list:
        """Split text into chunks for translation."""
        # Asian language sentence boundaries
        sentence_delimiters = {
            "th": [" ", "\n", "。", "．", "ฯ", "ๆ"],
            "zh": ["\n", "。", "，", "；", "！", "？"],
            "ja": ["\n", "。", "、", "！", "？", "」"],
            "default": ["\n", ".", "!", "?", "\r"]
        }
        
        # Use character count approximation for Asian languages
        if language_hint in ["th", "zh", "ja", "ko"]:
            max_chars = max_tokens * 2  # Conservative estimate
            delimiter_set = sentence_delimiters.get(language_hint, sentence_delimiters["default"])
        else:
            max_chars = max_tokens * 4  # Default estimate
            delimiter_set = sentence_delimiters["default"]

        chunks = []
        current_chunk = []
        current_length = 0
        buffer = ""

        def safe_add(chunk, buffer):
            if buffer:
                chunk.append(buffer.strip())
                return len(buffer)
            return 0

        for char in text:
            buffer += char
            current_length += 1
            
            # Check for sentence boundaries
            if char in delimiter_set:
                # Check if adding this would exceed limit
                if (current_length + len(buffer)) > max_chars:
                    # Flush current buffer to chunk
                    chunk_length = safe_add(current_chunk, buffer)
                    current_length = chunk_length
                    buffer = ""
                    
                    # Start new chunk if over limit
                    if chunk_length >= max_chars:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = []
                        current_length = 0

        # Add remaining text
        safe_add(current_chunk, buffer)
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks
    
    def _get_system_prompt(self, source_lang: str, target_lang: str) -> str:
        """Get system prompt for translation."""
        return f"""As a medical translation expert, translate this {source_lang} text to {target_lang} with:
        - Exact preservation of medical terminology
        - Natural handling of Asian language particles (ครับ/ค่ะ/-san/-sama)
        - Explicit [Note:] markers for ambiguous terms
        - Strict structural fidelity"""
    
    def _get_user_prompt(self, chunk: str, source_lang: str, target_lang: str) -> str:
        """Get user prompt for translation."""
        return f"""TRANSLATION TASK:
        {chunk}
        
        **Accuracy is Paramount** 
        Ensure to not leave any part of the text untranslated.
        Ensure that all medical terms, anatomical references, and disease names are translated with precision and according to standard medical terminology in {target_lang}.  
        DO NOT assume common meanings—always verify potential medical interpretations before finalizing the translation.

        **Molecule Names & Test Names**  
        Always retain the full and precise name of any molecule, biomarker, protein, enzyme, drug, or laboratory test.  
        If the {source_lang} term seems truncated or missing qualifiers (e.g., missing the organ/system of origin), verify the full form based on context and use the medically correct name in {target_lang}.  
        If a term refers to a specific diagnostic test, branded test, or proprietary medical product, explicitly use its official {target_lang} name instead of a generic translation.

        **Handling Ambiguous or Implicit Terms**  
        If the {source_lang} text omits crucial clarifications, assess the context and select the most medically appropriate translation in {target_lang}.  
        If uncertain, add a clarifying note in brackets (e.g., "elastase [assumed pancreatic elastase-1 based on context]").  In this case, be sure to write as well the translation.
        If a term has multiple medical interpretations, prioritize the most relevant meaning for the given context.  
        If a term has a non-medical common meaning but is used in a medical context, translate it using the appropriate medical terminology.

        **SPECIFIC REQUIREMENTS:**
        1. Preserve numerical values and measurements exactly
        2. Handle Asian-specific:
        - Thai honorific particles → natural equivalents if applies
        - Chinese measure words → localized properly if applies
        - Japanese contextual honorifics if applies
        3. Mark uncertain terms with [Assumed:...]
        4. Maintain original speaker labels (Speaker A/B), use always A, B, C instead of numbers to identify the Speakers.
        5. **IMPORTANT** Do not add any other text or comments to the translation
        6. **IMPORTANT** Be sure that ALL the original text is translated, DO NOT miss any part of the text.
        7. **IMPORTANT** Do not add any other text or comments to the translation, no Title, No footer, nothing more than translation and text for translated text explication.
        """