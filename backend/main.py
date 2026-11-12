
import os
import sys
import hmac
import shutil
import uuid
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import (
    KLYPTRA_HOME, PROJECTS_DIR, EXPORTS_DIR, MODELS_DIR, CACHE_DIR,
    TEMP_CACHE_DIR, RENDERS_CACHE_DIR, LOGS_DIR, BROLL_DIR, BRANDS_DIR, VOICEOVERS_DIR,
    DEFAULT_WHISPER_MODEL, AVAILABLE_WHISPER_MODELS,
    FFMPEG_EXE, FFPROBE_EXE, init_storage_directories,
    get_models_dir, set_models_dir, is_production, get_resource_root,
    MAX_UPLOAD_BYTES, ALLOWED_VIDEO_EXTENSIONS, ALLOWED_MEDIA_EXTENSIONS
)
from .database import (
    init_db, create_project, get_project, list_projects,
    update_project_status, delete_project,
    create_clips_batch, get_clip, list_clips_for_project,
    update_clip, create_export, get_export, list_exports, delete_export,
    delete_clips_for_project, get_all_settings, get_setting,
    update_settings, reset_settings,
    list_caption_presets, get_caption_preset, create_caption_preset, update_caption_preset, delete_caption_preset,
    list_brand_profiles, get_brand_profile, create_brand_profile, update_brand_profile, delete_brand_profile,
    list_broll_assets, get_broll_asset, create_broll_asset, delete_broll_asset,
    list_voiceovers, get_voiceover, create_voiceover, delete_voiceover
)
from .ffmpeg_service import (
    probe_video, extract_audio, detect_face_center_x, detect_speaker_tracking_keyframes,
    generate_ass_subtitle, render_clip, FFmpegError
)
from .transcription import transcribe_audio_file
from .clip_engine import detect_clip_candidates, generate_clip_suggestions
from .audio_service import detect_silences, detect_filler_words
from .broll_service import match_broll_suggestions, MOTION_GRAPHICS_TEMPLATES
from .tts_service import get_available_system_voices, generate_offline_voiceover
from .export_service import generate_srt, generate_vtt, generate_premiere_xml
from .tasks import create_task, update_task, get_task, cancel_task, is_task_cancelled
from .hardware import (
    get_system_hardware_profile, clear_hardware_cache,
    run_gpu_test, run_ffmpeg_test, get_ram_info, get_cpu_info, get_storage_info
)
from .queue_manager import enqueue_transcription, enqueue_render
from .youtube_service import validate_youtube_url, fetch_youtube_metadata, download_youtube_video, YouTubeError

# Initialize storage and database
init_storage_directories()
init_db()

# Configure persistent logging
log_file = LOGS_DIR / "klyptra.log"
file_handler = RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger = logging.getLogger("klyptra")
logger.setLevel(logging.INFO)
if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
    logger.addHandler(file_handler)

_PROD = is_production()
_SESSION_TOKEN = os.environ.get("KLYPTRA_SESSION_TOKEN", "").strip()

app = FastAPI(
    title="KLYPTRA API",
    version="1.0.0",
    docs_url=None if _PROD else "/docs",
    redoc_url=None if _PROD else "/redoc",
    openapi_url=None if _PROD else "/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Klyptra-Token", "Range"],
)

@app.middleware("http")
async def session_token_guard(request: Request, call_next):
    """
    When running inside the standalone desktop shell (KLYPTRA_SESSION_TOKEN set),
    protect all /api/* routes (except /api/health) against unauthorized local requests.
    """
    if _SESSION_TOKEN and request.url.path.startswith("/api/") and request.url.path != "/api/health":
        header_token = request.headers.get("X-Klyptra-Token", "")
        query_token = request.query_params.get("token", "") if request.url.path == "/api/media/stream" else ""
        provided = header_token or query_token
        if not provided or not hmac.compare_digest(provided, _SESSION_TOKEN):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized local session."})
    return await call_next(request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal processing error occurred. Check Application Logs for details."}
    )

def _is_path_within(child: Path, parent: Path) -> bool:
    try:
        return child.resolve().is_relative_to(parent.resolve())
    except Exception:
        return False

def _validate_safe_media_path(raw_path: str) -> Path:
    """Prevent path traversal and arbitrary file reads outside managed KLYPTRA directories."""
    if not raw_path or ".." in Path(raw_path).parts:
        raise HTTPException(status_code=403, detail="Invalid media file path.")
    p = Path(raw_path).resolve()
    if p.suffix.lower() not in ALLOWED_MEDIA_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Unsupported media file type.")
    if not _is_path_within(p, KLYPTRA_HOME):
        # Allow reading if it is explicitly registered as a project source or export in the DB
        allowed_roots = [KLYPTRA_HOME.resolve()]
        if not any(_is_path_within(p, r) for r in allowed_roots):
            raise HTTPException(status_code=403, detail="Access outside KLYPTRA workspace is not permitted.")
    return p

# ----------------- Request Models -----------------

class YouTubeInspectRequest(BaseModel):
    url: str

class YouTubeImportRequest(BaseModel):
    url: str
    quality: Optional[str] = "1080p"
    confirm_authorized: bool = False

class ClipUpdateRequest(BaseModel):
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    aspect_ratio: Optional[str] = None
    crop_x: Optional[float] = None
    crop_y: Optional[float] = None
    captions_enabled: Optional[bool] = None
    caption_text: Optional[str] = None
    caption_font: Optional[str] = None
    caption_size: Optional[int] = None
    caption_color: Optional[str] = None
    caption_highlight_color: Optional[str] = None
    caption_position: Optional[str] = None
    caption_preset: Optional[str] = None
    caption_animation: Optional[str] = None
    caption_speed: Optional[float] = None
    caption_intensity: Optional[float] = None
    caption_words_per_line: Optional[int] = None
    caption_highlight_words: Optional[bool] = None
    reframing_mode: Optional[str] = None
    volume: Optional[float] = None
    is_muted: Optional[bool] = None
    audio_denoise: Optional[bool] = None
    audio_normalize: Optional[bool] = None
    audio_clarity: Optional[bool] = None
    filler_removal: Optional[bool] = None
    music_ducking: Optional[bool] = None
    bg_music_path: Optional[str] = None
    bg_music_volume: Optional[float] = None
    brand_profile_id: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    overlays: Optional[List[Dict[str, Any]]] = None

class RegenerateSuggestionsRequest(BaseModel):
    custom_instruction: Optional[str] = None

class CaptionPresetCreateRequest(BaseModel):
    name: str
    font_name: Optional[str] = "Inter"
    font_size: Optional[int] = 24
    primary_color: Optional[str] = "#FFFFFF"
    highlight_color: Optional[str] = "#8273D6"
    bg_color: Optional[str] = ""
    outline_color: Optional[str] = "#181818"
    position: Optional[str] = "bottom"
    animation: Optional[str] = "Fade"
    words_per_line: Optional[int] = 4
    max_line_length: Optional[int] = 26

class CaptionPresetUpdateRequest(BaseModel):
    name: Optional[str] = None
    font_name: Optional[str] = None
    font_size: Optional[int] = None
    primary_color: Optional[str] = None
    highlight_color: Optional[str] = None
    bg_color: Optional[str] = None
    outline_color: Optional[str] = None
    position: Optional[str] = None
    animation: Optional[str] = None
    words_per_line: Optional[int] = None
    max_line_length: Optional[int] = None

class ApplyPresetRequest(BaseModel):
    preset_id: str
    clip_ids: Optional[List[str]] = None

class BrandProfileCreateRequest(BaseModel):
    name: str
    logo_path: Optional[str] = None
    primary_color: Optional[str] = "#8273D6"
    secondary_color: Optional[str] = "#F0EDFC"
    caption_font: Optional[str] = "Inter"
    caption_preset_id: Optional[str] = "preset-minimal-clean"
    watermark_path: Optional[str] = None
    watermark_position: Optional[str] = "top-right"
    watermark_opacity: Optional[float] = 0.85
    intro_path: Optional[str] = None
    outro_path: Optional[str] = None
    default_aspect_ratio: Optional[str] = "9:16"
    default_quality: Optional[str] = "1080p"

class BrandProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    logo_path: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    caption_font: Optional[str] = None
    caption_preset_id: Optional[str] = None
    watermark_path: Optional[str] = None
    watermark_position: Optional[str] = None
    watermark_opacity: Optional[float] = None
    intro_path: Optional[str] = None
    outro_path: Optional[str] = None
    default_aspect_ratio: Optional[str] = None
    default_quality: Optional[str] = None

class ApplyBrandRequest(BaseModel):
    brand_id: str
    clip_ids: Optional[List[str]] = None

class VoiceoverGenerateRequest(BaseModel):
    text: str
    voice: Optional[str] = "Microsoft David"
    speed: Optional[int] = 0
    volume: Optional[float] = 1.0
    project_id: Optional[str] = None
    clip_id: Optional[str] = None

class SubtitleExportRequest(BaseModel):
    format: Optional[str] = "srt"  # srt, vtt, txt

class ExportRequest(BaseModel):
    resolution: Optional[str] = "1080p"
    fps: Optional[int] = 30
    aspect_ratio: Optional[str] = None
    destination_folder: Optional[str] = None
    filename: Optional[str] = None

class BatchExportRequest(BaseModel):
    clip_ids: Optional[List[str]] = None
    resolution: Optional[str] = "1080p"
    fps: Optional[int] = 30
    destination_folder: Optional[str] = None

class OpenFolderRequest(BaseModel):
    path: str

class ModelDownloadRequest(BaseModel):
    model_name: str

# ----------------- System & Health Endpoints -----------------

@app.api_route("/api/health", methods=["GET", "HEAD"])
def health_check():
    return {
        "status": "ok",
        "app": "KLYPTRA",
        "version": "2.0.0",
        "storage": str(KLYPTRA_HOME)
    }

@app.get("/api/system-info")
def system_info():
    hw = get_system_hardware_profile(FFMPEG_EXE)
    settings = get_all_settings()
    active_model = settings.get("whisper_model", DEFAULT_WHISPER_MODEL)
    return {
        "gpu_acceleration": hw["is_gpu_accelerated"],
        "device_description": hw["whisper"]["description"],
        "gpu": hw["gpu"],
        "gpu_name": hw["gpu"]["name"],
        "gpu_driver": hw["gpu"]["driver_version"],
        "vram_free_mb": hw["gpu"]["vram_free_mb"],
        "vram_total_mb": hw["gpu"]["vram_total_mb"],
        "video_encoder": hw["video_encoder"]["description"],
        "video_encoder_name": hw["video_encoder"]["encoder"],
        "video_encoder_is_hardware": hw["video_encoder"]["is_hardware"],
        "cpu": hw.get("cpu", {}),
        "ram": hw.get("ram", {}),
        "storage": hw.get("storage", {}),
        "ffmpeg": hw.get("ffmpeg", {}),
        "models_available": AVAILABLE_WHISPER_MODELS,
        "active_model": active_model,
        "default_model": DEFAULT_WHISPER_MODEL,
        "ffmpeg_path": FFMPEG_EXE,
        "ffprobe_path": FFPROBE_EXE,
        "disk_free_gb": hw.get("storage", {}).get("free_gb", 0),
        "disk_total_gb": hw.get("storage", {}).get("total_gb", 0)
    }

# ----------------- YouTube Import Endpoints -----------------

@app.post("/api/youtube/inspect")
def inspect_youtube_link(req: YouTubeInspectRequest):
    if not validate_youtube_url(req.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a standard YouTube video link (watch, shorts, or youtu.be)."
        )
    try:
        meta = fetch_youtube_metadata(req.url)
        return meta
    except YouTubeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/api/youtube/import")
def import_youtube_video(req: YouTubeImportRequest):
    if not req.confirm_authorized:
        raise HTTPException(
            status_code=400,
            detail="Authorization required: You must confirm that you own this content or have permission to edit it."
        )

    if not validate_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")

    project_id = str(uuid.uuid4())
    proj_dir = PROJECTS_DIR / project_id
    source_dir = proj_dir / "source"
    for sub in ["source", "audio", "transcripts", "clips", "previews", "exports"]:
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)

    task_id = create_task("youtube_download", "Downloading video from YouTube", {"project_id": project_id, "url": req.url})

    def run_download():
        try:
            def on_progress(p_data):
                update_task(
                    task_id,
                    progress=p_data.get("percent", 0.0),
                    message=p_data.get("message", "Downloading video...")
                )

            downloaded_path = download_youtube_video(
                url=req.url,
                output_dir=str(source_dir),
                quality=req.quality or "1080p",
                progress_callback=on_progress,
                cancel_checker=lambda: is_task_cancelled(task_id)
            )

            # Probe real downloaded video metadata
            update_task(task_id, progress=98.0, message="Inspecting downloaded stream metadata...")
            meta = probe_video(downloaded_path)

            title = Path(downloaded_path).stem.replace("_", " ").title()
            proj = create_project(
                project_id=project_id,
                name=title,
                source_filename=meta["filename"],
                source_path=str(Path(downloaded_path).resolve()),
                duration=meta["duration"],
                width=meta["width"],
                height=meta["height"],
                fps=meta["fps"],
                codec=meta["codec"],
                has_audio=meta["has_audio"],
                file_size=meta["file_size"]
            )

            update_task(task_id, progress=100.0, message="Import complete!", status="completed", result=proj)

        except Exception as e:
            err_msg = str(e)
            update_task(task_id, status="error", error=err_msg, message=f"Download failed: {err_msg}")
            # Clean up empty project directory on failure
            if proj_dir.exists():
                shutil.rmtree(str(proj_dir), ignore_errors=True)

    enqueue_render(task_id, run_download)
    return {"task_id": task_id, "project_id": project_id, "status": "processing"}

# ----------------- Project Endpoints -----------------

@app.get("/api/projects")
def get_all_projects():
    return list_projects()

@app.get("/api/projects/{project_id}")
def get_single_project(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.delete("/api/projects/{project_id}")
def remove_project(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    proj_dir = PROJECTS_DIR / project_id
    if proj_dir.exists():
        try:
            shutil.rmtree(str(proj_dir), ignore_errors=True)
        except Exception:
            pass

    deleted = delete_project(project_id)
    return {"success": deleted}

@app.post("/api/projects/upload")
async def upload_video(
    file: Optional[UploadFile] = File(None),
    filepath: Optional[str] = Form(None)
):
    project_id = str(uuid.uuid4())
    proj_dir = PROJECTS_DIR / project_id
    for d in ["source", "audio", "transcripts", "clips", "previews", "exports"]:
        (proj_dir / d).mkdir(parents=True, exist_ok=True)

    dest_video_path = None

    if file and file.filename:
        safe_name = Path(file.filename).name
        if Path(safe_name).suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
            shutil.rmtree(str(proj_dir), ignore_errors=True)
            raise HTTPException(status_code=400, detail="Unsupported video format. Supported formats: MP4, MOV, MKV, WEBM, AVI, M4V.")
        dest_video_path = proj_dir / "source" / safe_name
        total_written = 0
        with open(dest_video_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > MAX_UPLOAD_BYTES:
                    buffer.close()
                    shutil.rmtree(str(proj_dir), ignore_errors=True)
                    raise HTTPException(status_code=413, detail="Video exceeds maximum allowed size (10 GB).")
                buffer.write(chunk)
    elif filepath:
        src_path = Path(filepath).resolve()
        if not src_path.exists() or not src_path.is_file():
            shutil.rmtree(str(proj_dir), ignore_errors=True)
            raise HTTPException(status_code=400, detail="Specified video file does not exist.")
        if src_path.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
            shutil.rmtree(str(proj_dir), ignore_errors=True)
            raise HTTPException(status_code=400, detail="Unsupported video format. Supported formats: MP4, MOV, MKV, WEBM, AVI, M4V.")
        if src_path.stat().st_size > MAX_UPLOAD_BYTES:
            shutil.rmtree(str(proj_dir), ignore_errors=True)
            raise HTTPException(status_code=413, detail="Video exceeds maximum allowed size (10 GB).")
        dest_video_path = proj_dir / "source" / src_path.name
        shutil.copy2(str(src_path), str(dest_video_path))
    else:
        shutil.rmtree(str(proj_dir), ignore_errors=True)
        raise HTTPException(status_code=400, detail="No video file or valid filepath provided.")

    try:
        meta = probe_video(str(dest_video_path))
    except Exception as e:
        if dest_video_path.exists():
            dest_video_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to probe video file: {str(e)}")

    title = Path(dest_video_path).stem.replace("_", " ").title()

    project = create_project(
        project_id=project_id,
        name=title,
        source_filename=meta["filename"],
        source_path=str(dest_video_path.resolve()),
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        fps=meta["fps"],
        codec=meta["codec"],
        has_audio=meta["has_audio"],
        file_size=meta["file_size"]
    )

    return project

# ----------------- Transcription & Analysis -----------------

@app.post("/api/projects/{project_id}/transcribe")
def start_transcription(
    project_id: str,
    profile: str = Query("balanced"),
    model_size: Optional[str] = Query(None),
    language: Optional[str] = Query(None)
):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    task_id = create_task("transcription", f"Transcribing '{p['name']}'", {"project_id": project_id, "profile": profile})
    update_project_status(project_id, "transcribing")

    def run_transcription():
        try:
            update_task(task_id, progress=5.0, message="Extracting audio stream...")
            source_path = p["source_path"]
            proj_dir = PROJECTS_DIR / project_id
            audio_path = proj_dir / "audio" / "extracted_16k.wav"
            extract_audio(source_path, str(audio_path))

            if is_task_cancelled(task_id):
                update_project_status(project_id, "created")
                return

            transcript_json_path = proj_dir / "transcripts" / "transcript.json"

            def on_progress(pct, msg):
                update_task(task_id, progress=pct, message=msg)

            result = transcribe_audio_file(
                audio_path=str(audio_path),
                output_json_path=str(transcript_json_path),
                profile=profile,
                model_size=model_size,
                language=language if language and language != "auto" else None,
                source_video_path=source_path,
                progress_callback=on_progress
            )

            update_project_status(
                project_id,
                status="transcribed",
                language=result.get("language"),
                transcript_path=str(transcript_json_path.resolve())
            )
            update_task(task_id, progress=100.0, message="Transcription complete!", status="completed", result=result)

        except Exception as e:
            err_msg = str(e)
            logger.exception(f"Transcription failed for project {project_id}: {err_msg}")
            update_project_status(project_id, "error", error_message=f"[Transcription] {err_msg}")
            update_task(task_id, status="error", error=f"[Transcription] {err_msg}", message=f"Transcription failed: {err_msg}")

    # Use queue manager with concurrency limit 1 for Whisper
    enqueue_transcription(task_id, run_transcription)
    return {"task_id": task_id, "status": "processing"}

@app.post("/api/projects/{project_id}/analyze")
def start_clip_analysis(project_id: str, custom_instruction: Optional[str] = Query(None)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    task_id = create_task("analysis", f"Analyzing clips for '{p['name']}'", {"project_id": project_id, "custom_instruction": custom_instruction})
    update_project_status(project_id, "analyzing")

    def run_analysis():
        try:
            update_task(task_id, progress=10.0, message="Loading transcript data...")
            transcript_path = p.get("transcript_path")
            if not transcript_path or not Path(transcript_path).exists():
                raise RuntimeError("Project has not been transcribed yet.")

            import json
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)

            update_task(task_id, progress=30.0, message="Evaluating speech moments & hooks...")
            clips_candidates = detect_clip_candidates(
                transcript_data=transcript_data,
                project_id=project_id,
                min_clip_duration=15.0,
                max_clip_duration=60.0,
                custom_instruction=custom_instruction
            )

            update_task(task_id, progress=60.0, message="Detecting facial positioning for 9:16 vertical crop...")
            for c in clips_candidates:
                face_x = detect_face_center_x(p["source_path"], start_sec=c["start_time"], duration=min(10.0, c["duration"]))
                c["crop_x"] = round(face_x, 3)

            update_task(task_id, progress=85.0, message="Saving candidate clips...")
            saved_clips = create_clips_batch(clips_candidates)

            update_project_status(project_id, "ready")
            update_task(task_id, progress=100.0, message=f"Identified {len(saved_clips)} clips!", status="completed", result={"clips_count": len(saved_clips)})

        except Exception as e:
            err_msg = str(e)
            logger.exception(f"Clip analysis failed for project {project_id}: {err_msg}")
            update_project_status(project_id, "error", error_message=f"[Clip Analysis] {err_msg}")
            update_task(task_id, status="error", error=f"[Clip Analysis] {err_msg}", message=f"Analysis failed: {err_msg}")

    enqueue_render(task_id, run_analysis)
    return {"task_id": task_id, "status": "processing"}

@app.get("/api/projects/{project_id}/transcript")
def get_project_transcript(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    t_path = p.get("transcript_path")
    if t_path and Path(t_path).exists():
        try:
            import json
            with open(t_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read transcript: {e}")
    return {"segments": [], "full_text": "", "language": p.get("language") or "en"}

@app.get("/api/clips/{clip_id}/transcript")
def get_clip_transcript(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    p = get_project(c["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    t_path = p.get("transcript_path")
    if t_path and Path(t_path).exists():
        try:
            import json
            with open(t_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            st = c["start_time"]
            et = c["end_time"]
            matched_segs = []
            for seg in data.get("segments", []):
                if seg.get("end", 0) >= st and seg.get("start", 0) <= et:
                    matched_segs.append(seg)
            return {
                "clip_id": clip_id,
                "start_time": st,
                "end_time": et,
                "segments": matched_segs,
                "full_text": c.get("transcript_text") or c.get("caption_text") or ""
            }
        except Exception:
            pass
    return {
        "clip_id": clip_id,
        "start_time": c["start_time"],
        "end_time": c["end_time"],
        "segments": [{"start": c["start_time"], "end": c["end_time"], "text": c.get("transcript_text") or ""}],
        "full_text": c.get("transcript_text") or ""
    }

@app.post("/api/projects/{project_id}/retry")
def retry_project_processing(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    source_path = Path(p["source_path"])
    if not source_path.exists():
        raise HTTPException(status_code=400, detail=f"Source video file not found at {source_path}")

    task_id = create_task("retry_processing", f"Retrying processing for '{p['name']}'", {"project_id": project_id})
    update_project_status(project_id, "processing")

    def run_retry():
        current_stage = "Audio Extraction"
        try:
            proj_dir = PROJECTS_DIR / project_id
            audio_path = proj_dir / "audio" / "extracted_16k.wav"
            transcript_json_path = proj_dir / "transcripts" / "transcript.json"

            # 1. Audio step
            current_stage = "Audio Extraction"
            update_task(task_id, progress=10.0, message="Verifying audio stream...")
            if not audio_path.exists() or audio_path.stat().st_size < 1000:
                update_task(task_id, progress=20.0, message="Extracting audio...")
                extract_audio(str(source_path), str(audio_path))
            else:
                update_task(task_id, progress=25.0, message="Audio stream verified.")

            # 2. Transcription step
            current_stage = "Whisper Speech Transcription"
            transcript_data = None
            if transcript_json_path.exists() and transcript_json_path.stat().st_size > 10:
                try:
                    import json
                    with open(transcript_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "segments" in data:
                            transcript_data = data
                            update_task(task_id, progress=50.0, message="Reusing verified transcript...")
                except Exception:
                    transcript_data = None

            if not transcript_data:
                update_task(task_id, progress=35.0, message="Transcribing speech with Whisper...")
                user_settings = get_all_settings()
                model_name = user_settings.get("whisper_model", "base")
                pref = user_settings.get("device_preference", "auto")
                force_cpu = (pref == "cpu")

                def on_trans_progress(pct, msg):
                    update_task(task_id, progress=35.0 + (pct * 0.3), message=msg)

                transcript_data = transcribe_audio_file(
                    audio_path=str(audio_path),
                    output_json_path=str(transcript_json_path),
                    profile=user_settings.get("profile", "balanced"),
                    model_size=model_name,
                    language=user_settings.get("language") if user_settings.get("language") != "auto" else None,
                    source_video_path=str(source_path),
                    force_cpu=force_cpu,
                    progress_callback=on_trans_progress
                )

            # 3. Clip candidates step
            current_stage = "Clip Candidate Intelligence"
            update_task(task_id, progress=70.0, message="Evaluating moments and candidate clips...")
            clip_dur_pref = get_setting("default_clip_duration", "30-60") or "30-60"
            dur_parts = [float(x) for x in clip_dur_pref.split("-") if x.isdigit()]
            min_dur = dur_parts[0] if len(dur_parts) > 0 else 15.0
            max_dur = dur_parts[1] if len(dur_parts) > 1 else 60.0
            raw_count = get_setting("default_clip_count", "5") or "5"
            clip_count_pref = int(raw_count) if raw_count.isdigit() else 5

            clips_candidates = detect_clip_candidates(
                transcript_data=transcript_data,
                project_id=project_id,
                min_clip_duration=min_dur,
                max_clip_duration=max_dur,
                max_clips=clip_count_pref
            )

            # 4. Facial positioning
            current_stage = "Vertical Facial Framing"
            update_task(task_id, progress=85.0, message="Analyzing facial framing for vertical presentation...")
            for c in clips_candidates:
                face_x = detect_face_center_x(str(source_path), start_sec=c["start_time"], duration=min(5.0, c["duration"]))
                c["crop_x"] = round(face_x, 3)

            # 5. Database update
            current_stage = "Database Finalization"
            delete_clips_for_project(project_id)
            saved_clips = create_clips_batch(clips_candidates)

            update_project_status(
                project_id,
                status="ready",
                error_message="",
                language=transcript_data.get("language"),
                transcript_path=str(transcript_json_path.resolve())
            )
            update_task(task_id, progress=100.0, message=f"Retry complete! Generated {len(saved_clips)} clips.", status="completed", result={"clips_count": len(saved_clips)})

        except Exception as e:
            err_msg = str(e)
            logger.exception(f"Retry processing failed during {current_stage}: {err_msg}")
            update_project_status(project_id, "error", error_message=f"[{current_stage}] {err_msg}")
            update_task(task_id, status="error", error=f"[{current_stage}] {err_msg}", message=f"Retry failed during {current_stage}: {err_msg}")

    enqueue_render(task_id, run_retry)
    return {"task_id": task_id, "status": "processing"}


# ----------------- Clips & Preview -----------------

@app.get("/api/projects/{project_id}/clips")
def get_project_clips(project_id: str):
    return list_clips_for_project(project_id)

@app.get("/api/clips/{clip_id}")
def get_single_clip(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    return c

@app.patch("/api/clips/{clip_id}")
def modify_clip(clip_id: str, updates: ClipUpdateRequest):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")

    up_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if "start_time" in up_dict or "end_time" in up_dict:
        st = up_dict.get("start_time", c["start_time"])
        et = up_dict.get("end_time", c["end_time"])
        if et <= st:
            raise HTTPException(status_code=400, detail="End time must be greater than start time")
        up_dict["duration"] = round(et - st, 2)

    updated = update_clip(clip_id, up_dict)
    return updated

def _prepare_clip_subtitles(clip: Dict[str, Any], project: Dict[str, Any], out_ass_path: str, font_size_offset: int = 0) -> Optional[str]:
    if not clip.get("captions_enabled"):
        return None

    sub_segments = []
    transcript_path = project.get("transcript_path")
    if transcript_path and Path(transcript_path).exists():
        try:
            import json
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                clip_st = clip["start_time"]
                clip_et = clip["end_time"]
                for seg in data.get("segments", []):
                    if seg["end"] >= clip_st and seg["start"] <= clip_et:
                        words_in_clip = []
                        for w in seg.get("words", []):
                            if w.get("end", 0) >= clip_st and w.get("start", 0) <= clip_et:
                                words_in_clip.append({
                                    "word": w.get("word", ""),
                                    "start": max(0.0, w.get("start", 0) - clip_st),
                                    "end": max(0.1, w.get("end", 0) - clip_st)
                                })
                        sub_segments.append({
                            "start": max(0.0, seg["start"] - clip_st),
                            "end": max(0.2, seg["end"] - clip_st),
                            "text": seg.get("text", "").strip(),
                            "words": words_in_clip
                        })
        except Exception:
            sub_segments = []

    if not sub_segments:
        raw_text = clip.get("caption_text") or clip.get("transcript_text") or ""
        sub_segments = [{"start": 0.0, "end": clip["duration"], "text": raw_text}]

    preset_data = {}
    preset_name_or_id = clip.get("caption_preset")
    if preset_name_or_id:
        p_row = get_caption_preset(preset_name_or_id)
        if p_row:
            preset_data = p_row

    font_name = clip.get("caption_font") or preset_data.get("font_name", "Inter")
    font_sz = (clip.get("caption_size") or preset_data.get("font_size", 24)) + font_size_offset
    prim_col = clip.get("caption_color") or preset_data.get("primary_color", "#FFFFFF")
    hi_col = clip.get("caption_highlight_color") or preset_data.get("highlight_color", "#8273D6")
    bg_col = preset_data.get("bg_color") or ""
    out_col = preset_data.get("outline_color") or "#181818"
    pos = clip.get("caption_position") or preset_data.get("position", "bottom")
    anim = clip.get("caption_animation") or preset_data.get("animation", "Fade")
    w_per_line = clip.get("caption_words_per_line") or preset_data.get("words_per_line", 4)
    hi_words = clip.get("caption_highlight_words", True)
    speed = float(clip.get("caption_speed", 1.0))

    return generate_ass_subtitle(
        segments_or_words=sub_segments,
        output_ass_path=out_ass_path,
        font_name=font_name,
        font_size=font_sz,
        color=prim_col,
        highlight_color=hi_col,
        bg_color=bg_col,
        outline_color=out_col,
        position=pos,
        animation=anim,
        preset_name=preset_name_or_id,
        words_per_line=w_per_line,
        highlight_words=hi_words,
        animation_speed=speed
    )

@app.post("/api/clips/{clip_id}/regenerate-suggestions")
def regenerate_clip_ai_suggestions(clip_id: str, req: Optional[RegenerateSuggestionsRequest] = None):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")

    instruction = req.custom_instruction if req and req.custom_instruction else c.get("custom_instruction")
    sugg = generate_clip_suggestions(
        transcript_text=c.get("transcript_text") or c.get("caption_text") or c["title"],
        title=c["title"],
        custom_instruction=instruction
    )
    updated = update_clip(clip_id, {
        "titles_json": sugg["titles"],
        "hooks_json": sugg["hooks"],
        "description": sugg["description"],
        "hashtags": sugg["hashtags"]
    })
    return updated

@app.post("/api/clips/{clip_id}/preview")
def generate_clip_preview(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")

    p = get_project(c["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    task_id = create_task("preview_render", f"Rendering preview for '{c['title']}'", {"clip_id": clip_id})
    update_clip(clip_id, {"status": "rendering_preview"})

    def run_preview():
        try:
            update_task(task_id, progress=10.0, message="Preparing preview timeline...")
            proj_dir = PROJECTS_DIR / p["id"]
            preview_file = proj_dir / "previews" / f"preview_{clip_id}.mp4"

            # Brand Profile details if assigned
            brand = get_brand_profile(c.get("brand_profile_id")) if c.get("brand_profile_id") else None
            wm_path = brand.get("watermark_path") if brand else None
            wm_pos = brand.get("watermark_position", "top-right") if brand else "top-right"
            wm_opacity = float(brand.get("watermark_opacity", 0.85)) if brand else 0.85

            subtitle_file = None
            if c["captions_enabled"]:
                update_task(task_id, progress=25.0, message="Generating styled subtitle tracks...")
                sub_path = proj_dir / "previews" / f"sub_{clip_id}.ass"
                subtitle_file = _prepare_clip_subtitles(c, p, str(sub_path), font_size_offset=0)

            update_task(task_id, progress=45.0, message="Encoding preview video...")
            render_res = render_clip(
                source_path=p["source_path"],
                output_path=str(preview_file),
                start_time=c["start_time"],
                duration=c["duration"],
                aspect_ratio=c["aspect_ratio"],
                reframing_mode=c.get("reframing_mode", "single"),
                crop_x=c["crop_x"],
                crop_y=c["crop_y"],
                subtitle_path=subtitle_file,
                watermark_path=wm_path,
                watermark_position=wm_pos,
                watermark_opacity=wm_opacity,
                audio_denoise=bool(c.get("audio_denoise", False)),
                audio_normalize=bool(c.get("audio_normalize", False)),
                audio_clarity=bool(c.get("audio_clarity", False)),
                bg_music_path=c.get("bg_music_path"),
                bg_music_volume=float(c.get("bg_music_volume", 0.2)),
                music_ducking=bool(c.get("music_ducking", False)),
                resolution="720p",
                fps=30,
                volume=c.get("volume", 1.0),
                is_muted=c.get("is_muted", False),
                use_gpu=True
            )

            update_clip(clip_id, {
                "preview_path": render_res["output_path"],
                "status": "preview_ready"
            })
            update_task(task_id, progress=100.0, message="Preview ready!", status="completed", result={"preview_path": render_res["output_path"]})

        except Exception as e:
            err_msg = str(e)
            update_clip(clip_id, {"status": "error", "error_message": err_msg})
            update_task(task_id, status="error", error=err_msg, message=f"Preview render failed: {err_msg}")

    enqueue_render(task_id, run_preview)
    return {"task_id": task_id, "status": "processing"}

# ----------------- Export Endpoints -----------------

@app.post("/api/clips/{clip_id}/export")
def export_single_clip(clip_id: str, req: ExportRequest):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")

    p = get_project(c["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    task_id = create_task("export", f"Exporting '{c['title']}'", {"clip_id": clip_id})

    dest_folder = Path(req.destination_folder) if req.destination_folder else EXPORTS_DIR
    dest_folder.mkdir(parents=True, exist_ok=True)

    clean_name = req.filename or f"{p['name']}_{c['title']}_{req.resolution}.mp4"
    clean_name = "".join(ch for ch in clean_name if ch.isalnum() or ch in (" ", ".", "_", "-")).strip()
    if not clean_name.endswith(".mp4"):
        clean_name += ".mp4"

    out_file = dest_folder / clean_name

    def run_export():
        try:
            update_task(task_id, progress=10.0, message="Setting up export parameters...")
            proj_dir = PROJECTS_DIR / p["id"]

            brand = get_brand_profile(c.get("brand_profile_id")) if c.get("brand_profile_id") else None
            wm_path = brand.get("watermark_path") if brand else None
            wm_pos = brand.get("watermark_position", "top-right") if brand else "top-right"
            wm_opacity = float(brand.get("watermark_opacity", 0.85)) if brand else 0.85

            subtitle_file = None
            if c["captions_enabled"]:
                update_task(task_id, progress=20.0, message="Compiling synchronized subtitles...")
                sub_path = proj_dir / "exports" / f"export_sub_{clip_id}.ass"
                subtitle_file = _prepare_clip_subtitles(c, p, str(sub_path), font_size_offset=4)

            update_task(task_id, progress=40.0, message=f"Encoding final {req.resolution} MP4 video...")
            res = render_clip(
                source_path=p["source_path"],
                output_path=str(out_file),
                start_time=c["start_time"],
                duration=c["duration"],
                aspect_ratio=req.aspect_ratio or c["aspect_ratio"],
                reframing_mode=c.get("reframing_mode", "single"),
                crop_x=c["crop_x"],
                crop_y=c["crop_y"],
                subtitle_path=subtitle_file,
                watermark_path=wm_path,
                watermark_position=wm_pos,
                watermark_opacity=wm_opacity,
                audio_denoise=bool(c.get("audio_denoise", False)),
                audio_normalize=bool(c.get("audio_normalize", False)),
                audio_clarity=bool(c.get("audio_clarity", False)),
                bg_music_path=c.get("bg_music_path"),
                bg_music_volume=float(c.get("bg_music_volume", 0.2)),
                music_ducking=bool(c.get("music_ducking", False)),
                resolution=req.resolution or "1080p",
                fps=req.fps or 30,
                volume=c.get("volume", 1.0),
                is_muted=c.get("is_muted", False),
                use_gpu=True
            )

            exp_id = str(uuid.uuid4())
            export_record = create_export({
                "id": exp_id,
                "project_id": p["id"],
                "clip_id": clip_id,
                "output_filename": clean_name,
                "output_path": res["output_path"],
                "resolution": req.resolution or "1080p",
                "aspect_ratio": req.aspect_ratio or c["aspect_ratio"],
                "fps": req.fps or 30,
                "file_size": res["file_size"],
                "status": "completed"
            })

            update_clip(clip_id, {"status": "exported"})
            update_task(task_id, progress=100.0, message="Export successfully finished!", status="completed", result=export_record)

        except Exception as e:
            err_msg = str(e)
            update_task(task_id, status="error", error=err_msg, message=f"Export failed: {err_msg}")

    enqueue_render(task_id, run_export)
    return {"task_id": task_id, "status": "processing"}

@app.post("/api/projects/{project_id}/batch-export")
def batch_export_clips(project_id: str, req: BatchExportRequest):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    clips = list_clips_for_project(project_id)
    if req.clip_ids:
        clips = [c for c in clips if c["id"] in req.clip_ids]

    if not clips:
        raise HTTPException(status_code=400, detail="No clips available to export.")

    task_id = create_task("batch_export", f"Batch exporting {len(clips)} clips", {"project_id": project_id})

    def run_batch():
        try:
            completed_records = []
            dest_folder = Path(req.destination_folder) if req.destination_folder else EXPORTS_DIR
            dest_folder.mkdir(parents=True, exist_ok=True)

            total = len(clips)
            for idx, c in enumerate(clips):
                if is_task_cancelled(task_id):
                    break

                pct = round((idx / total) * 100.0, 1)
                update_task(task_id, progress=pct, message=f"Rendering clip {idx+1}/{total}: '{c['title']}'...")

                clean_name = f"{p['name']}_Clip_{idx+1}_{req.resolution}.mp4"
                clean_name = "".join(ch for ch in clean_name if ch.isalnum() or ch in (" ", ".", "_", "-")).strip()
                out_file = dest_folder / clean_name

                sub_file = None
                if c["captions_enabled"]:
                    sub_path = dest_folder / f"sub_{c['id']}.ass"
                    sub_file = _prepare_clip_subtitles(c, p, str(sub_path), font_size_offset=4)

                brand = get_brand_profile(c.get("brand_profile_id")) if c.get("brand_profile_id") else None
                wm_path = brand.get("watermark_path") if brand else None
                wm_pos = brand.get("watermark_position", "top-right") if brand else "top-right"
                wm_opacity = float(brand.get("watermark_opacity", 0.85)) if brand else 0.85

                res = render_clip(
                    source_path=p["source_path"],
                    output_path=str(out_file),
                    start_time=c["start_time"],
                    duration=c["duration"],
                    aspect_ratio=c["aspect_ratio"],
                    reframing_mode=c.get("reframing_mode", "single"),
                    crop_x=c["crop_x"],
                    crop_y=c["crop_y"],
                    subtitle_path=sub_file,
                    watermark_path=wm_path,
                    watermark_position=wm_pos,
                    watermark_opacity=wm_opacity,
                    audio_denoise=bool(c.get("audio_denoise", False)),
                    audio_normalize=bool(c.get("audio_normalize", False)),
                    audio_clarity=bool(c.get("audio_clarity", False)),
                    bg_music_path=c.get("bg_music_path"),
                    bg_music_volume=float(c.get("bg_music_volume", 0.2)),
                    music_ducking=bool(c.get("music_ducking", False)),
                    resolution=req.resolution or "1080p",
                    fps=req.fps or 30,
                    volume=c.get("volume", 1.0),
                    is_muted=c.get("is_muted", False),
                    use_gpu=True
                )

                exp_id = str(uuid.uuid4())
                rec = create_export({
                    "id": exp_id,
                    "project_id": p["id"],
                    "clip_id": c["id"],
                    "output_filename": clean_name,
                    "output_path": res["output_path"],
                    "resolution": req.resolution or "1080p",
                    "aspect_ratio": c["aspect_ratio"],
                    "fps": req.fps or 30,
                    "file_size": res["file_size"],
                    "status": "completed"
                })
                completed_records.append(rec)

            update_task(task_id, progress=100.0, message=f"Successfully exported {len(completed_records)} clips!", status="completed", result=completed_records)

        except Exception as e:
            err_msg = str(e)
            update_task(task_id, status="error", error=err_msg, message=f"Batch export failed: {err_msg}")

    enqueue_render(task_id, run_batch)
    return {"task_id": task_id, "status": "processing"}

# ----------------- Subtitles & XML Export Endpoints -----------------

@app.post("/api/clips/{clip_id}/export-subtitles")
def export_clip_subtitles(clip_id: str, req: SubtitleExportRequest):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    p = get_project(c["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    fmt = (req.format or "srt").lower().strip()
    clean_name = f"{p['name']}_{c['title']}.{fmt}"
    clean_name = "".join(ch for ch in clean_name if ch.isalnum() or ch in (" ", ".", "_", "-")).strip()
    out_file = EXPORTS_DIR / clean_name

    segments = []
    transcript_path = p.get("transcript_path")
    if transcript_path and Path(transcript_path).exists():
        try:
            import json
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for s in data.get("segments", []):
                    if s["end"] >= c["start_time"] and s["start"] <= c["end_time"]:
                        segments.append({
                            "start": max(0.0, s["start"] - c["start_time"]),
                            "end": max(0.2, s["end"] - c["start_time"]),
                            "text": s.get("text", "").strip()
                        })
        except Exception:
            pass

    if not segments:
        segments = [{"start": 0.0, "end": c["duration"], "text": c.get("caption_text") or c.get("transcript_text") or ""}]

    if fmt == "srt":
        saved_path = generate_srt(segments, str(out_file))
    elif fmt == "vtt":
        saved_path = generate_vtt(segments, str(out_file))
    else:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(s["text"] for s in segments))
        saved_path = str(out_file.resolve())

    return {"output_path": saved_path, "filename": clean_name, "format": fmt}

@app.post("/api/clips/{clip_id}/export-xml")
def export_clip_premiere_xml(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    p = get_project(c["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    clean_name = f"{p['name']}_{c['title']}_sequence.xml"
    clean_name = "".join(ch for ch in clean_name if ch.isalnum() or ch in (" ", ".", "_", "-")).strip()
    out_file = EXPORTS_DIR / clean_name

    meta = probe_video(p["source_path"])
    xml_path = generate_premiere_xml(
        project_name=p["name"],
        clip_title=c["title"],
        source_file_path=p["source_path"],
        start_time=c["start_time"],
        end_time=c["end_time"],
        fps=meta["fps"],
        width=meta["width"],
        height=meta["height"],
        output_xml_path=str(out_file)
    )

    return {"output_path": xml_path, "filename": clean_name, "format": "premiere_xml"}

# ----------------- Caption Presets Endpoints -----------------

@app.get("/api/caption-presets")
def get_caption_presets_endpoint():
    return list_caption_presets()

@app.post("/api/caption-presets")
def create_caption_preset_endpoint(req: CaptionPresetCreateRequest):
    return create_caption_preset(req.model_dump())

@app.put("/api/caption-presets/{preset_id}")
def update_caption_preset_endpoint(preset_id: str, req: CaptionPresetUpdateRequest):
    up = update_caption_preset(preset_id, {k: v for k, v in req.model_dump().items() if v is not None})
    if not up:
        raise HTTPException(status_code=404, detail="Preset not found")
    return up

@app.delete("/api/caption-presets/{preset_id}")
def delete_caption_preset_endpoint(preset_id: str):
    deleted = delete_caption_preset(preset_id)
    return {"success": deleted}

@app.post("/api/projects/{project_id}/apply-caption-preset")
def apply_preset_to_project_clips(project_id: str, req: ApplyPresetRequest):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    preset = get_caption_preset(req.preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    clips = list_clips_for_project(project_id)
    target_clips = [c for c in clips if (not req.clip_ids or c["id"] in req.clip_ids)]

    updates_count = 0
    for c in target_clips:
        update_clip(c["id"], {
            "caption_preset": preset["name"],
            "caption_font": preset["font_name"],
            "caption_size": preset["font_size"],
            "caption_color": preset["primary_color"],
            "caption_highlight_color": preset["highlight_color"],
            "caption_position": preset["position"],
            "caption_animation": preset["animation"],
            "caption_words_per_line": preset["words_per_line"]
        })
        updates_count += 1

    return {"success": True, "applied_to_count": updates_count, "preset": preset["name"]}

# ----------------- Speaker & Reframing Endpoints -----------------

@app.post("/api/clips/{clip_id}/detect-speakers")
def detect_clip_speakers(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    p = get_project(c["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    tracking = detect_speaker_tracking_keyframes(
        p["source_path"],
        start_sec=c["start_time"],
        duration=c["duration"]
    )
    # Update clip's crop_x with smoothed center x
    update_clip(clip_id, {"crop_x": tracking["smoothed_center_x"]})
    return tracking

# ----------------- Audio Enhancement Endpoints -----------------

@app.get("/api/projects/{project_id}/silences")
def get_project_silences(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    proj_dir = PROJECTS_DIR / project_id
    audio_path = proj_dir / "audio" / "extracted_16k.wav"
    target_media = str(audio_path) if audio_path.exists() else p["source_path"]

    silences = detect_silences(target_media)
    return {"silences": silences, "count": len(silences)}

@app.get("/api/projects/{project_id}/fillers")
def get_project_fillers(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript_path = p.get("transcript_path")
    if not transcript_path or not Path(transcript_path).exists():
        return {"fillers": [], "count": 0}

    import json
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    fillers = detect_filler_words(transcript_data)
    return {"fillers": fillers, "count": len(fillers)}

# ----------------- B-Roll & Motion Graphics Endpoints -----------------

@app.get("/api/broll")
def get_broll_library(category: Optional[str] = Query(None)):
    return list_broll_assets(category)

@app.post("/api/broll/upload")
async def upload_broll_asset(
    file: Optional[UploadFile] = File(None),
    filepath: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form("General"),
    tags: Optional[str] = Form("")
):
    BROLL_DIR.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4())

    dest_file = None
    if file and file.filename:
        safe_name = Path(file.filename).name
        dest_file = BROLL_DIR / f"{asset_id}_{safe_name}"
        with open(dest_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        display_name = name or Path(file.filename).stem
    elif filepath:
        src = Path(filepath)
        if not src.exists():
            raise HTTPException(status_code=400, detail="File path does not exist")
        dest_file = BROLL_DIR / f"{asset_id}_{src.name}"
        shutil.copy2(str(src), str(dest_file))
        display_name = name or src.stem
    else:
        raise HTTPException(status_code=400, detail="No file or filepath provided")

    # Probe duration and dimensions
    dur = 0.0
    w = 0
    h = 0
    asset_type = "video"
    ext = dest_file.suffix.lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".svg"]:
        asset_type = "image"
    else:
        try:
            meta = probe_video(str(dest_file))
            dur = meta.get("duration", 0.0)
            w = meta.get("width", 0)
            h = meta.get("height", 0)
        except Exception:
            pass

    rec = create_broll_asset({
        "id": asset_id,
        "name": display_name,
        "file_path": str(dest_file.resolve()),
        "asset_type": asset_type,
        "category": category or "General",
        "tags": tags or "",
        "duration": dur,
        "width": w,
        "height": h
    })
    return rec

@app.delete("/api/broll/{asset_id}")
def remove_broll_asset(asset_id: str):
    asset = get_broll_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    f_path = Path(asset["file_path"])
    if f_path.exists():
        try:
            f_path.unlink()
        except Exception:
            pass
    deleted = delete_broll_asset(asset_id)
    return {"success": deleted}

@app.post("/api/clips/{clip_id}/suggest-broll")
def suggest_clip_broll(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")

    text = c.get("transcript_text") or c.get("caption_text") or ""
    all_assets = list_broll_assets()
    suggestions = match_broll_suggestions(text, all_assets)
    return {"suggestions": suggestions}

@app.get("/api/motion-graphics/templates")
def get_motion_graphics_templates():
    return MOTION_GRAPHICS_TEMPLATES

# ----------------- Voiceover Endpoints -----------------

@app.get("/api/voiceover/voices")
def get_voiceover_voices():
    return get_available_system_voices()

@app.post("/api/voiceover/generate")
def generate_voiceover_endpoint(req: VoiceoverGenerateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Voiceover text cannot be empty")

    res = generate_offline_voiceover(
        text=req.text,
        voice=req.voice,
        speed=req.speed or 0,
        volume=req.volume or 1.0
    )

    rec = create_voiceover({
        "project_id": req.project_id,
        "clip_id": req.clip_id,
        "text": req.text,
        "voice": req.voice,
        "speed": req.speed or 0,
        "volume": req.volume or 1.0,
        "file_path": res["output_path"],
        "duration": res["duration"]
    })
    return rec

@app.get("/api/voiceovers")
def list_voiceovers_endpoint(project_id: Optional[str] = Query(None)):
    return list_voiceovers(project_id)

# ----------------- Brand Kit Endpoints -----------------

@app.get("/api/brand-profiles")
def list_brands():
    return list_brand_profiles()

@app.post("/api/brand-profiles")
def create_brand(req: BrandProfileCreateRequest):
    return create_brand_profile(req.model_dump())

@app.put("/api/brand-profiles/{brand_id}")
def update_brand(brand_id: str, req: BrandProfileUpdateRequest):
    up = update_brand_profile(brand_id, {k: v for k, v in req.model_dump().items() if v is not None})
    if not up:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return up

@app.delete("/api/brand-profiles/{brand_id}")
def delete_brand(brand_id: str):
    deleted = delete_brand_profile(brand_id)
    return {"success": deleted}

@app.post("/api/projects/{project_id}/apply-brand")
def apply_brand_to_clips(project_id: str, req: ApplyBrandRequest):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    brand = get_brand_profile(req.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    clips = list_clips_for_project(project_id)
    target_clips = [c for c in clips if (not req.clip_ids or c["id"] in req.clip_ids)]

    count = 0
    for c in target_clips:
        update_clip(c["id"], {
            "brand_profile_id": brand["id"],
            "caption_font": brand.get("caption_font", "Inter"),
            "caption_color": brand.get("primary_color", "#FFFFFF"),
            "caption_highlight_color": brand.get("secondary_color", "#8273D6"),
            "aspect_ratio": brand.get("default_aspect_ratio", c.get("aspect_ratio", "9:16"))
        })
        count += 1

    return {"success": True, "applied_to_count": count, "brand": brand["name"]}

@app.get("/api/exports")
def get_all_exports():
    return list_exports()

@app.delete("/api/exports/{export_id}")
def remove_export(export_id: str):
    exp = get_export(export_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Export not found")

    out_path = Path(exp["output_path"])
    if out_path.exists():
        try:
            out_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete export file on disk: {e}")

    deleted = delete_export(export_id)
    return {"success": deleted}

@app.post("/api/open-folder")
def open_folder_in_explorer(req: OpenFolderRequest):
    cur_models_dir = get_models_dir()
    named_map = {
        "appdata": KLYPTRA_HOME,
        "projects": PROJECTS_DIR,
        "models": cur_models_dir,
        "cache": CACHE_DIR,
        "exports": EXPORTS_DIR,
        "logs": LOGS_DIR
    }
    lowered = req.path.strip().lower()
    if lowered in named_map or not lowered:
        target = named_map.get(lowered, EXPORTS_DIR)
    else:
        p = Path(req.path).resolve()
        if not _is_path_within(p, KLYPTRA_HOME) and not _is_path_within(p, cur_models_dir):
            # Also permit custom export_dir if configured by user
            custom_export = get_setting("export_dir", "")
            if custom_export and _is_path_within(p, Path(custom_export)):
                target = p if p.is_dir() else p.parent
            else:
                target = EXPORTS_DIR
        else:
            target = p if p.is_dir() else p.parent

    target.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(str(target))
        else:
            subprocess.run(["explorer.exe", str(target)])
        return {"success": True, "opened": str(target)}
    except Exception as e:
        logger.warning(f"Failed to open folder {target}: {e}")
        raise HTTPException(status_code=500, detail="Could not open directory in file explorer.")

# ----------------- Settings Endpoints -----------------

@app.get("/api/settings")
def get_settings_endpoint():
    return get_all_settings()

@app.post("/api/settings")
def update_settings_endpoint(settings: Dict[str, Any]):
    return update_settings(settings)

@app.post("/api/settings/reset")
def reset_settings_endpoint():
    return reset_settings()

# ----------------- Diagnostics & Hardware -----------------

@app.post("/api/system/test-gpu")
def test_gpu_endpoint():
    return run_gpu_test()

@app.post("/api/system/test-ffmpeg")
def test_ffmpeg_endpoint():
    return run_ffmpeg_test(FFMPEG_EXE)

@app.post("/api/system/refresh-hardware")
def refresh_hardware_endpoint():
    clear_hardware_cache()
    return system_info()

@app.get("/api/system/logs")
def get_system_logs(lines: int = Query(200)):
    log_file = LOGS_DIR / "klyptra.log"
    if not log_file.exists():
        return {"logs": "No log records found yet."}
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {"logs": "".join(recent)}
    except Exception as e:
        return {"logs": f"Error reading log file: {str(e)}"}

# ----------------- Storage Management -----------------

def get_folder_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total

@app.get("/api/system/storage-info")
def get_storage_breakdown():
    cur_models_dir = get_models_dir()
    total_disk, used_disk, free_disk = shutil.disk_usage(str(KLYPTRA_HOME))
    return {
        "paths": {
            "app_data": str(KLYPTRA_HOME),
            "projects": str(PROJECTS_DIR),
            "models": str(cur_models_dir),
            "cache": str(CACHE_DIR),
            "exports": str(EXPORTS_DIR)
        },
        "sizes_mb": {
            "projects": round(get_folder_size(PROJECTS_DIR) / (1024 * 1024), 1),
            "models": round(get_folder_size(cur_models_dir) / (1024 * 1024), 1),
            "cache": round(get_folder_size(CACHE_DIR) / (1024 * 1024), 1),
            "exports": round(get_folder_size(EXPORTS_DIR) / (1024 * 1024), 1),
        },
        "disk": {
            "total_gb": round(total_disk / (1024 ** 3), 1),
            "used_gb": round(used_disk / (1024 ** 3), 1),
            "free_gb": round(free_disk / (1024 ** 3), 1),
            "free_percent": round((free_disk / total_disk) * 100, 1)
        }
    }

@app.post("/api/system/clear-temp")
def clear_temporary_files():
    cleared_bytes = 0
    cleared_files = 0
    for target_dir in [TEMP_CACHE_DIR, RENDERS_CACHE_DIR]:
        if target_dir.exists():
            for item in target_dir.iterdir():
                try:
                    if item.is_file():
                        cleared_bytes += item.stat().st_size
                        item.unlink()
                        cleared_files += 1
                    elif item.is_dir():
                        sz = get_folder_size(item)
                        cleared_bytes += sz
                        shutil.rmtree(str(item), ignore_errors=True)
                        cleared_files += 1
                except Exception as e:
                    logger.warning(f"Failed to delete temp item {item}: {e}")
    return {
        "cleared_files": cleared_files,
        "cleared_mb": round(cleared_bytes / (1024 * 1024), 2),
        "message": f"Successfully cleared {cleared_files} temporary files ({round(cleared_bytes / (1024 * 1024), 2)} MB reclaimed)."
    }

# ----------------- First-Launch Setup & Model Management -----------------

class ModelStorageRequest(BaseModel):
    models_dir: str

@app.get("/api/setup/status")
def get_setup_status():
    cur_models_dir = get_models_dir()
    active_model = get_setting("whisper_model", "base")
    first_launch_done = get_setting("first_launch_completed", "false") == "true"
    downloaded_models = []
    for m in AVAILABLE_WHISPER_MODELS:
        sub = cur_models_dir / f"models--Systran--faster-whisper-{m}"
        if sub.exists() and any(sub.rglob("model.bin")):
            downloaded_models.append(m)
    hw = get_system_hardware_profile(FFMPEG_EXE)
    return {
        "first_launch_completed": first_launch_done,
        "any_model_downloaded": len(downloaded_models) > 0,
        "downloaded_models": downloaded_models,
        "active_model": active_model,
        "models_dir": str(cur_models_dir),
        "ffmpeg_available": hw.get("ffmpeg", {}).get("available", False),
        "gpu_accelerated": hw.get("is_gpu_accelerated", False)
    }

@app.post("/api/models/storage")
def update_models_storage(req: ModelStorageRequest):
    raw = (req.models_dir or "").strip()
    if not raw or ".." in Path(raw).parts:
        raise HTTPException(status_code=400, detail="Invalid model storage path.")
    try:
        updated = set_models_dir(raw)
        return {"success": True, "models_dir": str(updated)}
    except Exception as e:
        logger.warning(f"Could not set models directory {raw}: {e}")
        raise HTTPException(status_code=400, detail="Unable to configure the specified model storage folder.")

@app.get("/api/models")
def list_available_models():
    cur_models_dir = get_models_dir()
    current_setting = get_setting("whisper_model", "base")
    models = []
    approx_sizes = {
        "tiny": "75 MB",
        "base": "145 MB",
        "small": "480 MB",
        "medium": "1.5 GB"
    }
    for m in AVAILABLE_WHISPER_MODELS:
        model_subfolder = cur_models_dir / f"models--Systran--faster-whisper-{m}"
        downloaded = model_subfolder.exists() and any(model_subfolder.rglob("model.bin"))
        size_mb = round(get_folder_size(model_subfolder) / (1024 * 1024), 1) if model_subfolder.exists() else 0.0

        models.append({
            "name": m,
            "downloaded": downloaded,
            "size_mb": size_mb,
            "approx_size": approx_sizes.get(m, "Unknown"),
            "is_active": (m == current_setting)
        })
    return models

@app.post("/api/models/download")
def download_model_endpoint(req: ModelDownloadRequest):
    m_name = req.model_name.lower().strip()
    if m_name not in AVAILABLE_WHISPER_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {m_name}")

    cur_models_dir = get_models_dir()
    task_id = create_task("model_download", f"Downloading Whisper model '{m_name}'", {"model": m_name})

    def run_download():
        try:
            update_task(task_id, progress=10.0, message=f"Connecting to download '{m_name}' model (resumable & SHA-256 verified)...")
            from faster_whisper import download_model
            model_path = download_model(m_name, output_dir=str(cur_models_dir))
            model_bin = Path(model_path) / "model.bin"
            if not model_bin.exists() or model_bin.stat().st_size < 1024 * 1024:
                raise RuntimeError("Downloaded model archive verification failed (missing or incomplete model.bin).")
            update_settings({"whisper_model": m_name, "first_launch_completed": "true"})
            update_task(task_id, progress=100.0, message=f"Whisper '{m_name}' downloaded and verified!", status="completed")
        except Exception as e:
            err_msg = str(e)
            logger.exception(f"Model download failed: {err_msg}")
            update_task(task_id, status="error", error="Model download failed. Verify your internet connection and retry.", message="Model download failed. Check network and retry.")

    enqueue_render(task_id, run_download)
    return {"task_id": task_id, "status": "processing"}

@app.delete("/api/models/{model_name}")
def delete_model_endpoint(model_name: str):
    m_name = model_name.lower().strip()
    if m_name not in AVAILABLE_WHISPER_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {m_name}")

    cur_models_dir = get_models_dir()
    model_subfolder = cur_models_dir / f"models--Systran--faster-whisper-{m_name}"
    if not model_subfolder.exists():
        return {"success": True, "message": "Model not downloaded"}

    try:
        shutil.rmtree(str(model_subfolder), ignore_errors=True)
        return {"success": True, "message": f"Deleted model {m_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to remove model files.")


# ----------------- Task Management -----------------

@app.get("/api/tasks/{task_id}/status")
def task_status(task_id: str):
    t = get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t

@app.post("/api/tasks/{task_id}/cancel")
def cancel_running_task(task_id: str):
    cancelled = cancel_task(task_id)
    return {"success": cancelled}

# ----------------- Video Range Streaming (HTTP 206) -----------------

@app.get("/api/media/stream")
def stream_media_file(path: str, request: Request):
    file_path = _validate_safe_media_path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range")

    if not range_header:
        return FileResponse(str(file_path), media_type="video/mp4")

    try:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
    except Exception:
        start = 0
        end = file_size - 1

    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))
    chunk_length = end - start + 1

    def iter_file():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_length
            chunk_size = 1024 * 1024
            while remaining > 0:
                read_size = min(remaining, chunk_size)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(iter_file(), status_code=206, headers=headers)

# ----------------- Mount Static Frontend -----------------
from fastapi.staticfiles import StaticFiles

ROOT_DIR = get_resource_root()
app.mount("/", StaticFiles(directory=str(ROOT_DIR), html=True), name="static")
