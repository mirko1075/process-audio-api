"""
Test script to verify YouTube video transcription fixes.
Tests the enhanced yt-dlp configuration and error handling.
"""

import requests
import json
import time

def test_video_transcription_fix():
    """Test video transcription with enhanced error handling."""
    
    base_url = "http://localhost:5000"
    api_key = "your-api-key-here"  # Replace with your actual API key
    
    print("🧪 Testing Video Transcription Fixes")
    print("=" * 50)
    
    # Test videos (from simple to potentially problematic)
    test_videos = [
        {
            "name": "Simple Public Video",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - usually works
            "expected": "should work"
        },
        {
            "name": "Educational Content",
            "url": "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - Gangnam Style
            "expected": "should work"
        },
        {
            "name": "Original Problem Video",
            "url": "https://www.youtube.com/watch?v=-X9XILuCwcg",
            "expected": "may fail depending on restrictions"
        }
    ]
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n🎥 Test {i}/3: {video['name']}")
        print(f"URL: {video['url']}")
        print(f"Expected: {video['expected']}")
        
        data = {
            "video_url": video['url'],
            "model_size": "tiny",  # Use smallest model for faster testing
            "language": "en"
        }
        
        try:
            print("📡 Sending request...")
            response = requests.post(
                f"{base_url}/transcriptions/video",
                json=data,
                headers=headers,
                timeout=120  # 2 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ SUCCESS!")
                print(f"   Transcript length: {len(result.get('transcript', ''))} characters")
                print(f"   Duration: {result.get('duration_seconds', 'unknown')} seconds")
                print(f"   Model: {result.get('model_used', 'unknown')}")
                if 'metadata' in result:
                    metadata = result['metadata']
                    print(f"   Title: {metadata.get('title', 'Unknown')}")
                    print(f"   Uploader: {metadata.get('uploader', 'Unknown')}")
            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   Raw response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ TIMEOUT: Request took longer than 2 minutes")
        except requests.exceptions.ConnectionError:
            print("🔌 CONNECTION ERROR: Could not connect to the API")
            print("   Make sure the Flask app is running on localhost:5000")
            break
        except Exception as e:
            print(f"💥 UNEXPECTED ERROR: {e}")
        
        # Wait between tests to be respectful to YouTube
        if i < len(test_videos):
            print("⏳ Waiting 5 seconds before next test...")
            time.sleep(5)
    
    print("\n📊 Test Summary")
    print("=" * 30)
    print("✅ If any tests succeeded: yt-dlp configuration is working")
    print("❌ If all tests failed with 403: YouTube is blocking all requests")
    print("🔄 If mixed results: Some videos have restrictions, others work")
    print("")
    print("💡 Next Steps:")
    print("- If all failed: Run ./scripts/update_ytdlp.sh")
    print("- If mixed: Use working video URLs or upload files directly")
    print("- Check API key is correct in the script")


def test_file_upload():
    """Test video file upload as alternative to URL download."""
    print("\n📁 Testing File Upload Alternative")
    print("=" * 40)
    print("Note: This requires you to have a video file to test with")
    print("")
    print("Example curl command for file upload:")
    print("curl -X POST http://localhost:5000/transcriptions/video \\")
    print("  -H 'x-api-key: your-key' \\")
    print("  -F 'video=@your-video.mp4' \\")
    print("  -F 'model_size=tiny'")


if __name__ == "__main__":
    print("⚠️  IMPORTANT: Update the API key in this script before running!")
    print("   Line 16: api_key = 'your-api-key-here'")
    print("")
    
    # Uncomment the next line after setting your API key
    # test_video_transcription_fix()
    
    test_file_upload()
    
    print("\n🚀 To run the video tests:")
    print("1. Set your API key in this script")
    print("2. Make sure Flask app is running (python app.py)")
    print("3. Uncomment the test_video_transcription_fix() call")
    print("4. Run: python test_video_fixes.py")