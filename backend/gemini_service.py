"""
KLYPTRA — Optional Google Gemini API Integration Service
Provides optional cloud AI enhancements (title generation, hook detection, transcript summaries,
hashtags, and semantic ranking) with secure local key storage and zero cloud dependency.
Core application features operate 100% locally with or without this service.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from pathlib import Path
from backend.config import KLYPTRA_HOME

GEMINI_CONFIG_PATH = KLYPTRA_HOME / "gemini_config.json"
SUPPORTED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def load_gemini_config() -> Dict[str, Any]:
    default_cfg = {
        "enabled": False,
        "api_key": "",
        "model": "gemini-2.5-flash",
        "consent_transcript": False,
        "consent_video": False,
        "local_only_mode": True
    }
    if GEMINI_CONFIG_PATH.exists():
        try:
            saved = json.loads(GEMINI_CONFIG_PATH.read_text(encoding="utf-8"))
            default_cfg.update(saved)
        except Exception:
            pass
    return default_cfg

def save_gemini_config(cfg: Dict[str, Any]) -> bool:
    try:
        KLYPTRA_HOME.mkdir(parents=True, exist_ok=True)
        # Never store raw key unmasked in public displays, store securely in user AppData
        GEMINI_CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[GeminiService] Error saving config: {e}")
        return False

def test_gemini_connection(api_key: str, model: str = "gemini-2.5-flash") -> Dict[str, Any]:
    if not api_key or not api_key.strip():
        return {"success": False, "error": "No API key provided."}
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": "Reply with 'KLYPTRA_OK' only."}]
        }],
        "generationConfig": {
            "maxOutputTokens": 10
        }
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = ""
            if "candidates" in data and len(data["candidates"]) > 0:
                parts = data["candidates"][0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
            return {"success": True, "model": model, "reply": text}
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code}: {e.reason}"
        try:
            body = json.loads(e.read().decode("utf-8"))
            if "error" in body and "message" in body["error"]:
                error_msg = body["error"]["message"]
        except Exception:
            pass
        return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}

def enhance_clip_metadata(
    clip_title: str,
    transcript_segment: str,
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """Enhance clip titles, hooks, and hashtags using Gemini API if configured with explicit consent."""
    cfg = load_gemini_config()
    key = api_key or cfg.get("api_key")
    if not key or not cfg.get("enabled") or not cfg.get("consent_transcript") or cfg.get("local_only_mode"):
        # Local fallback heuristic
        return {
            "source": "local",
            "title": clip_title,
            "hook": transcript_segment[:80] + "..." if len(transcript_segment) > 80 else transcript_segment,
            "hashtags": ["#Shorts", "#Viral", "#KLYPTRA"]
        }
    
    prompt = (
        f"You are a short-form video editor. Given this clip transcript: '{transcript_segment}', "
        "provide a JSON object with: "
        "1. 'title': a punchy 4-7 word title, "
        "2. 'hook': a 1-sentence viral hook explanation, "
        "3. 'hashtags': an array of 4 relevant trending hashtags. "
        "Output ONLY raw valid JSON."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key.strip()}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 250}
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean possible markdown fencing
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            parsed = json.loads(raw_text.strip())
            parsed["source"] = "gemini"
            return parsed
    except Exception as e:
        print(f"[GeminiService] Enhancement error: {e}, falling back to local heuristic.")
        return {
            "source": "local_fallback",
            "title": clip_title,
            "hook": transcript_segment[:80] + "..." if len(transcript_segment) > 80 else transcript_segment,
            "hashtags": ["#Shorts", "#KLYPTRA"]
        }
