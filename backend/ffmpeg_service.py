import os
import sys
import json
import subprocess
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from .config import FFMPEG_EXE, FFPROBE_EXE, get_win_subprocess_kwargs
from .hardware import detect_best_ffmpeg_encoder

ASSETS_DIR = Path(__file__).parent / "assets"
CASCADE_PATH = ASSETS_DIR / "haarcascade_frontalface_default.xml"

class FFmpegError(Exception):
    pass

def probe_video(file_path: str) -> Dict[str, Any]:
    """
    Extract real metadata using ffprobe.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Source video not found: {file_path}")

    cmd = [
        FFPROBE_EXE,
        "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name,codec_type",
        "-show_entries", "format=duration,size,format_name",
        "-of", "json",
        str(path)
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, **get_win_subprocess_kwargs())
        data = json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"FFprobe failed: {e.stderr}")
    except json.JSONDecodeError as e:
        raise FFmpegError(f"Invalid FFprobe output: {e}")

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise FFmpegError("No valid video stream found in the file.")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    codec = video_stream.get("codec_name", "unknown")

    # Frame rate calculation
    r_fps = video_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in r_fps:
            num, den = r_fps.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(r_fps)
    except Exception:
        fps = 30.0

    # Duration calculation
    duration_str = format_info.get("duration") or video_stream.get("duration", "0")
    try:
        duration = float(duration_str)
    except Exception:
        duration = 0.0

    # File size
    size_str = format_info.get("size", "0")
    try:
        file_size = int(size_str)
    except Exception:
        file_size = path.stat().st_size if path.exists() else 0

    return {
        "filename": path.name,
        "filepath": str(path.resolve()),
        "duration": round(duration, 2),
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "codec": codec,
        "has_audio": audio_stream is not None,
        "file_size": file_size
    }

def extract_audio(video_path: str, output_wav_path: str) -> str:
    """
    Extract 16kHz mono 16-bit WAV audio for Whisper transcription.
    """
    v_path = Path(video_path)
    o_path = Path(output_wav_path)
    o_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", str(v_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(o_path)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **get_win_subprocess_kwargs())
    if res.returncode != 0:
        raise FFmpegError(f"Audio extraction failed: {res.stderr}")

    if not o_path.exists() or o_path.stat().st_size == 0:
        raise FFmpegError("Extracted audio file is empty or missing.")

    return str(o_path)

def detect_face_center_x(video_path: str, start_sec: float = 0.0, duration: float = 10.0) -> float:
    """
    Detect the prominent face center X (normalized 0.0 to 1.0) across frames.
    Falls back to 0.5 (center) if no face detected or file unreadable.
    """
    res = detect_speaker_tracking_keyframes(video_path, start_sec, duration)
    return res.get("smoothed_center_x", 0.5)

def detect_speaker_tracking_keyframes(
    video_path: str,
    start_sec: float = 0.0,
    duration: float = 10.0,
    samples: int = 24
) -> Dict[str, Any]:
    """
    Detects face positions over time, speaker count, and smoothed crop center X.
    Provides speaker-tracking metadata to prevent distracting framing jumps.
    """
    default_result = {
        "smoothed_center_x": 0.5,
        "speaker_count": 1,
        "has_left_speaker": False,
        "has_right_speaker": False,
        "keyframes": []
    }

    if not CASCADE_PATH.exists():
        return default_result

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return default_result

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        start_frame = max(0, int(start_sec * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        face_cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
        centers_x = []
        left_faces = 0
        right_faces = 0
        keyframes = []

        total_frames = max(1, int(duration * fps))
        step_frames = max(1, int(total_frames / max(1, samples)))

        for i in range(samples):
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50))

            frame_time = round(start_sec + (i * step_frames / fps), 2)

            if len(faces) > 0:
                largest = max(faces, key=lambda f: f[2] * f[3])
                cx = (largest[0] + largest[2] / 2.0) / float(w)
                centers_x.append(cx)
                keyframes.append({"time": frame_time, "center_x": round(cx, 3)})

                for f in faces:
                    fcx = (f[0] + f[2] / 2.0) / float(w)
                    if fcx < 0.45:
                        left_faces += 1
                    elif fcx > 0.55:
                        right_faces += 1

            for _ in range(step_frames - 1):
                cap.grab()

        if not centers_x:
            return default_result

        # Exponential moving average smoothing for camera tracking
        smoothed = centers_x[0]
        alpha = 0.3
        for val in centers_x[1:]:
            smoothed = (alpha * val) + ((1.0 - alpha) * smoothed)

        speaker_cnt = 2 if (left_faces >= 3 and right_faces >= 3) else 1

        return {
            "smoothed_center_x": round(float(smoothed), 3),
            "speaker_count": speaker_cnt,
            "has_left_speaker": left_faces >= 3,
            "has_right_speaker": right_faces >= 3,
            "keyframes": keyframes
        }

    except Exception:
        return default_result
    finally:
        cap.release()

def color_to_ass_hex(hex_str: str, alpha: int = 0) -> str:
    clean = (hex_str or "").lstrip("#")
    if len(clean) == 6:
        r, g, b = clean[0:2], clean[2:4], clean[4:6]
        return f"&H{alpha:02X}{b}{g}{r}&"
    elif len(clean) == 8:
        r, g, b, a = clean[0:2], clean[2:4], clean[4:6], clean[6:8]
        return f"&H{a}{b}{g}{r}&"
    return f"&H{alpha:02X}FFFFFF&"

def generate_ass_subtitle(
    segments_or_words: List[Dict[str, Any]],
    output_ass_path: str,
    font_name: str = "Inter",
    font_size: int = 24,
    color: str = "#FFFFFF",
    highlight_color: str = "#8B5CF6",
    bg_color: Optional[str] = None,
    outline_color: Optional[str] = None,
    position: str = "bottom",
    animation: str = "Fade",
    preset_name: Optional[str] = None,
    words_per_line: int = 4,
    highlight_words: bool = True,
    animation_speed: float = 1.0,
    video_width: int = 1080,
    video_height: int = 1920,
    primary_color: Optional[str] = None
) -> str:
    """
    Generates professional ASS subtitle files supporting all 15 styling presets,
    Hindi/Devanagari scripts (Nirmala UI), karaoke word highlighting, and fluid animations.
    """
    if primary_color:
        color = primary_color
    out_path = Path(output_ass_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Preset override handling
    preset_lower = (preset_name or "").lower().strip()
    border_style = 1  # 1 = outline + shadow, 3 = opaque box
    outline_thickness = 3.5
    shadow_depth = 1.5

    if "box" in preset_lower or (bg_color and len(bg_color) > 3):
        border_style = 3  # Opaque background box
        outline_thickness = 6.0
        shadow_depth = 0.0

    if "cinematic" in preset_lower:
        outline_thickness = 2.0
        shadow_depth = 2.0
    elif "gaming" in preset_lower:
        font_size = max(font_size, 30)
        outline_thickness = 4.5
    elif "neon" in preset_lower:
        outline_thickness = 5.0
        shadow_depth = 3.0
    elif "minimal outline" in preset_lower:
        outline_thickness = 4.0
        shadow_depth = 0.0

    ass_primary = color_to_ass_hex(color, 0)
    ass_highlight = color_to_ass_hex(highlight_color, 0)
    ass_outline = color_to_ass_hex(outline_color or "#181818", 0)
    ass_bg = color_to_ass_hex(bg_color or "#181818", 64) if bg_color else "&H80000000&"

    alignment_map = {"bottom": 2, "middle": 5, "top": 8}
    alignment = alignment_map.get(position, 2)
    margin_v = 150 if position == "bottom" else (70 if position == "top" else 0)

    # Automatically select Nirmala UI if Hindi/Devanagari text or font chosen
    selected_font = font_name or "Inter"
    if any(k in selected_font.lower() for k in ["hindi", "devanagari", "nirmala"]):
        selected_font = "Nirmala UI"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{selected_font},{font_size},{ass_primary},{ass_highlight},{ass_outline},{ass_bg},1,0,0,0,100,100,0,0,{border_style},{outline_thickness},{shadow_depth},{alignment},40,40,{margin_v},1
Style: Highlight,{selected_font},{font_size},{ass_highlight},{ass_primary},{ass_outline},{ass_bg},1,0,0,0,100,100,0,0,{border_style},{outline_thickness},{shadow_depth},{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    # Build ASS animation tag prefix
    anim_tag = ""
    anim_lower = (animation or "Fade").lower().strip()
    
    fade_dur = max(60, int(130 / max(0.5, animation_speed)))
    if anim_lower == "minimal fade":
        anim_tag = "{\\fad(70,70)}"
    elif "fade" in anim_lower:
        anim_tag = f"{{\\fad({fade_dur},{fade_dur})}}"
    elif anim_lower == "elastic pop":
        anim_tag = "{\\t(0,80,\\fscx125\\fscy125)\\t(80,150,\\fscx95\\fscy95)\\t(150,220,\\fscx100\\fscy100)}"
    elif "pop" in anim_lower:
        anim_tag = "{\\t(0,80,\\fscx115\\fscy115)\\t(80,160,\\fscx100\\fscy100)}"
    elif "bounce" in anim_lower:
        anim_tag = "{\\t(0,90,\\fscy125)\\t(90,180,\\fscy100)}"
    elif anim_lower == "scale":
        anim_tag = "{\\fscx82\\fscy82\\t(0,180,\\fscx100\\fscy100)}"
    elif "slide up" in anim_lower:
        anim_tag = f"{{\\move({video_width//2},{video_height - margin_v + 35},{video_width//2},{video_height - margin_v},0,180)}}"
    elif "slide down" in anim_lower:
        anim_tag = f"{{\\move({video_width//2},{video_height - margin_v - 35},{video_width//2},{video_height - margin_v},0,180)}}"
    elif "zoom" in anim_lower:
        anim_tag = "{\\fscx92\\fscy92\\t(0,250,\\fscx100\\fscy100)}"
    elif "sweep" in anim_lower:
        anim_tag = f"{{\\t(0,180,\\c{ass_highlight})\\t(180,360,\\c{ass_primary})}}"
    elif "gradient" in anim_lower:
        anim_tag = f"{{\\t(0,160,\\c{ass_highlight})\\t(160,320,\\c{ass_primary})}}"
    elif "typewriter" in anim_lower:
        anim_tag = "{\\fad(0,0)\\t(0,220,\\alpha&H00&)}"
    elif "character" in anim_lower:
        anim_tag = "{\\fad(50,50)\\t(0,180,\\fscx106\\fscy106)\\t(180,280,\\fscx100\\fscy100)}"
    elif "reveal" in anim_lower:
        anim_tag = f"{{\\t(0,150,\\c{ass_highlight})\\t(150,280,\\c{ass_primary})}}"

    lines = [header]

    for seg in segments_or_words:
        seg_words = seg.get("words", [])
        start_t = max(0.0, float(seg.get("start", 0.0)))
        end_t = max(start_t + 0.2, float(seg.get("end", 0.0)))
        raw_text = seg.get("text", "").strip()
        if not raw_text:
            continue

        # If word timestamps are available and karaoke / active word highlighting is desired
        if highlight_words and seg_words and ("karaoke" in anim_lower or "reveal" in anim_lower):
            for w_idx, w in enumerate(seg_words):
                w_st = max(0.0, float(w.get("start", start_t)))
                w_et = max(w_st + 0.15, float(w.get("end", end_t)))
                
                # Construct formatted phrase highlighting current word
                phrase_parts = []
                for j, other_w in enumerate(seg_words):
                    clean_w_text = other_w.get("word", "").replace("\n", " ").strip()
                    if j == w_idx:
                        phrase_parts.append(f"{{\\c{ass_highlight}\\b1}}{clean_w_text}{{\\c{ass_primary}\\b0}}")
                    else:
                        phrase_parts.append(clean_w_text)
                
                line_content = " ".join(phrase_parts).replace("\n", "\\N")
                lines.append(f"Dialogue: 0,{fmt_time(w_st)},{fmt_time(w_et)},Default,,0,0,0,,{anim_tag}{line_content}\n")
        else:
            clean_text = raw_text.replace("\n", "\\N").replace("{", "(").replace("}", ")")
            lines.append(f"Dialogue: 0,{fmt_time(start_t)},{fmt_time(end_t)},Default,,0,0,0,,{anim_tag}{clean_text}\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return str(out_path)

def escape_ffmpeg_filter_path(file_path: str) -> str:
    p = str(Path(file_path).resolve()).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p

def render_clip(
    source_path: str,
    output_path: str,
    start_time: float,
    duration: float,
    aspect_ratio: str = "9:16",
    reframing_mode: str = "single",
    crop_x: float = 0.5,
    crop_y: float = 0.5,
    subtitle_path: Optional[str] = None,
    watermark_path: Optional[str] = None,
    watermark_position: str = "top-right",
    watermark_opacity: float = 0.85,
    audio_denoise: bool = False,
    audio_normalize: bool = False,
    audio_clarity: bool = False,
    bg_music_path: Optional[str] = None,
    bg_music_volume: float = 0.2,
    music_ducking: bool = False,
    resolution: str = "1080p",
    fps: int = 30,
    volume: float = 1.0,
    is_muted: bool = False,
    use_gpu: bool = True
) -> Dict[str, Any]:
    """
    Render a real, verified MP4 clip using optimized FFmpeg encoding.
    Supports all aspect ratios (9:16, 1:1, 4:5, 16:9), reframing layouts,
    audio cleanup filters, BGM mixing with ducking, and watermark branding.
    """
    src = Path(source_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Source video not found: {source_path}")

    meta = probe_video(str(src))
    src_w = meta["width"]
    src_h = meta["height"]

    # Target resolution dimensions
    res_lower = (resolution or "1080p").lower()
    if res_lower == "4k":
        if aspect_ratio == "9:16":
            out_w, out_h = (2160, 3840)
        elif aspect_ratio == "1:1":
            out_w, out_h = (2160, 2160)
        elif aspect_ratio == "4:5":
            out_w, out_h = (2160, 2700)
        else:  # 16:9
            out_w, out_h = (3840, 2160)
    elif res_lower == "720p":
        if aspect_ratio == "9:16":
            out_w, out_h = (720, 1280)
        elif aspect_ratio == "1:1":
            out_w, out_h = (720, 720)
        elif aspect_ratio == "4:5":
            out_w, out_h = (720, 900)
        else:  # 16:9
            out_w, out_h = (1280, 720)
    else:  # 1080p default
        if aspect_ratio == "9:16":
            out_w, out_h = (1080, 1920)
        elif aspect_ratio == "1:1":
            out_w, out_h = (1080, 1080)
        elif aspect_ratio == "4:5":
            out_w, out_h = (1080, 1350)
        else:  # 16:9
            out_w, out_h = (1920, 1080)

    # 1. Video Reframing Filter Construction
    mode = (reframing_mode or "single").lower()

    if mode == "blur_fill":
        crop_filter = (
            f"split=2[bg_in][fg_in];"
            f"[bg_in]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=25:5[bg];"
            f"[fg_in]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
    elif mode == "stacked" and aspect_ratio == "9:16":
        # Two speakers or speaker + presentation stacked vertically
        crop_filter = (
            f"split=2[top_in][bot_in];"
            f"[top_in]crop=iw/2:ih:0:0,scale={out_w}:{out_h//2}[top];"
            f"[bot_in]crop=iw/2:ih:iw/2:0,scale={out_w}:{out_h//2}[bot];"
            f"[top][bot]vstack"
        )
    elif mode == "side_by_side":
        crop_filter = (
            f"split=2[left_in][right_in];"
            f"[left_in]crop=iw/2:ih:0:0,scale={out_w//2}:{out_h}[left];"
            f"[right_in]crop=iw/2:ih:iw/2:0,scale={out_w//2}:{out_h}[right];"
            f"[left][right]hstack"
        )
    elif mode == "pip":
        crop_filter = (
            f"split=2[main_in][inset_in];"
            f"[main_in]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2[main];"
            f"[inset_in]crop=min(iw\\,ih):min(iw\\,ih),scale={out_w//3}:{out_h//3}[inset];"
            f"[main][inset]overlay=W-w-30:30"
        )
    else:
        # Standard intelligent face-aware cropping
        if aspect_ratio == "9:16":
            target_crop_w = int(src_h * 9.0 / 16.0)
            if target_crop_w > src_w:
                crop_box_w = src_w
                crop_box_h = int(src_w * 16.0 / 9.0)
                offset_x = 0
                offset_y = int((src_h - crop_box_h) * crop_y)
            else:
                crop_box_w = target_crop_w
                crop_box_h = src_h
                max_x = max(0, src_w - crop_box_w)
                offset_x = int(max_x * crop_x)
                offset_y = 0
            crop_filter = f"crop={crop_box_w}:{crop_box_h}:{offset_x}:{offset_y},scale={out_w}:{out_h}"
        elif aspect_ratio == "4:5":
            target_crop_w = int(src_h * 4.0 / 5.0)
            if target_crop_w > src_w:
                crop_box_w = src_w
                crop_box_h = int(src_w * 5.0 / 4.0)
                offset_x = 0
                offset_y = int((src_h - crop_box_h) * crop_y)
            else:
                crop_box_w = target_crop_w
                crop_box_h = src_h
                offset_x = int(max(0, src_w - crop_box_w) * crop_x)
                offset_y = 0
            crop_filter = f"crop={crop_box_w}:{crop_box_h}:{offset_x}:{offset_y},scale={out_w}:{out_h}"
        elif aspect_ratio == "1:1":
            side = min(src_w, src_h)
            offset_x = int((src_w - side) * crop_x)
            offset_y = int((src_h - side) * crop_y)
            crop_filter = f"crop={side}:{side}:{offset_x}:{offset_y},scale={out_w}:{out_h}"
        else:  # 16:9
            crop_filter = f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2"

    vf = crop_filter

    # Watermark overlay if provided
    has_watermark = watermark_path and Path(watermark_path).exists()
    if has_watermark:
        wm_esc = escape_ffmpeg_filter_path(watermark_path)
        wm_pos_map = {
            "top-left": "25:25",
            "top-right": "W-w-25:25",
            "bottom-left": "25:H-h-25",
            "bottom-right": "W-w-25:H-h-25"
        }
        wm_coord = wm_pos_map.get(watermark_position, "W-w-25:25")
        wm_scale = int(out_w * 0.18)
        vf = f"{vf}[vbase];movie='{wm_esc}',scale={wm_scale}:-1,format=rgba,colorchannelmixer=aa={watermark_opacity:.2f}[wm];[vbase][wm]overlay={wm_coord}"

    # Subtitles
    if subtitle_path and Path(subtitle_path).exists():
        escaped_sub = escape_ffmpeg_filter_path(subtitle_path)
        vf = f"{vf},ass='{escaped_sub}'"

    filter_complex = vf

    # 2. Audio Processing Filters
    af_filters = []
    if audio_denoise:
        af_filters.append("afftdn=nr=12:nf=-30")
    if audio_clarity:
        af_filters.append("equalizer=f=3000:t=q:w=1:g=3.5,equalizer=f=250:t=q:w=1:g=-2")
    if audio_normalize:
        af_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    vol = max(0.0, min(3.0, volume))
    if vol != 1.0:
        af_filters.append(f"volume={vol:.2f}")

    audio_filter_str = ",".join(af_filters) if af_filters else None

    # Audio command args
    audio_args = []
    if is_muted or not meta["has_audio"]:
        audio_args = ["-an"]
    else:
        audio_args = ["-c:a", "aac", "-b:a", "192k"]
        if audio_filter_str:
            audio_args.extend(["-filter:a", audio_filter_str])

    # Base render command
    base_cmd = [
        FFMPEG_EXE,
        "-y",
        "-ss", f"{start_time:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(src),
    ]

    # Handle BGM mixing if specified
    if bg_music_path and Path(bg_music_path).exists() and not is_muted:
        base_cmd.extend(["-stream_loop", "-1", "-i", str(bg_music_path)])
        bg_vol = max(0.0, min(1.0, bg_music_volume))
        if meta.get("has_audio", True):
            duck_filter = f"[1:a]volume={bg_vol:.2f}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            # If ducking active, use sidechain
            if music_ducking:
                duck_filter = f"[1:a]volume={bg_vol:.2f}[bgm];[bgm][0:a]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=350[ducked];[0:a][ducked]amix=inputs=2:duration=first[aout]"
            audio_args = ["-filter_complex", duck_filter, "-map", "0:v", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
        else:
            # Video stream has no audio, use BGM directly
            bg_filter = f"[1:a]volume={bg_vol:.2f}[aout]"
            audio_args = ["-filter_complex", bg_filter, "-map", "0:v", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]

    base_cmd.extend(["-vf", filter_complex, "-r", str(fps)])

    # Encoder detection
    best_enc = detect_best_ffmpeg_encoder(FFMPEG_EXE) if use_gpu else {
        "encoder": "libx264",
        "args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"]
    }

    enc_args = list(best_enc["args"])
    if "-pix_fmt" not in enc_args:
        enc_args.extend(["-pix_fmt", "yuv420p"])

    cmd = base_cmd + enc_args + audio_args + ["-movflags", "+faststart", str(out)]
    run_res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **get_win_subprocess_kwargs())

    if run_res.returncode == 0 and out.exists() and out.stat().st_size > 0:
        return validate_and_return_render(str(out), out_w, out_h)

    # Fallback to libx264 CPU encoding if preferred encoder or complex filter failed
    fallback_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"]
    fallback_cmd = base_cmd + fallback_args + audio_args + ["-movflags", "+faststart", str(out)]
    fallback_res = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **get_win_subprocess_kwargs())

    if fallback_res.returncode != 0:
        raise FFmpegError(f"Rendering failed: {fallback_res.stderr}")

    return validate_and_return_render(str(out), out_w, out_h)

def validate_and_return_render(output_path: str, expected_w: int, expected_h: int) -> Dict[str, Any]:
    out = Path(output_path)
    if not out.exists() or out.stat().st_size == 0:
        raise FFmpegError(f"Rendered file is missing or has zero size: {output_path}")

    meta = probe_video(str(out))
    if meta["duration"] <= 0:
        raise FFmpegError("Rendered video duration is 0 seconds.")

    return {
        "output_path": str(out.resolve()),
        "duration": meta["duration"],
        "width": meta["width"],
        "height": meta["height"],
        "file_size": meta["file_size"],
        "codec": meta["codec"]
    }
