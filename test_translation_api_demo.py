#!/usr/bin/env python3
"""Demo of the enhanced Google Translation error messages via API."""

import requests
import json


def test_google_translation_api():
    """Test the Google translation API endpoint with enhanced error handling."""
    print("Testing Google Translation API Error Handling")
    print("=" * 50)
    
    # Test data
    test_data = {
        "text": "Patient presents with acute chest pain and elevated troponin levels.",
        "target_language": "es"
    }
    
    try:
        print("Sending request to Google translation endpoint...")
        print(f"Text: {test_data['text']}")
        print(f"Target Language: {test_data['target_language']}")
        
        response = requests.post(
            "http://localhost:5000/translations/google",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Translation successful!")
            print(f"Translation: {result['translated_text']}")
            print(f"Service: {result.get('service', 'google_cloud')}")
        else:
            # This is where we'll see our enhanced error message
            error_data = response.json()
            print("❌ Translation failed (expected due to API not enabled)")
            print(f"Error Message: {error_data.get('error', 'Unknown error')}")
            print("\n💡 This enhanced error message now clearly explains:")
            print("   - The specific Google Cloud issue")
            print("   - How to enable the Translation API")
            print("   - Alternative: Use /translations/openai endpoint")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app")
        print("💡 Start the Flask app first: python app.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def demo_openai_alternative():
    """Show how to use the OpenAI translation as an alternative."""
    print("\n" + "=" * 50)
    print("Alternative: OpenAI Translation (Working)")
    print("=" * 50)
    
    test_data = {
        "text": "Patient presents with acute chest pain and elevated troponin levels.",
        "source_language": "en",
        "target_language": "es"
    }
    
    try:
        print("Sending request to OpenAI translation endpoint...")
        print(f"Text: {test_data['text']}")
        print(f"Source: {test_data['source_language']}")
        print(f"Target: {test_data['target_language']}")
        
        response = requests.post(
            "http://localhost:5000/translations/openai",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ OpenAI translation successful!")
            print(f"Translation: {result['translated_text']}")
            print(f"Model: {result['model_used']}")
            if 'chunks_processed' in result:
                print(f"Chunks processed: {result['chunks_processed']}")
        else:
            error_data = response.json()
            print(f"❌ Error: {error_data.get('error', 'Unknown error')}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app")
        print("💡 Start the Flask app first: python app.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    test_google_translation_api()
    demo_openai_alternative()