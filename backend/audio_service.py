import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import FFMPEG_EXE, get_win_subprocess_kwargs

# English and Hindi filler words/phrases
FILLER_WORDS = [
    "um", "uh", "umm", "uhh", "er", "ah",
    "you know", "like", "actually", "basically", "literally",
    "sort of", "kind of", "i mean", "right?",
    "matlab", "toh", "yaar", "achha", "na", "hai na"
]

def detect_silences(
    media_path: str,
    min_duration: float = 1.2,
    noise_threshold: str = "-32dB"
) -> List[Dict[str, float]]:
    """
    Detects silent pauses using FFmpeg silencedetect filter.
    Returns list of {'start': float, 'end': float, 'duration': float}.
    """
    path = Path(media_path)
    if not path.exists():
        return []

    cmd = [
        FFMPEG_EXE,
        "-i", str(path),
        "-af", f"silencedetect=noise={noise_threshold}:d={min_duration}",
        "-f", "null",
        "-"
    ]

    try:
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, **get_win_subprocess_kwargs())
        lines = res.stderr.splitlines()

        silences = []
        cur_start = None

        for line in lines:
            if "silence_start:" in line:
                m = re.search(r"silence_start:\s*([0-9.]+)", line)
                if m:
                    cur_start = float(m.group(1))
            elif "silence_end:" in line and cur_start is not None:
                m = re.search(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)", line)
                if m:
                    end_t = float(m.group(1))
                    dur = float(m.group(2))
                    silences.append({
                        "start": round(cur_start, 2),
                        "end": round(end_t, 2),
                        "duration": round(dur, 2)
                    })
                    cur_start = None

        return silences
    except Exception:
        return []

def detect_filler_words(transcript_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scans word-level timestamps in transcript data to identify common filler phrases.
    Returns list of {'word': str, 'start': float, 'end': float, 'type': 'filler'}.
    """
    detected = []
    segments = transcript_data.get("segments", [])

    for seg in segments:
        words = seg.get("words", [])
        if words:
            for w in words:
                clean = re.sub(r"[^\w\s]", "", w.get("word", "")).strip().lower()
                if clean in FILLER_WORDS:
                    detected.append({
                        "word": w.get("word", "").strip(),
                        "start": round(float(w.get("start", 0.0)), 2),
                        "end": round(float(w.get("end", 0.0)), 2),
                        "duration": round(float(w.get("end", 0.0)) - float(w.get("start", 0.0)), 2),
                        "type": "filler"
                    })
        else:
            # Sentence level fallback
            seg_text = seg.get("text", "").lower()
            for fw in FILLER_WORDS:
                pattern = r"\b" + re.escape(fw) + r"\b"
                for match in re.finditer(pattern, seg_text):
                    detected.append({
                        "word": fw,
                        "start": round(float(seg.get("start", 0.0)), 2),
                        "end": round(min(float(seg.get("end", 0.0)), float(seg.get("start", 0.0)) + 0.8), 2),
                        "duration": 0.8,
                        "type": "filler"
                    })

    return detected

