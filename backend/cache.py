import os
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from .config import CACHE_DIR

TRANSCRIPTS_CACHE_DIR = CACHE_DIR / "transcripts"
TRANSCRIPTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def compute_file_fingerprint(file_path: str) -> str:
    """
    Computes a fast SHA-256 fingerprint based on the file size and head/tail chunks.
    Execution takes milliseconds, even on multi-gigabyte video files.
    """
    p = Path(file_path)
    if not p.exists():
        return ""

    size = p.stat().st_size
    hasher = hashlib.sha256()
    hasher.update(str(size).encode("utf-8"))

    chunk_size = 1024 * 1024  # 1MB
    with open(p, "rb") as f:
        # Read head
        head = f.read(chunk_size)
        hasher.update(head)
        # Read tail if large enough
        if size > chunk_size * 2:
            f.seek(-chunk_size, os.SEEK_END)
            tail = f.read(chunk_size)
            hasher.update(tail)

    return hasher.hexdigest()

def get_transcript_cache_key(fingerprint: str, model_size: str, language: Optional[str], profile: str) -> str:
    raw = f"{fingerprint}_{model_size}_{language or 'auto'}_{profile}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def get_cached_transcript(cache_key: str) -> Optional[Dict[str, Any]]:
    if not cache_key:
        return None
    cache_file = TRANSCRIPTS_CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_cached_transcript(cache_key: str, data: Dict[str, Any]):
    if not cache_key:
        return
    cache_file = TRANSCRIPTS_CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

