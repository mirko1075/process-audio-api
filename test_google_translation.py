#!/usr/bin/env python3
"""Test Google translation service error handling."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from core.translation.google_service import GoogleTranslator
from utils.exceptions import TranslationError


def test_google_translation():
    """Test Google translation with enhanced error messages."""
    print("Testing Google Cloud Translation Service")
    print("=" * 50)
    
    try:
        print("1. Initializing Google Translator...")
        translator = GoogleTranslator()
        print("   ✓ Translator initialized successfully")
        
        print("\n2. Testing translation...")
        result = translator.translate(
            text="Hello, how are you?",
            target_language="es"
        )
        
        print("   ✓ Translation successful!")
        print(f"   Original: Hello, how are you?")
        print(f"   Translation: {result['translated_text']}")
        print(f"   Service: {result['service']}")
        print(f"   Target Language: {result['target_language']}")
        
    except TranslationError as e:
        print(f"\n❌ Translation Error (This is expected):")
        print(f"   {str(e)}")
        print("\n💡 This enhanced error message helps you understand:")
        print("   - What specific Google Cloud issue occurred")
        print("   - How to fix the configuration")
        print("   - Alternative solutions (use OpenAI translation)")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error:")
        print(f"   {str(e)}")


if __name__ == "__main__":
    test_google_translation()