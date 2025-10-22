#!/bin/bash

# Script to update yt-dlp to the latest version to handle YouTube restrictions

echo "🔄 Updating yt-dlp to handle YouTube restrictions..."

# Update yt-dlp to the latest version
pip install --upgrade yt-dlp

# Check version
echo "✅ Current yt-dlp version:"
yt-dlp --version

echo ""
echo "📋 Common solutions for YouTube 403 errors:"
echo "1. Updated yt-dlp to latest version"
echo "2. Enhanced user agent and headers"
echo "3. Added retry logic with exponential backoff"
echo "4. Improved error messages"
echo ""
echo "💡 If issues persist:"
echo "- Try different video URLs"
echo "- Upload video files directly instead"
echo "- Check if video has geographic restrictions"
echo "- Ensure video is publicly accessible"
echo ""
echo "🧪 Test with a simple video:"
echo "yt-dlp --extract-audio --audio-format mp3 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' --output 'test_video.%(ext)s'"