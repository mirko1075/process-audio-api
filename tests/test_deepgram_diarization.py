"""Test suite for Deepgram diarization functionality."""
import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from flask_app.clients.deepgram import DeepgramClient
from flask_app.services.transcription import DeepgramService
from utils.exceptions import TranscriptionError


class TestDeepgramDiarization:
    """Test cases for Deepgram diarization features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the DGClient to avoid requiring real API keys
        with patch('flask_app.clients.deepgram.DGClient'):
            self.client = DeepgramClient(api_key="test-api-key")
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_transcribe_without_diarization(self, mock_dg_client):
        """Test transcription without diarization (default behavior)."""
        # Setup mocks
        mock_client_instance = Mock()
        mock_dg_client.return_value = mock_client_instance
        
        # Create new client instance with mocks
        client = DeepgramClient(api_key="test-api-key")
        client._client = mock_client_instance
        
        mock_response = self._create_mock_response(include_speakers=False)
        mock_client_instance.listen.rest.v.return_value.transcribe_file.return_value = mock_response
        
        # Test transcription without diarization
        audio_data = b"fake audio data"
        result = client.transcribe(audio_data, language="en", model="nova-2", diarize=False)
        
        assert result["transcript"] == "Hello, this is a test."
        assert result["confidence"] == 0.95
        assert "diarization" not in result
        assert result["service"] == "deepgram"
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_transcribe_with_diarization(self, mock_dg_client):
        """Test transcription with diarization enabled."""
        # Setup mocks
        mock_client_instance = Mock()
        mock_dg_client.return_value = mock_client_instance
        
        # Create new client instance with mocks
        # Create new client instance with mocks
        client = DeepgramClient(api_key="test-api-key")
        client._client = mock_client_instance
        
        mock_response = self._create_mock_response(include_speakers=True)
        mock_client_instance.listen.rest.v.return_value.transcribe_file.return_value = mock_response
        
        # Test transcription with diarization
        audio_data = b"fake audio data"
        result = client.transcribe(audio_data, language="en", model="nova-2", diarize=True)
        
        assert result["transcript"] == "Hello, this is a test."
        assert result["confidence"] == 0.95
        assert "diarization" in result
        
        # Check diarization structure
        diarization = result["diarization"]
        assert diarization["speakers_detected"] == 2
        assert len(diarization["speakers"]) == 2
        assert len(diarization["segments"]) == 2
        
        # Check speaker segments
        segments = diarization["segments"]
        assert segments[0]["speaker"] == "Speaker_0"
        assert segments[0]["text"] == "Hello this"  # No comma because it processes individual words
        assert segments[1]["speaker"] == "Speaker_1"
        assert segments[1]["text"] == "is a test"
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_transcribe_with_paragraphs(self, mock_dg_client):
        """Test transcription with paragraph detection."""
        # Setup mocks
        mock_client_instance = Mock()
        mock_dg_client.return_value = mock_client_instance
        
        # Create new client instance with mocks
        client = DeepgramClient(api_key="test-api-key")
        client._client = mock_client_instance
        
        mock_response = self._create_mock_response(include_paragraphs=True)
        mock_client_instance.listen.rest.v.return_value.transcribe_file.return_value = mock_response
        
        # Test transcription with paragraphs
        audio_data = b"fake audio data"
        result = client.transcribe(audio_data, paragraphs=True)
        
        assert "paragraphs" in result
        paragraphs = result["paragraphs"]
        assert len(paragraphs) == 2
        assert paragraphs[0]["text"] == "Hello, this"
        assert paragraphs[1]["text"] == "is a test."
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_process_diarization_with_multiple_speakers(self, mock_dg_client):
        """Test diarization processing with multiple speakers."""
        # Setup mocks
        mock_dg_client.return_value = Mock()
        
        # Create client with mocks
        client = DeepgramClient(api_key="test-api-key")
        
        # Mock word data with speaker information
        words = [
            {"word": "Hello", "speaker": 0, "start": 0.0, "end": 0.5, "confidence": 0.95},
            {"word": "this", "speaker": 0, "start": 0.6, "end": 0.9, "confidence": 0.92},
            {"word": "is", "speaker": 1, "start": 1.0, "end": 1.2, "confidence": 0.88},
            {"word": "a", "speaker": 1, "start": 1.3, "end": 1.4, "confidence": 0.90},
            {"word": "test", "speaker": 1, "start": 1.5, "end": 1.8, "confidence": 0.93},
        ]
        
        result = client._process_diarization({}, words)
        
        assert result["speakers_detected"] == 2
        assert result["total_duration"] == 1.8
        assert len(result["segments"]) == 2
        
        # Check speaker statistics
        speakers = result["speakers"]
        speaker_0 = next(s for s in speakers if s["speaker_id"] == "Speaker_0")
        speaker_1 = next(s for s in speakers if s["speaker_id"] == "Speaker_1")
        
        assert speaker_0["total_words"] == 2
        assert speaker_1["total_words"] == 3
        assert speaker_0["average_confidence"] == pytest.approx(0.935, rel=1e-3)
        assert speaker_1["average_confidence"] == pytest.approx(0.903, rel=1e-3)
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_process_diarization_empty_words(self, mock_dg_client):
        """Test diarization processing with no word data."""
        # Setup mocks
        mock_dg_client.return_value = Mock()
        
        # Create client with mocks
        client = DeepgramClient(api_key="test-api-key")
        
        result = client._process_diarization({}, [])
        
        assert "error" in result
        assert "No word-level data available" in result["error"]
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_process_paragraphs_valid_data(self, mock_dg_client):
        """Test paragraph processing with valid data."""
        # Setup mocks
        mock_dg_client.return_value = Mock()
        
        # Create client with mocks
        client = DeepgramClient(api_key="test-api-key")
        
        # Mock paragraph data
        mock_paragraphs = {
            "transcript": [
                {"text": "First paragraph.", "start": 0.0, "end": 2.0},
                {"text": "Second paragraph.", "start": 2.1, "end": 4.0}
            ]
        }
        
        result = client._process_paragraphs(mock_paragraphs)
        
        assert len(result) == 2
        assert result[0]["text"] == "First paragraph."
        assert result[0]["start_time"] == 0.0
        assert result[0]["duration"] == 2.0
        assert result[1]["text"] == "Second paragraph."
        assert result[1]["duration"] == 1.9
    
    @patch('flask_app.clients.deepgram.DGClient')
    def test_process_paragraphs_empty_data(self, mock_dg_client):
        """Test paragraph processing with empty data."""
        # Setup mocks
        mock_dg_client.return_value = Mock()
        
        # Create client with mocks
        client = DeepgramClient(api_key="test-api-key")
        
        result = client._process_paragraphs(None)
        assert result == []
        
        result = client._process_paragraphs({})
        assert result == []
    
    def _create_mock_response(self, include_speakers=False, include_paragraphs=False):
        """Create a mock Deepgram response for testing."""
        # Basic word data
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.95},
            {"word": "this", "start": 0.6, "end": 0.9, "confidence": 0.92},
            {"word": "is", "start": 1.0, "end": 1.2, "confidence": 0.88},
            {"word": "a", "start": 1.3, "end": 1.4, "confidence": 0.90},
            {"word": "test", "start": 1.5, "end": 1.8, "confidence": 0.93},
        ]
        
        # Add speaker information if diarization is enabled
        if include_speakers:
            words[0]["speaker"] = 0
            words[1]["speaker"] = 0
            words[2]["speaker"] = 1
            words[3]["speaker"] = 1
            words[4]["speaker"] = 1
        
        mock_alternative = {
            "transcript": "Hello, this is a test.",
            "confidence": 0.95,
            "words": words
        }
        
        # Add paragraphs if requested
        if include_paragraphs:
            mock_alternative["paragraphs"] = {
                "transcript": [
                    {"text": "Hello, this", "start": 0.0, "end": 0.9},
                    {"text": "is a test.", "start": 1.0, "end": 1.8}
                ]
            }
        
        mock_response = {
            "results": {
                "channels": [
                    {
                        "alternatives": [mock_alternative],
                        "detected_language": "en",
                        "language_confidence": 0.99
                    }
                ],
                "language": "en",
                "metadata": {
                    "duration": 1.8,
                    "channels": 1,
                    "request_id": "test-request-123"
                }
            }
        }
        
        return mock_response


class TestDeepgramService:
    """Test cases for DeepgramService with diarization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('flask_app.services.transcription.DeepgramClient') as mock_client_class:
            self.mock_client = Mock()
            mock_client_class.return_value = self.mock_client
            self.service = DeepgramService()
    
    def test_transcribe_with_diarization_enabled(self):
        """Test service transcribe method with diarization."""
        # Mock file upload
        mock_file = Mock()
        mock_file.read.return_value = b"fake audio data"
        
        # Mock client response with diarization
        mock_response = {
            "transcript": "Hello world",
            "confidence": 0.95,
            "diarization": {
                "speakers_detected": 2,
                "speakers": [
                    {"speaker_id": "Speaker_0", "total_words": 1},
                    {"speaker_id": "Speaker_1", "total_words": 1}
                ],
                "segments": [
                    {"speaker": "Speaker_0", "text": "Hello", "start_time": 0.0},
                    {"speaker": "Speaker_1", "text": "world", "start_time": 0.5}
                ]
            }
        }
        
        self.mock_client.transcribe.return_value = mock_response
        
        # Test transcription with diarization
        result = self.service.transcribe(
            mock_file, 
            language="en", 
            model="nova-2", 
            diarize=True
        )
        
        assert result["transcript"] == "Hello world"
        assert "diarization" in result
        assert result["diarization"]["speakers_detected"] == 2
        
        # Verify client was called with correct parameters
        self.mock_client.transcribe.assert_called_once_with(
            audio_data=b"fake audio data",
            language="en",
            model="nova-2",
            diarize=True,
            punctuate=True,
            paragraphs=False
        )
    
    def test_transcribe_with_all_options(self):
        """Test service with all enhanced options enabled."""
        # Mock file upload
        mock_file = Mock()
        mock_file.read.return_value = b"fake audio data"
        
        # Mock client response
        mock_response = {
            "transcript": "Test transcript",
            "confidence": 0.90,
            "diarization": {"speakers_detected": 1},
            "paragraphs": [{"text": "Test paragraph"}]
        }
        
        self.mock_client.transcribe.return_value = mock_response
        
        # Test with all options
        result = self.service.transcribe(
            mock_file,
            language="es",
            model="nova-2",
            diarize=True,
            punctuate=False,
            paragraphs=True
        )
        
        assert result["transcript"] == "Test transcript"
        assert "diarization" in result
        assert "paragraphs" in result
        
        # Verify all parameters passed correctly
        self.mock_client.transcribe.assert_called_once_with(
            audio_data=b"fake audio data",
            language="es",
            model="nova-2",
            diarize=True,
            punctuate=False,
            paragraphs=True
        )


class TestDeepgramAPIEndpoint:
    """Test cases for Deepgram API endpoint with diarization."""
    
    @pytest.fixture
    def client(self, monkeypatch):
        """Create test client with mocked environment."""
        monkeypatch.setenv("API_KEY", "test-api-key")
        monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
        monkeypatch.setenv("FLASK_ENV", "testing")
        
        from flask_app import create_app
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            yield client
    
    @patch('flask_app.api.transcription.DeepgramService')
    def test_deepgram_endpoint_with_diarization(self, mock_service_class, client):
        """Test Deepgram endpoint with diarization parameter."""
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.transcribe.return_value = {
            "transcript": "Speaker 1 says hello. Speaker 2 responds.",
            "confidence": 0.92,
            "diarization": {
                "speakers_detected": 2,
                "segments": [
                    {"speaker": "Speaker_0", "text": "Speaker 1 says hello."},
                    {"speaker": "Speaker_1", "text": "Speaker 2 responds."}
                ]
            }
        }
        
        # Create fake audio file
        fake_audio = io.BytesIO(b"fake audio content")
        fake_audio.name = "test.wav"
        
        # Test request with diarization enabled
        response = client.post(
            "/transcriptions/deepgram",
            headers={"x-api-key": "test-api-key"},
            data={
                "audio": (fake_audio, "test.wav"),
                "language": "en",
                "model": "nova-2",
                "diarize": "true",
                "paragraphs": "false"
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert "diarization" in data
        assert data["diarization"]["speakers_detected"] == 2
        assert data["processing_info"]["diarization_enabled"] is True
        
        # Verify service was called with correct parameters
        mock_service.transcribe.assert_called_once()
        call_kwargs = mock_service.transcribe.call_args[1]
        assert call_kwargs["diarize"] is True
        assert call_kwargs["language"] == "en"
        assert call_kwargs["model"] == "nova-2"
    
    def test_deepgram_endpoint_invalid_diarize_parameter(self, client):
        """Test that invalid diarize parameter defaults to False."""
        fake_audio = io.BytesIO(b"fake audio content")
        fake_audio.name = "test.wav"
        
        with patch('flask_app.api.transcription.DeepgramService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.transcribe.return_value = {"transcript": "test"}
            
            # Test with invalid diarize value
            response = client.post(
                "/transcriptions/deepgram",
                headers={"x-api-key": "test-api-key"},
                data={
                    "audio": (fake_audio, "test.wav"),
                    "diarize": "invalid_value"
                }
            )
            
            assert response.status_code == 200
            
            # Should default to False
            call_kwargs = mock_service.transcribe.call_args[1]
            assert call_kwargs["diarize"] is False