"""Test suite for video transcription services."""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from flask_app.services.video_transcription import VideoTranscriptionService
from flask_app.clients.video_processor import VideoProcessor
from utils.exceptions import TranscriptionError


class TestVideoTranscriptionService:
    """Test cases for VideoTranscriptionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = VideoTranscriptionService()
    
    def test_transcribe_from_url_empty_url(self):
        """Test transcription with empty URL."""
        with pytest.raises(TranscriptionError, match="Video URL cannot be empty"):
            self.service.transcribe_from_url("", model_size="tiny")
    
    def test_transcribe_from_url_invalid_model_size(self):
        """Test transcription with invalid model size."""
        with pytest.raises(TranscriptionError, match="Invalid model size"):
            self.service.transcribe_from_url(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                model_size="invalid_model"
            )
    
    @patch('flask_app.services.video_transcription.get_video_processor')
    def test_transcribe_from_url_success(self, mock_get_processor):
        """Test successful URL transcription."""
        # Mock VideoProcessor
        mock_processor = Mock()
        mock_get_processor.return_value = mock_processor
        
        # Create a new service instance to use the mocked processor
        service = VideoTranscriptionService()
        service.video_processor = mock_processor
        
        mock_processor.process_video_url.return_value = {
            "transcript": "Test transcript",
            "confidence": 0.95,
            "detected_language": "en",
            "model": "whisper",
            "word_count": 2,
            "transcription_time": 15.2,
            "source": "video_url",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "video_title": "Test Video",
            "video_duration": 120,
            "video_uploader": "Test User"
        }
        
        result = service.transcribe_from_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            model_size="tiny"
        )
        
        assert result["transcript"] == "Test transcript"
        assert result["confidence"] == 0.95
        assert result["detected_language"] == "en"
        assert result["service"] == "whisper-video"
        mock_processor.process_video_url.assert_called_once()
    
    @patch('flask_app.services.video_transcription.get_video_processor')
    def test_transcribe_from_url_processing_error(self, mock_get_processor):
        """Test URL transcription with processing error."""
        # Mock VideoProcessor to raise exception
        mock_processor = Mock()
        mock_get_processor.return_value = mock_processor
        
        # Create a new service instance to use the mocked processor
        service = VideoTranscriptionService()
        service.video_processor = mock_processor
        
        mock_processor.process_video_url.side_effect = Exception("Download failed")
        
        with pytest.raises(TranscriptionError, match="Video URL transcription failed"):
            service.transcribe_from_url(
                "https://www.youtube.com/watch?v=invalid",
                model_size="tiny"
            )


class TestVideoProcessor:
    """Test cases for VideoProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = VideoProcessor()
    
    def test_init_whisper_model_caching(self):
        """Test that Whisper model is cached properly."""
        with patch('flask_app.clients.video_processor.whisper.load_model') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            # First call should load model
            model1 = self.processor._get_whisper_model("tiny")
            mock_load.assert_called_once_with("tiny")
            
            # Second call should use cached model
            model2 = self.processor._get_whisper_model("tiny")
            assert model1 is model2
            mock_load.assert_called_once()  # Still only called once
    
    def test_validate_url_youtube(self):
        """Test URL validation for YouTube URLs."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            assert self.processor._is_valid_url(url)
    
    def test_validate_url_invalid(self):
        """Test URL validation for invalid URLs."""
        invalid_urls = [
            "not_a_url",
            "http://",
            "ftp://example.com",
            ""
        ]
        
        for url in invalid_urls:
            assert not self.processor._is_valid_url(url)
    
    @patch('flask_app.clients.video_processor.yt_dlp.YoutubeDL')
    def test_download_video_success(self, mock_ytdl_class):
        """Test successful video download."""
        mock_ytdl = Mock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
        mock_ytdl.extract_info.return_value = {
            "title": "Test Video",
            "uploader": "Test User",
            "duration": 120
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path, metadata = self.processor._download_video(
                "https://www.youtube.com/watch?v=test",
                temp_dir
            )
            
            assert metadata["title"] == "Test Video"
            assert metadata["uploader"] == "Test User"
            assert metadata["duration"] == 120
            mock_ytdl.extract_info.assert_called_once()
    
    def test_extract_audio_from_video(self):
        """Test audio extraction from video file."""
        with patch('flask_app.clients.video_processor.AudioSegment') as mock_audio_seg:
            mock_audio = Mock()
            mock_audio_seg.from_file.return_value = mock_audio
            
            with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_video:
                with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio:
                    result_path = self.processor._extract_audio_from_video(
                        temp_video.name,
                        temp_audio.name
                    )
                    
                    assert result_path == temp_audio.name
                    mock_audio_seg.from_file.assert_called_once_with(temp_video.name)
                    mock_audio.export.assert_called_once()
    
    @patch('flask_app.clients.video_processor.whisper')
    def test_transcribe_audio_success(self, mock_whisper):
        """Test successful audio transcription."""
        mock_model = Mock()
        mock_whisper.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "text": "Test transcript",
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Test transcript",
                    "avg_logprob": -0.1
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio:
            result = self.processor._transcribe_audio(temp_audio.name, "tiny")
            
            assert result["transcript"] == "Test transcript"
            assert result["language"] == "en"
            assert len(result["segments"]) == 1
            assert result["confidence"] > 0.8  # avg_logprob converted to confidence
    
    def test_calculate_confidence_from_logprob(self):
        """Test confidence calculation from log probability."""
        # Test various log probability values
        test_cases = [
            (-0.1, 0.9),   # High confidence
            (-0.5, 0.6),   # Medium confidence  
            (-1.0, 0.37),  # Lower confidence
            (-2.0, 0.14),  # Low confidence
        ]
        
        for logprob, expected_min in test_cases:
            confidence = self.processor._calculate_confidence(logprob)
            assert confidence >= expected_min - 0.05  # Allow small tolerance
            assert 0.0 <= confidence <= 1.0


class TestVideoTranscriptionIntegration:
    """Integration tests for video transcription workflow."""
    
    @pytest.fixture
    def mock_video_file(self):
        """Create a mock video file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            yield f.name
        os.unlink(f.name)
    
    @patch('flask_app.clients.video_processor.whisper.load_model')
    @patch('flask_app.clients.video_processor.AudioSegment')
    def test_process_video_file_workflow(self, mock_audio_seg, mock_whisper_load, mock_video_file):
        """Test complete video file processing workflow."""
        # Mock whisper model
        mock_model = Mock()
        mock_whisper_load.return_value = mock_model
        mock_model.transcribe.return_value = {
            "text": "Complete test transcript",
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 10.0, "text": "Complete test transcript", "avg_logprob": -0.2}
            ]
        }
        
        # Mock audio processing
        mock_audio = Mock()
        mock_audio_seg.from_file.return_value = mock_audio
        
        processor = VideoProcessor()
        
        result = processor.process_video_file(
            mock_video_file,
            model_size="tiny",
            auto_detect_language=True
        )
        
        assert result["transcript"] == "Complete test transcript"
        assert result["language"] == "en"
        assert result["model_used"] == "tiny"
        assert "processing_time" in result
        assert "confidence" in result