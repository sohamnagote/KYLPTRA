import os
import sys
import shutil
import glob
from pathlib import Path
from typing import Dict, Any

# Base AppData directory for KLYPTRA (User Data always lives in %LOCALAPPDATA%\KLYPTRA)
LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
KLYPTRA_HOME = Path(os.environ.get("KLYPTRA_DATA_DIR") or (Path(LOCALAPPDATA) / "KLYPTRA"))

DATABASE_DIR = KLYPTRA_HOME / "database"
PROJECTS_DIR = KLYPTRA_HOME / "projects"
DEFAULT_MODELS_DIR = KLYPTRA_HOME / "models" / "whisper"
MODELS_PATH_CONFIG = KLYPTRA_HOME / "models_dir.txt"
CACHE_DIR = KLYPTRA_HOME / "cache"
RENDERS_CACHE_DIR = CACHE_DIR / "renders"
TEMP_CACHE_DIR = CACHE_DIR / "temporary"
LOGS_DIR = KLYPTRA_HOME / "logs"
EXPORTS_DIR = KLYPTRA_HOME / "exports"
BROLL_DIR = KLYPTRA_HOME / "broll"
BRANDS_DIR = KLYPTRA_HOME / "brands"
VOICEOVERS_DIR = KLYPTRA_HOME / "voiceovers"

DATABASE_PATH = DATABASE_DIR / "klyptra.db"

def get_models_dir() -> Path:
    """Resolve user-configured Whisper model directory, defaulting to %LOCALAPPDATA%\\KLYPTRA\\models\\whisper."""
    try:
        if MODELS_PATH_CONFIG.exists():
            custom = MODELS_PATH_CONFIG.read_text(encoding="utf-8").strip()
            if custom:
                p = Path(custom)
                p.mkdir(parents=True, exist_ok=True)
                return p
    except Exception:
        pass
    DEFAULT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_MODELS_DIR

def set_models_dir(new_path: str) -> Path:
    p = Path(new_path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    MODELS_PATH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    MODELS_PATH_CONFIG.write_text(str(p), encoding="utf-8")
    global MODELS_DIR
    MODELS_DIR = p
    return p

MODELS_DIR = get_models_dir()

def is_production() -> bool:
    return os.environ.get("KLYPTRA_ENV", "").strip().lower() == "production"

def get_resource_root() -> Path:
    """Resolve the application root directory whether running from source, PyInstaller bundle, or Electron sidecar."""
    env_root = os.environ.get("KLYPTRA_WEB_ROOT")
    if env_root and Path(env_root).exists() and (Path(env_root) / "index.html").exists():
        return Path(env_root)
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS") and (Path(sys._MEIPASS) / "index.html").exists():
            return Path(sys._MEIPASS)
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "index.html").exists():
            return exe_dir
        if (exe_dir.parent / "index.html").exists():
            return exe_dir.parent
        if (exe_dir.parent / "app" / "index.html").exists():
            return exe_dir.parent / "app"
    return Path(__file__).resolve().parent.parent

def get_win_subprocess_kwargs() -> Dict[str, Any]:
    """Suppress console window flashing when spawning CLI tools from GUI apps on Windows."""
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}  # subprocess.CREATE_NO_WINDOW
    return {}

def init_storage_directories():
    for d in [
        KLYPTRA_HOME,
        DATABASE_DIR,
        PROJECTS_DIR,
        get_models_dir(),
        CACHE_DIR,
        RENDERS_CACHE_DIR,
        TEMP_CACHE_DIR,
        LOGS_DIR,
        EXPORTS_DIR,
        BROLL_DIR,
        BRANDS_DIR,
        VOICEOVERS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

def _find_binary(exe_name: str) -> str:
    """Locate bundled or system FFmpeg/FFprobe binary reliably without hardcoded user paths."""
    win_exe = f"{exe_name}.exe" if sys.platform == "win32" else exe_name
    root = get_resource_root()

    # 1. Explicit environment override (e.g. from Electron sidecar)
    env_bin_dir = os.environ.get("KLYPTRA_BIN_DIR")
    if env_bin_dir:
        candidate = Path(env_bin_dir) / win_exe
        if candidate.exists():
            return str(candidate)

    # 2. Bundled directories inside PyInstaller or Electron resources
    candidates = [
        root / "resources" / "bin" / win_exe,
        root / "bin" / win_exe,
        Path(sys.executable).parent / "bin" / win_exe,
        Path(sys.executable).parent / "resources" / "bin" / win_exe,
        Path(sys.executable).parent.parent / "bin" / win_exe,
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    # 3. System PATH
    which_res = shutil.which(exe_name)
    if which_res:
        return which_res

    # 4. Generic WinGet installation scan under current user's LOCALAPPDATA (dev fallback)
    winget_pattern = str(Path(LOCALAPPDATA) / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg*" / "*" / "bin" / win_exe)
    matches = glob.glob(winget_pattern)
    if matches:
        return matches[0]

    return exe_name

FFMPEG_EXE = _find_binary("ffmpeg")
FFPROBE_EXE = _find_binary("ffprobe")

# Whisper configuration
DEFAULT_WHISPER_MODEL = "base"
AVAILABLE_WHISPER_MODELS = ["tiny", "base", "small", "medium"]

# Security limits
MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB max video upload
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
ALLOWED_MEDIA_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS | {".mp3", ".wav", ".aac", ".m4a", ".png", ".jpg", ".jpeg", ".webp", ".srt", ".vtt", ".xml"}

# Video export settings
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_FPS = 30
