import sys
from pathlib import Path
from starlette.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "KLYPTRA"

def test_api_system_info():
    res = client.get("/api/system-info")
    assert res.status_code == 200
    data = res.json()
    assert "gpu_acceleration" in data
    assert "device_description" in data
    assert "disk_free_gb" in data

def test_api_projects_list_empty_initially():
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_api_nonexistent_project_404():
    res = client.get("/api/projects/non-existent-uuid-1234")
    assert res.status_code == 404

def test_api_nonexistent_clip_404():
    res = client.get("/api/clips/non-existent-uuid-1234")
    assert res.status_code == 404

def test_api_task_status_404():
    res = client.get("/api/tasks/non-existent-task/status")
    assert res.status_code == 404

