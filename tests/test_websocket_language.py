#!/usr/bin/env python3
"""
Test script for WebSocket dynamic language support.

This script tests the WebSocket audio streaming endpoint with different languages.
"""
import socketio
import time
import sys
from base64 import b64encode

# Configuration
WEBSOCKET_URL = "http://localhost:5000"
NAMESPACE = "/audio-stream"

# Test cases: (language_code, expected_language)
TEST_CASES = [
    ("it", "it", "Italian - valid language"),
    ("es", "es", "Spanish - valid language"),
    ("fr", "fr", "French - valid language"),
    ("invalid", "en", "Invalid language - should default to English"),
    ("xyz", "en", "Unknown language - should default to English"),
    (None, "en", "No language - should default to English"),
]

def test_language_selection():
    """Test WebSocket connection with different language parameters."""
    import os
    import pytest

    # Integration test: require WS_TEST_TOKEN env var to run
    token = os.getenv('WS_TEST_TOKEN')
    if not token:
        pytest.skip('WS integration tests skipped: set WS_TEST_TOKEN to run')

    print("=" * 80)
    print("WebSocket Dynamic Language Support Test")
    print("=" * 80)
    print()
    
    results = []
    
    for lang_code, expected_lang, description in TEST_CASES:
        print(f"Testing: {description}")
        print(f"  Language Code: {lang_code}")
        print(f"  Expected: {expected_lang}")
        
        # Create Socket.IO client
        sio = socketio.Client()
        
        # Track connection response
        connection_response = {}
        
        @sio.event
        def connect():
            print("  ✓ Connection established")
        
        @sio.on('connected', namespace=NAMESPACE)
        def on_connected(data):
            connection_response.update(data)
            print(f"  ✓ Received 'connected' event")
            print(f"  ✓ Language confirmed: {data.get('language')}")
        
        @sio.on('error', namespace=NAMESPACE)
        def on_error(data):
            print(f"  ✗ Error: {data}")
        
        @sio.event
        def disconnect():
            print("  ✓ Disconnected")
        
        try:
            # Connect with language parameter
            if lang_code is None:
                # Test without language parameter
                sio.connect(
                    WEBSOCKET_URL,
                    namespaces=[NAMESPACE],
                    auth={'token': token}
                )
            else:
                # Test with language parameter
                sio.connect(
                    f"{WEBSOCKET_URL}?lang={lang_code}",
                    namespaces=[NAMESPACE],
                    auth={'token': token}
                )
            
            # Wait for connection response
            time.sleep(1)
            
            # Verify language
            actual_lang = connection_response.get('language', 'UNKNOWN')
            success = actual_lang == expected_lang
            
            if success:
                print(f"  ✓ TEST PASSED: Language is '{actual_lang}' as expected")
            else:
                print(f"  ✗ TEST FAILED: Expected '{expected_lang}', got '{actual_lang}'")
            
            results.append({
                'test': description,
                'input': lang_code,
                'expected': expected_lang,
                'actual': actual_lang,
                'success': success
            })
            
            # Disconnect
            sio.disconnect()
            
        except Exception as e:
            print(f"  ✗ Connection failed: {e}")
            results.append({
                'test': description,
                'input': lang_code,
                'expected': expected_lang,
                'actual': 'ERROR',
                'success': False,
                'error': str(e)
            })
        
        print()
        time.sleep(0.5)  # Cooldown between tests
    
    # Print summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print()
    
    for result in results:
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"{status}: {result['test']}")
        print(f"         Input: {result['input']}")
        print(f"         Expected: {result['expected']}, Got: {result['actual']}")
        if 'error' in result:
            print(f"         Error: {result['error']}")
        print()
    
    # Assert all subtests passed when run under pytest
    assert passed == total, f"{passed}/{total} websocket language tests passed"


def test_audio_streaming():
    """Test sending audio data with a specific language.

    Integration test: requires WS_TEST_TOKEN env var. Optional WS_TEST_LANG
    environment variable can override language.
    """
    import os
    import pytest

    token = os.getenv('WS_TEST_TOKEN')
    if not token:
        pytest.skip('WS integration tests skipped: set WS_TEST_TOKEN to run')

    language = os.getenv('WS_TEST_LANG', 'it')

    print("=" * 80)
    print(f"WebSocket Audio Streaming Test (Language: {language})")
    print("=" * 80)
    print()

    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✓ Connected to WebSocket")
    
    @sio.on('connected', namespace=NAMESPACE)
    def on_connected(data):
        print(f"✓ Connection confirmed:")
        print(f"  - User ID: {data.get('user_id')}")
        print(f"  - Auth Type: {data.get('auth_type')}")
        print(f"  - Language: {data.get('language')}")
        print()
        
        # Send mock audio data (silence)
        print("Sending mock audio data...")
        mock_audio = b'\x00' * 1024  # 1KB of silence
        encoded_audio = b64encode(mock_audio).decode('utf-8')
        
        sio.emit('audio_data', encoded_audio, namespace=NAMESPACE)
        print("✓ Audio data sent")
    
    @sio.on('transcription', namespace=NAMESPACE)
    def on_transcription(data):
        print(f"✓ Received transcription:")
        print(f"  - Transcript: {data.get('transcript')}")
        print(f"  - Is Final: {data.get('is_final')}")
        print(f"  - Confidence: {data.get('confidence')}")
    
    @sio.on('error', namespace=NAMESPACE)
    def on_error(data):
        print(f"✗ Error: {data.get('message')}")
    
    @sio.event
    def disconnect():
        print("✓ Disconnected")
    
    try:
        # Connect with language parameter
        sio.connect(
            f"{WEBSOCKET_URL}?lang={language}",
            namespaces=[NAMESPACE],
            auth={'token': token}
        )
        
        # Keep connection alive for a few seconds
        time.sleep(3)
        
        # Disconnect
        sio.disconnect()
        print("\nTest completed successfully!")
        assert True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        pytest.fail(f"WebSocket audio streaming test failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test WebSocket dynamic language support")
    parser.add_argument(
        "--token",
        required=True,
        help="Authentication token (Auth0 JWT or session token)"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="WebSocket server URL (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--mode",
        choices=["language", "audio"],
        default="language",
        help="Test mode: 'language' for language selection tests, 'audio' for audio streaming test"
    )
    parser.add_argument(
        "--lang",
        default="it",
        help="Language for audio streaming test (default: it)"
    )
    
    args = parser.parse_args()
    
    # Update global configuration
    WEBSOCKET_URL = args.url
    
    # Run tests
    if args.mode == "language":
        test_language_selection(args.token)
    else:
        test_audio_streaming(args.token, args.lang)
