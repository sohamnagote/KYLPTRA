import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import (
    init_db, create_project, get_project, list_projects,
    update_project_status, delete_project,
    create_clips_batch, get_clip, list_clips_for_project,
    update_clip, create_export, list_exports
)
from backend.clip_engine import detect_clip_candidates, score_candidate_window
from backend.ffmpeg_service import color_to_ass_hex, generate_ass_subtitle

def test_database_project_crud():
    init_db()
    test_id = "test-proj-001"
    
    # Clean previous if exists
    delete_project(test_id)
    
    # Create project
    proj = create_project(
        project_id=test_id,
        name="Test Podcast Episode",
        source_filename="podcast.mp4",
        source_path="C:/videos/podcast.mp4",
        duration=120.5,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
        has_audio=True,
        file_size=10485760
    )
    
    assert proj is not None
    assert proj["id"] == test_id
    assert proj["name"] == "Test Podcast Episode"
    assert proj["duration"] == 120.5
    assert proj["status"] == "created"
    
    # Update status
    update_project_status(test_id, "transcribed", language="en")
    updated = get_project(test_id)
    assert updated["status"] == "transcribed"
    assert updated["language"] == "en"
    
    # List projects
    projs = list_projects()
    assert any(p["id"] == test_id for p in projs)
    
    # Clean up
    assert delete_project(test_id) is True
    assert get_project(test_id) is None

def test_clip_candidate_detection_and_scoring():
    mock_transcript = {
        "duration": 95.0,
        "segments": [
            {
                "id": 0,
                "start": 1.0,
                "end": 8.5,
                "text": "Why do so many creators fail on YouTube in their first month?",
                "words": []
            },
            {
                "id": 1,
                "start": 8.7,
                "end": 22.0,
                "text": "The secret is they never optimize their opening five seconds. That is the biggest mistake.",
                "words": []
            },
            {
                "id": 2,
                "start": 22.2,
                "end": 35.0,
                "text": "If you look at the top viral videos, every single creator uses a high energy visual hook.",
                "words": []
            },
            {
                "id": 3,
                "start": 35.5,
                "end": 50.0,
                "text": "Actually, this formula will definitely double your viewer retention.",
                "words": []
            }
        ]
    }
    
    clips = detect_clip_candidates(mock_transcript, project_id="test-proj", min_clip_duration=15.0, max_clip_duration=60.0)
    assert len(clips) > 0
    top_clip = clips[0]
    
    # Check score and properties
    assert top_clip["score"] >= 70
    assert len(top_clip["score_reasons"]) > 0
    assert top_clip["start_time"] >= 0.0
    assert top_clip["duration"] >= 15.0
    assert "YouTube" in top_clip["transcript_text"] or "secret" in top_clip["transcript_text"]

def test_ass_subtitle_generation(tmp_path):
    sub_path = tmp_path / "test_subtitles.ass"
    segments = [
        {"start": 1.5, "end": 4.2, "text": "Welcome to KLYPTRA video clipping studio."},
        {"start": 4.5, "end": 8.0, "text": "This is a synchronized vertical subtitle."}
    ]
    
    gen_path = generate_ass_subtitle(
        segments_or_words=segments,
        output_ass_path=str(sub_path),
        font_name="Inter",
        font_size=24,
        color="#FFFFFF",
        position="bottom"
    )
    
    assert Path(gen_path).exists()
    content = Path(gen_path).read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "Welcome to KLYPTRA" in content
    assert "Dialogue: 0,0:00:01.50,0:00:04.20" in content

def test_color_to_ass_hex():
    assert color_to_ass_hex("#FFFFFF") == "&H00FFFFFF&"
    assert color_to_ass_hex("#FF0000") == "&H000000FF&"  # Red in ASS BGR is 0000FF
    assert color_to_ass_hex("#0000FF") == "&H00FF0000&"  # Blue in ASS BGR is FF0000

