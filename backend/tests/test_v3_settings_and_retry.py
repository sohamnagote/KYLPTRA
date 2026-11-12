import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_project, get_all_settings, update_settings, reset_settings

client = TestClient(app)

def test_settings_crud():
    # Reset to defaults
    res = client.post("/api/settings/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["profile"] == "balanced"
    assert data["default_clip_count"] == "5"

    # Update settings
    update_res = client.post("/api/settings", json={
        "profile": "fast",
        "default_clip_count": "3",
        "export_resolution": "720p"
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["profile"] == "fast"
    assert updated["default_clip_count"] == "3"
    assert updated["export_resolution"] == "720p"

    # Retrieve settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    assert get_res.json()["profile"] == "fast"

def test_hardware_tests_api():
    # Test GPU endpoint
    gpu_res = client.post("/api/system/test-gpu")
    assert gpu_res.status_code == 200
    gpu_data = gpu_res.json()
    assert gpu_data["status"] in ("PASS", "INFO")
    assert "duration_sec" in gpu_data

    # Test FFmpeg endpoint
    ff_res = client.post("/api/system/test-ffmpeg")
    assert ff_res.status_code == 200
    ff_data = ff_res.json()
    assert ff_data["status"] == "PASS"
    assert "encoder" in ff_data

    # Test refresh hardware
    ref_res = client.post("/api/system/refresh-hardware")
    assert ref_res.status_code == 200
    assert "video_encoder" in ref_res.json()

def test_storage_info_api():
    res = client.get("/api/system/storage-info")
    assert res.status_code == 200
    data = res.json()
    assert "paths" in data
    assert "sizes_mb" in data
    assert "disk" in data
    assert data["disk"]["total_gb"] > 0

    clear_res = client.post("/api/system/clear-temp")
    assert clear_res.status_code == 200
    assert "cleared_files" in clear_res.json()

def test_models_api():
    res = client.get("/api/models")
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 4
    names = [m["name"] for m in models]
    assert "tiny" in names
    assert "base" in names
    assert "small" in names
    assert "medium" in names

def test_dueflow_showcase_project_health():
    from backend.database import list_projects
    projects = [proj for proj in list_projects() if proj["name"] == "Dueflow-Showcase"]
    assert len(projects) > 0, "Dueflow-Showcase project should exist"
    p = projects[0]
    proj_id = p["id"]
    assert p["status"] == "ready"
    assert not p.get("error_message")

    # Check clips
    clips_res = client.get(f"/api/projects/{proj_id}/clips")
    assert clips_res.status_code == 200
    clips = clips_res.json()
    assert len(clips) >= 3
    for c in clips:
        assert c["score"] >= 70
        assert c["duration"] > 0
        assert c["aspect_ratio"] == "9:16"

