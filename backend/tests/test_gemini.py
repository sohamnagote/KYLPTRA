import pytest
from backend.gemini_service import (
    load_gemini_config,
    save_gemini_config,
    test_gemini_connection as check_gemini_connection,
    enhance_clip_metadata,
    SUPPORTED_MODELS
)

def test_gemini_config_defaults():
    cfg = load_gemini_config()
    assert "enabled" in cfg
    assert "local_only_mode" in cfg
    assert "model" in cfg
    assert cfg["model"] in SUPPORTED_MODELS

def test_gemini_test_connection_empty_key():
    res = check_gemini_connection("")
    assert res["success"] is False
    assert "No API key" in res["error"]

def test_gemini_local_fallback_when_disabled():
    # When disabled, must return local fallback without network calls
    cfg = load_gemini_config()
    cfg["enabled"] = False
    cfg["local_only_mode"] = True
    save_gemini_config(cfg)
    
    result = enhance_clip_metadata("Test Title", "Here is a test transcript segment.")
    assert result["source"] == "local"
    assert result["title"] == "Test Title"
    assert "#Shorts" in result["hashtags"]

