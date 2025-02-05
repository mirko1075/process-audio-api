

```markdown:README.md
# Audio Processing API

A Flask-based REST API for audio processing, transcription, and analysis. This service supports multiple transcription models (AssemblyAI, OpenAI Whisper, Deepgram), sentiment analysis, and file handling capabilities.

## Features

- 🎤 Audio transcription using multiple providers:
  - AssemblyAI
  - OpenAI Whisper
  - Deepgram
- 📊 Sentiment analysis
- 📝 Text file generation
- 📊 Excel report generation
- 🔒 API key authentication
- 🎯 Multi-language support

## Prerequisites

- Python 3.12+
- FFmpeg installed on your system
- Valid API keys for:
  - AssemblyAI
  - OpenAI
  - Deepgram

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```env
OPENAI_API_KEY=your_openai_key
API_KEY=your_api_key
DEEPGRAM_API_KEY=your_deepgram_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
```

## Usage

Start the server:
```bash
python app.py
```

The server will run on `http://localhost:5000`

### API Endpoints

All endpoints require an `x-api-key` header for authentication.

#### 1. Process Audio
```http
POST /process
Content-Type: multipart/form-data
x-api-key: your_api_key

Parameters:
- audio: (file) Audio file to process
- double_model: (boolean) Use both AssemblyAI and Whisper
- language: (string) Target language code (default: "en")
- sentiment_analysis: (boolean) Perform sentiment analysis
- best_model: (boolean) Use best quality model
```

#### 2. Create Text File
```http
POST /text-to-file
Content-Type: application/json
x-api-key: your_api_key

Body:
{
    "text": "Your text content",
    "fileName": "desired_filename"
}
```

#### 3. Process Audio to File
```http
POST /process-to-file
Content-Type: multipart/form-data
x-api-key: your_api_key

Parameters:
- audio: (file) Audio file to process
- best_model: (boolean) Use best quality model
```

#### 4. Sentiment Analysis
```http
POST /sentiment-analysis
Content-Type: multipart/form-data
x-api-key: your_api_key

Parameters:
- file: (file) Excel file with queries
- text: (string) Text to analyze
- best_model: (boolean) Use best quality model
```

#### 5. Generate Excel Report
```http
POST /generate-excel
Content-Type: application/json
x-api-key: your_api_key

Body:
{
    "sheets": [
        {
            "name": "Sheet1",
            "data": [
                ["Header1", "Header2"],
                ["Value1", "Value2"]
            ]
        }
    ]
}
```

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized (invalid API key)
- 500: Internal Server Error

## File Size Limits

- Maximum audio file size: 100MB
- Larger files are automatically split into chunks for processing

## Development

- Uses Flask for the web framework
- Implements logging for debugging
- Supports multiple audio formats (converts to WAV internally)
- Includes cleanup of temporary files

## Security

- API key authentication required for all endpoints
- Environment variables for sensitive credentials
- Input validation and sanitization

## Environment Variables

Required environment variables in `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
API_KEY=your_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPL_API_KEY=your_deepl_api_key
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
```

## Dependencies

Key dependencies include:
- Flask
- OpenAI
- AssemblyAI
- Deepgram
- FFmpeg-python
- Pandas
- OpenPyXL
- Python-dotenv

For a complete list, see `requirements.txt`
```
