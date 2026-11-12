import sys
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.youtube_service import validate_youtube_url, fetch_youtube_metadata, YouTubeError
from backend.hardware import get_system_hardware_profile, check_whisper_cuda, detect_best_ffmpeg_encoder
from backend.cache import compute_file_fingerprint, get_transcript_cache_key, get_cached_transcript, save_cached_transcript
from backend.transcription import PROFILES

def test_youtube_url_validation():
    # Valid formats
    assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert validate_youtube_url("https://youtube.com/shorts/3nQNiWdeH2Q") is True
    assert validate_youtube_url("http://m.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert validate_youtube_url("https://www.youtube.com/live/dQw4w9WgXcQ") is True
    
    # Invalid formats / other domains
    assert validate_youtube_url("https://vimeo.com/12345678") is False
    assert validate_youtube_url("https://dailymotion.com/video/x7tgad0") is False
    assert validate_youtube_url("https://not-youtube.com/watch?v=abc") is False
    assert validate_youtube_url("not a url") is False
    assert validate_youtube_url("") is False

def test_youtube_metadata_fetch():
    # Test with standard public video (Never Gonna Give You Up)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    meta = fetch_youtube_metadata(url)
    assert meta is not None
    assert "title" in meta
    assert len(meta["title"]) > 0
    assert meta["duration"] > 0
    assert "channel" in meta
    assert "thumbnail" in meta
    assert "resolutions_available" in meta

def test_youtube_invalid_url_rejection():
    with pytest.raises(YouTubeError):
        fetch_youtube_metadata("https://invalid-domain.com/video")

def test_hardware_profiling():
    profile = get_system_hardware_profile()
    assert profile is not None
    assert "gpu" in profile
    assert "whisper" in profile
    assert "video_encoder" in profile
    assert profile["whisper"]["available"] is True
    assert profile["whisper"]["device"] == "cuda"
    assert profile["video_encoder"]["is_hardware"] is True

def test_transcript_caching(tmp_path):
    dummy_file = tmp_path / "dummy_video.mp4"
    dummy_file.write_bytes(b"A" * 1024 * 1024 * 2) # 2MB dummy file
    
    fp = compute_file_fingerprint(str(dummy_file))
    assert len(fp) == 64 # SHA256 hex
    
    key = get_transcript_cache_key(fp, "small", "en", "balanced")
    assert len(key) == 32 # MD5 hex
    
    # Save cache
    dummy_transcript = {"language": "en", "duration": 10.0, "full_text": "Cached speech"}
    save_cached_transcript(key, dummy_transcript)
    
    # Retrieve cache
    retrieved = get_cached_transcript(key)
    assert retrieved is not None
    assert retrieved["full_text"] == "Cached speech"

def test_transcription_profiles():
    assert "fast" in PROFILES
    assert "balanced" in PROFILES
    assert "accurate" in PROFILES
    assert PROFILES["fast"]["model"] == "base"
    assert PROFILES["balanced"]["model"] == "small"
    assert PROFILES["accurate"]["model"] == "medium"
    assert PROFILES["fast"]["beam_size"] == 1
    assert PROFILES["balanced"]["word_timestamps"] is True

