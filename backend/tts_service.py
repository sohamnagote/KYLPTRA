import os
import sys
import uuid
import base64
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import VOICEOVERS_DIR, get_win_subprocess_kwargs
from .ffmpeg_service import probe_video

VOICEOVERS_DIR.mkdir(parents=True, exist_ok=True)

def get_available_system_voices() -> List[str]:
    """
    Queries local Windows SpeechSynthesizer installed voices via PowerShell.
    Offline, fast, no external pip dependencies.
    """
    if sys.platform != "win32":
        return ["System Default"]

    ps_script = """
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }
    """

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=5,
            **get_win_subprocess_kwargs()
        )
        if res.returncode == 0:
            voices = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            if voices:
                return voices
    except Exception:
        pass

    return ["Microsoft David", "Microsoft Zira", "Microsoft Mark"]

def generate_offline_voiceover(
    text: str,
    voice: Optional[str] = "Microsoft David",
    speed: int = 0,
    volume: float = 1.0,
    output_wav_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates offline WAV audio from text using native Windows SAPI.
    """
    if not output_wav_path:
        out_file = VOICEOVERS_DIR / f"vo_{uuid.uuid4().hex[:8]}.wav"
    else:
        out_file = Path(output_wav_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Encode text to Base64 to guarantee 100% immunity to quotes, special chars, or multiline parser errors
    b64_text = base64.b64encode((text or "").encode("utf-8")).decode("ascii")
    sapi_rate = max(-10, min(10, int(speed)))
    sapi_vol = max(0, min(100, int(volume * 100)))
    safe_voice = (voice or "Microsoft David").replace("'", "").replace('"', '').replace("`", "")
    b64_voice = base64.b64encode(safe_voice.encode("utf-8")).decode("ascii")

    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {{
        $vName = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_voice}'))
        $synth.SelectVoice($vName)
    }} catch {{}}
    $synth.Rate = {sapi_rate}
    $synth.Volume = {sapi_vol}
    $synth.SetOutputToWaveFile('{str(out_file.resolve()).replace("'", "''")}')
    $bytes = [System.Convert]::FromBase64String('{b64_text}')
    $speakText = [System.Text.Encoding]::UTF8.GetString($bytes)
    $synth.Speak($speakText)
    $synth.Dispose()
    """

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            **get_win_subprocess_kwargs()
        )
        if res.returncode != 0 or not out_file.exists() or out_file.stat().st_size == 0:
            raise RuntimeError(f"TTS generation failed: {res.stderr}")

        dur = 0.0
        try:
            meta = probe_video(str(out_file))
            dur = meta.get("duration", 0.0)
        except Exception:
            dur = round(len(text.split()) / 2.5, 2)

        return {
            "output_path": str(out_file.resolve()),
            "duration": dur,
            "text": text,
            "voice": safe_voice,
            "file_size": out_file.stat().st_size
        }
    except Exception as e:
        raise RuntimeError(f"Offline voiceover synthesis error: {str(e)}")

