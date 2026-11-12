import os
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import yt_dlp
from .config import FFMPEG_EXE

logger = logging.getLogger(__name__)

# Strict YouTube URL matching regex
YOUTUBE_URL_REGEX = re.compile(
    r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?.*v=|shorts/|live/)|youtu\.be/)[a-zA-Z0-9_-]{6,}",
    re.IGNORECASE
)

class YouTubeError(Exception):
    pass

def validate_youtube_url(url: str) -> bool:
    """
    Validates whether the provided URL matches supported YouTube video formats:
    - youtube.com/watch?v=
    - youtu.be/
    - youtube.com/shorts/
    - youtube.com/live/
    """
    if not url or not isinstance(url, str):
        return False
    clean = url.strip()
    return bool(YOUTUBE_URL_REGEX.match(clean))

def fetch_youtube_metadata(url: str) -> Dict[str, Any]:
    """
    Extracts video metadata (title, thumbnail, duration, channel, formats) without downloading.
    """
    if not validate_youtube_url(url):
        raise YouTubeError("Invalid YouTube URL. Please provide a standard watch, shorts, or youtu.be link.")

    ydl_opts = {
        "extract_flat": False,
        "skip_download": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_EXE
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url.strip(), download=False)
            if not info:
                raise YouTubeError("Could not retrieve information for this video.")

            if info.get("is_live"):
                raise YouTubeError("Active live streams cannot be clipped until the broadcast is completed.")

            duration = info.get("duration", 0)
            formats = info.get("formats", [])

            # Check available heights
            heights = set()
            for f in formats:
                h = f.get("height")
                if h:
                    heights.add(h)

            resolutions = []
            if any(h >= 720 for h in heights):
                resolutions.append("720p")
            if any(h >= 1080 for h in heights):
                resolutions.append("1080p")
            resolutions.append("best")

            return {
                "id": info.get("id"),
                "title": info.get("title", "Untitled Video"),
                "channel": info.get("uploader", info.get("channel", "Unknown Channel")),
                "thumbnail": info.get("thumbnail"),
                "duration": round(float(duration), 1) if duration else 0.0,
                "duration_formatted": f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "0:00",
                "description": info.get("description", "")[:250],
                "webpage_url": info.get("webpage_url", url),
                "resolutions_available": resolutions
            }

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private video" in msg:
            raise YouTubeError("This video is private and cannot be accessed.")
        elif "Sign in to confirm your age" in msg:
            raise YouTubeError("This video requires age-gate sign in. Please import an authorized local copy.")
        elif "Video unavailable" in msg:
            raise YouTubeError("This video is unavailable or has been removed.")
        else:
            raise YouTubeError(f"YouTube metadata fetch error: {msg}")
    except Exception as e:
        raise YouTubeError(f"Failed to inspect YouTube URL: {str(e)}")

def download_youtube_video(
    url: str,
    output_dir: str,
    quality: str = "1080p",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_checker: Optional[Callable[[], bool]] = None
) -> str:
    """
    Downloads the selected YouTube video, merges audio & video with FFmpeg,
    and returns the saved local MP4 file path.
    """
    if not validate_youtube_url(url):
        raise YouTubeError("Invalid YouTube URL.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check disk space (minimum 500 MB)
    total, used, free = shutil.disk_usage(str(out_dir))
    if free < 500 * 1024 * 1024:
        raise YouTubeError("Insufficient disk space on output drive (at least 500MB required).")

    # Format selector
    if quality == "720p":
        format_sel = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best"
    elif quality == "best":
        format_sel = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:  # 1080p default
        format_sel = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]/best"

    out_template = str(out_dir / "%(id)s.%(ext)s")

    def ytdl_hook(d):
        if cancel_checker and cancel_checker():
            raise YouTubeError("Download cancelled by user.")

        if progress_callback:
            status = d.get("status")
            if status == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded_bytes = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0
                pct = round((downloaded_bytes / total_bytes) * 100.0, 1) if total_bytes > 0 else 0.0

                progress_callback({
                    "stage": "downloading",
                    "percent": pct,
                    "downloaded_mb": round(downloaded_bytes / (1024 * 1024), 1),
                    "total_mb": round(total_bytes / (1024 * 1024), 1),
                    "speed_mbps": round(speed / (1024 * 1024), 2) if speed else 0,
                    "eta_seconds": eta,
                    "message": f"Downloading stream ({pct}% - {round(downloaded_bytes / (1024 * 1024), 1)} MB)..."
                })
            elif status == "finished":
                progress_callback({
                    "stage": "merging",
                    "percent": 95.0,
                    "message": "Merging video and audio streams with FFmpeg..."
                })

    ydl_opts = {
        "format": format_sel,
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [ytdl_hook],
        "ffmpeg_location": FFMPEG_EXE
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if progress_callback:
                progress_callback({
                    "stage": "connecting",
                    "percent": 5.0,
                    "message": "Connecting to source and preparing stream..."
                })

            res = ydl.extract_info(url.strip(), download=True)
            video_id = res.get("id")

            # Find output file
            mp4_file = out_dir / f"{video_id}.mp4"
            if not mp4_file.exists():
                # Check if file has sanitized title name
                files = list(out_dir.glob(f"*{video_id}*.mp4"))
                if files:
                    mp4_file = files[0]
                else:
                    # Look for any mp4 in out_dir
                    all_mp4s = list(out_dir.glob("*.mp4"))
                    if all_mp4s:
                        mp4_file = all_mp4s[0]
                    else:
                        raise YouTubeError("Could not locate merged MP4 file after download.")

            return str(mp4_file.resolve())

    except yt_dlp.utils.DownloadError as e:
        raise YouTubeError(f"Download failed: {str(e)}")
    except Exception as e:
        if isinstance(e, YouTubeError):
            raise
        raise YouTubeError(f"YouTube processing encountered an error: {str(e)}")

