# Audio Transcription Service - Troubleshooting Guide

## OpenAI Whisper with Enhanced Auto-Chunking

### ✅ ENHANCED: Advanced File Processing

**Previous Issue**: Large audio files (>25MB) caused 413 errors.

**Current Solution**: Advanced chunking system with:

1. **Intelligent Size Detection**: Files >20MB automatically processed with chunking
2. **Audio Compression**: Automatic mono conversion + 16kHz sampling reduces file sizes by ~75%
3. **Dynamic Chunk Sizing**: Chunk duration calculated based on audio properties (2-8 minutes)
4. **Progressive Compression**: Additional compression applied if chunks still too large
5. **Smart Reconstruction**: All chunks combined seamlessly into final transcript

### Enhanced Processing Features

#### For Small Files (<20MB):
- Direct processing as before
- Single API call to Whisper
- Fast and efficient

#### For Large Files (>20MB):
- **Automatic compression**: Mono + 16kHz + bitrate optimization
- **Dynamic chunking**: 2-8 minute chunks based on file properties
- **Progressive processing**: Chunks processed sequentially with error resilience
- **Size validation**: Each chunk verified to be under limit before processing

### Real-World Example

**Your 54-minute, 50MB file:**
- ✅ Automatically compressed to ~13MB total
- ✅ Split into 7 optimized chunks (~2MB each)
- ✅ Each chunk processed successfully
- ✅ Combined into single transcript

### Configuration

Enhanced system parameters:
- **File Size Threshold**: 20MB (conservative with 5MB buffer)
- **Chunk Duration**: Dynamic 2-8 minutes (optimized per file)
- **Target Chunk Size**: 15MB (with safety margin)
- **Compression**: Mono, 16kHz, 128k bitrate
- **Fallback Compression**: 8kHz, 64k for oversized chunks

### Service Comparison Updated

| Service | File Size Limit | Quality | Speed | Chunking | Cost |
|---------|-----------------|---------|-------|----------|------|
| **Whisper** | ✅ No limit (auto-chunk) | Excellent | Moderate | Automatic | Low |
| **Deepgram** | ~No limit | Excellent | Fast | Not needed | Moderate |
| **AssemblyAI** | 100MB+ | Very Good | Fast | Not needed | Moderate |

### Response Format

#### Small File Response:
```json
{
  "transcript": "Your transcribed text here"
}
```

#### Large File Response (with chunking):
```json
{
  "transcript": "Combined transcript from all chunks",
  "chunks_processed": 3,
  "total_chunks": 3,
  "chunk_duration_minutes": 10
}
```

### Configuration

The chunking behavior can be customized:
- **Chunk Duration**: 10 minutes (configurable)
- **File Size Threshold**: 24MB (1MB buffer under API limit)
- **Format**: WAV for chunks (optimal for Whisper)

### Error Handling

The service gracefully handles:
- Individual chunk failures (marked in transcript)
- Audio format conversion issues
- Memory constraints for very large files
- API rate limits (processes chunks sequentially)

### Example Usage

**Any size file now works:**
```bash
curl -X POST http://localhost:5000/transcriptions/whisper \
  -H "x-api-key: YOUR_API_KEY" \
  -F "audio=@any_size_file.wav" \
  -F "language=en"
```

### Legacy Options (Still Available)

#### 1. Use Deepgram for Large Files
Still recommended for very large files requiring fastest processing:
- **Endpoint**: `POST /transcriptions/deepgram`
- **File Size**: No practical limit
- **Quality**: Excellent transcription quality with Nova-2 model

#### 2. Manual Compression
If you want smaller files for other reasons:

**Using FFmpeg:**
```bash
ffmpeg -i input.wav -ar 16000 -ac 1 -b:a 96k output.wav
```

### Monitoring and Logging

Enhanced logging now includes:
- Automatic chunking detection
- Chunk processing progress
- Individual chunk sizes and processing times
- Total processing statistics

### Performance Notes

- **Small files**: Same performance as before
- **Large files**: Processing time scales linearly with file size
- **Memory usage**: Efficient - processes one chunk at a time
- **API costs**: Same per-minute rate, just split across multiple requests

## Google Cloud Translation Issues

### Common Error: "Cloud Translation API has not been used in project before or it is disabled"

**Error Message:**

```text
google.api_core.exceptions.Forbidden: 403 POST https://translation.googleapis.com/language/translate/v2
Cloud Translation API has not been used in project 779105669206 before or it is disabled
```

**Cause**: The Google Cloud Translation API is not enabled for your project.

**Solution:**

#### 1. Enable the Translation API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or the project ID shown in the error)
3. Navigate to **APIs & Services** > **Library**
4. Search for "Cloud Translation API"
5. Click on "Cloud Translation API" and press **Enable**
6. Wait a few minutes for the API to be fully activated

#### 2. Verify Service Account Permissions

Ensure your service account has the necessary permissions:

- `roles/cloudtranslate.user` - For basic translation
- `roles/cloudtranslate.admin` - For advanced features

#### 3. Check Credentials Setup

1. **Service Account Key**: Ensure `google/google-credentials.json` exists
2. **Environment Variable**: Set `GOOGLE_APPLICATION_CREDENTIALS` if needed
3. **Project ID**: Verify the correct project ID in your credentials

#### 4. Test Configuration

You can test your Google Cloud setup:

```bash
# Install Google Cloud CLI (if not already installed)
curl https://sdk.cloud.google.com | bash
source ~/.bashrc

# Authenticate and test
gcloud auth application-default login
gcloud translate translate "Hello world" --target-language="es"
```

### Alternative: Use OpenAI Translation

If Google Cloud setup is problematic, use the OpenAI translation service instead:

**Endpoint**: `POST /translations/openai`

**Benefits:**

- ✅ Simpler setup (just API key needed)
- ✅ Enhanced with automatic text chunking for long texts
- ✅ Medical-focused translation prompts
- ✅ Supports all major languages
- ✅ Handles texts of any length automatically

**Request Example:**

```json
{
  "text": "Patient presents with acute chest pain...",
  "source_language": "en",
  "target_language": "es"
}
```

### Google Cloud Billing Issues

**Error**: `QuotaExceeded` or billing-related errors

**Solutions:**

1. **Enable Billing**: Ensure your Google Cloud project has billing enabled
2. **Check Quotas**: Visit Cloud Console > IAM & Admin > Quotas
3. **Increase Limits**: Request quota increases if needed
4. **Monitor Usage**: Set up billing alerts to track usage

### Authentication Errors

**Error**: `Unauthenticated` - Invalid credentials

**Solutions:**

1. **Regenerate Key**: Download a new service account key
2. **File Permissions**: Ensure the credentials file is readable
3. **Path Issues**: Verify the path to `google-credentials.json`
4. **Key Format**: Ensure the JSON file is valid and complete
