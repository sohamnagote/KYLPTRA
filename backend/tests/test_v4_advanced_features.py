import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import (
    create_project, get_project, create_clips_batch, get_clip,
    list_caption_presets, get_caption_preset, create_caption_preset,
    delete_caption_preset, list_brand_profiles, create_brand_profile,
    delete_brand_profile, list_broll_assets, create_broll_asset,
    delete_broll_asset
)
from backend.broll_service import match_broll_suggestions, MOTION_GRAPHICS_TEMPLATES
from backend.audio_service import detect_filler_words
from backend.export_service import generate_srt, generate_vtt, generate_premiere_xml
import tempfile
import uuid
from pathlib import Path

client = TestClient(app)

def test_caption_presets_api():
    # 1. List presets - should contain the 15 built-in presets
    res = client.get("/api/caption-presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) >= 15
    preset_names = [p["name"] for p in presets]
    assert "Minimal Clean" in preset_names
    assert "Bold Highlight" in preset_names
    assert "Karaoke" in preset_names
    assert "Cinematic" in preset_names
    assert "News Style" in preset_names

    # 2. Create custom preset
    custom_res = client.post("/api/caption-presets", json={
        "name": "Test Custom Preset",
        "font_name": "Plus Jakarta Sans",
        "font_size": 28,
        "primary_color": "#FF00FF",
        "highlight_color": "#00FFFF",
        "animation": "Pop"
    })
    assert custom_res.status_code == 200
    custom_preset = custom_res.json()
    assert custom_preset["name"] == "Test Custom Preset"
    preset_id = custom_preset["id"]

    # 3. Update preset
    up_res = client.put(f"/api/caption-presets/{preset_id}", json={
        "name": "Updated Custom Preset",
        "font_size": 32
    })
    assert up_res.status_code == 200
    assert up_res.json()["name"] == "Updated Custom Preset"
    assert up_res.json()["font_size"] == 32

    # 4. Delete custom preset
    del_res = client.delete(f"/api/caption-presets/{preset_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

def test_brand_kit_api():
    # 1. Create brand profile
    create_res = client.post("/api/brand-profiles", json={
        "name": "Acme Media Brand",
        "primary_color": "#8273D6",
        "secondary_color": "#F0EDFC",
        "caption_font": "Inter",
        "watermark_position": "top-right",
        "watermark_opacity": 0.85,
        "default_aspect_ratio": "9:16",
        "default_quality": "1080p"
    })
    assert create_res.status_code == 200
    brand = create_res.json()
    assert brand["name"] == "Acme Media Brand"
    brand_id = brand["id"]

    # 2. List brands
    list_res = client.get("/api/brand-profiles")
    assert list_res.status_code == 200
    assert any(b["id"] == brand_id for b in list_res.json())

    # 3. Update brand
    up_res = client.put(f"/api/brand-profiles/{brand_id}", json={
        "name": "Acme Media Pro"
    })
    assert up_res.status_code == 200
    assert up_res.json()["name"] == "Acme Media Pro"

    # 4. Delete brand
    del_res = client.delete(f"/api/brand-profiles/{brand_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

def test_motion_graphics_and_broll():
    # 1. Templates endpoint
    tpl_res = client.get("/api/motion-graphics/templates")
    assert tpl_res.status_code == 200
    tpls = tpl_res.json()
    assert len(tpls) == 8
    assert any("Lower Third" in t["name"] for t in tpls)

    # 2. Match B-Roll suggestions algorithm
    assets = [
        {"id": "b1", "name": "finance_growth_chart.mp4", "tags": "finance, money, revenue, business", "category": "Business"},
        {"id": "b2", "name": "nature_trees.mp4", "tags": "trees, green, forest, outdoor", "category": "Nature"}
    ]
    transcript = "In this video we discuss building revenue and business growth for startups."
    matched = match_broll_suggestions(transcript, assets)
    assert len(matched) > 0
    assert matched[0]["asset"]["id"] == "b1"
    assert "business" in matched[0]["matched_terms"] or "revenue" in matched[0]["matched_terms"]

def test_filler_word_detection():
    data = {
        "segments": [
            {
                "start": 0.0,
                "end": 4.0,
                "text": "Um, so you know, actually this is very important.",
                "words": [
                    {"word": "Um", "start": 0.1, "end": 0.5},
                    {"word": "so", "start": 0.6, "end": 0.8},
                    {"word": "you know", "start": 0.9, "end": 1.4},
                    {"word": "actually", "start": 1.5, "end": 1.9},
                    {"word": "this", "start": 2.0, "end": 2.2}
                ]
            }
        ]
    }
    fillers = detect_filler_words(data)
    assert len(fillers) >= 2
    filler_words = [f["word"].lower() for f in fillers]
    assert "um" in filler_words or "actually" in filler_words

def test_export_subtitles_and_xml(tmp_path):
    segments = [
        {"start": 0.0, "end": 2.5, "text": "Welcome to Klyptra Studio."},
        {"start": 2.5, "end": 5.0, "text": "Creating viral short-form clips."}
    ]

    # SRT
    srt_file = tmp_path / "test.srt"
    res_srt = generate_srt(segments, str(srt_file))
    assert Path(res_srt).exists()
    content = srt_file.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:02,500" in content
    assert "Welcome to Klyptra Studio." in content

    # VTT
    vtt_file = tmp_path / "test.vtt"
    res_vtt = generate_vtt(segments, str(vtt_file))
    assert Path(res_vtt).exists()
    vtt_content = vtt_file.read_text(encoding="utf-8")
    assert "WEBVTT" in vtt_content

    # Premiere XML
    xml_file = tmp_path / "test.xml"
    res_xml = generate_premiere_xml(
        project_name="Test Project",
        clip_title="Clip 1",
        source_file_path=str(tmp_path / "dummy.mp4"),
        start_time=10.0,
        end_time=30.0,
        fps=30.0,
        width=1920,
        height=1080,
        output_xml_path=str(xml_file)
    )
    assert Path(res_xml).exists()
    xml_content = xml_file.read_text(encoding="utf-8")
    assert "<xmeml version=\"4\">" in xml_content
    assert "Test Project - Clip 1" in xml_content
    assert "<in>300</in>" in xml_content
    assert "<out>900</out>" in xml_content

def test_voiceover_voices():
    res = client.get("/api/voiceover/voices")
    assert res.status_code == 200
    voices = res.json()
    assert isinstance(voices, list)
    assert len(voices) > 0

def test_edge_case_custom_instruction_keywords():
    from backend.clip_engine import extract_instruction_keywords
    assert extract_instruction_keywords("") == []
    assert extract_instruction_keywords(None) == []
    kw = extract_instruction_keywords("Find controversial business moments with funny jokes")
    assert "controversial" in kw
    assert "business" in kw
    assert "funny" in kw

def test_edge_case_ass_all_animation_presets(tmp_path):
    from backend.ffmpeg_service import generate_ass_subtitle
    animations = [
        "Fade", "Pop", "Elastic Pop", "Bounce", "Slide Up", "Slide Down",
        "Typewriter", "Karaoke", "Word Reveal", "Highlight Sweep",
        "Smooth Zoom", "Character Reveal", "Gradient Highlight", "Minimal Fade"
    ]
    test_segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello world"},
        {"start": 2.0, "end": 4.5, "text": "नमस्ते दोस्तों, क्लिप्ट्रा प्रो में आपका स्वागत है"}
    ]

    for anim in animations:
        out_ass = tmp_path / f"test_{anim.replace(' ', '_')}.ass"
        res_ass = generate_ass_subtitle(
            test_segments,
            str(out_ass),
            font_name="Inter",
            font_size=24,
            primary_color="#FFFFFF",
            highlight_color="#FFE600",
            position="bottom",
            animation=anim
        )
        assert Path(res_ass).exists()
        content = out_ass.read_text(encoding="utf-8")
        assert "[Script Info]" in content
        assert "Dialogue: 0," in content
        # Verify Hindi segment falls back or renders properly
        assert "नमस्ते" in content

def test_edge_case_export_xml_escaping(tmp_path):
    xml_file = tmp_path / "test_escaped.xml"
    res_xml = generate_premiere_xml(
        project_name="Tom & Jerry <Special> \"Director's Cut\"",
        clip_title="Clips > Best & Funniest Moments",
        source_file_path=str(tmp_path / "video.mp4"),
        start_time=5.0,
        end_time=15.0,
        fps=24.0,
        width=1080,
        height=1920,
        output_xml_path=str(xml_file)
    )
    assert Path(res_xml).exists()
    content = xml_file.read_text(encoding="utf-8")
    assert "&amp;" in content
    assert "&lt;Special&gt;" in content
    assert "<xmeml version=\"4\">" in content
