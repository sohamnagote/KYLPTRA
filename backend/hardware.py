import os
import sys
import subprocess
import json
import logging
import platform
import shutil
import time
import ctypes
from typing import Dict, Any, Optional
from .config import get_win_subprocess_kwargs

logger = logging.getLogger(__name__)

_HARDWARE_CACHE: Optional[Dict[str, Any]] = None

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_ram_info() -> Dict[str, Any]:
    """
    Get physical RAM total and free in GB via Win32 API.
    """
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total_gb = round(stat.ullTotalPhys / (1024 ** 3), 1)
            free_gb = round(stat.ullAvailPhys / (1024 ** 3), 1)
            used_gb = round(total_gb - free_gb, 1)
            return {
                "total_gb": total_gb,
                "free_gb": free_gb,
                "used_gb": used_gb,
                "load_percent": stat.dwMemoryLoad,
                "summary": f"{free_gb} GB free / {total_gb} GB total ({stat.dwMemoryLoad}% load)"
            }
    except Exception as e:
        logger.debug(f"RAM query error: {e}")
    return {
        "total_gb": 0,
        "free_gb": 0,
        "used_gb": 0,
        "load_percent": 0,
        "summary": "Unknown"
    }

def get_cpu_info() -> Dict[str, Any]:
    """
    Get CPU model name, architecture and logical core count.
    """
    model = os.environ.get("PROCESSOR_IDENTIFIER", platform.processor() or "Unknown CPU")
    cores = os.cpu_count() or 1
    arch = platform.machine()
    return {
        "model": model,
        "cores": cores,
        "architecture": arch,
        "summary": f"{model} ({cores} cores)"
    }

def get_storage_info(target_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get free, used, total disk space for application drive.
    """
    if not target_path:
        target_path = os.environ.get("LOCALAPPDATA", "C:\\")
    try:
        usage = shutil.disk_usage(target_path)
        total_gb = round(usage.total / (1024 ** 3), 1)
        free_gb = round(usage.free / (1024 ** 3), 1)
        used_gb = round(usage.used / (1024 ** 3), 1)
        free_percent = round((usage.free / usage.total) * 100, 1)
        return {
            "path": target_path,
            "total_gb": total_gb,
            "free_gb": free_gb,
            "used_gb": used_gb,
            "free_percent": free_percent,
            "summary": f"{free_gb} GB free / {total_gb} GB total ({free_percent}% free)"
        }
    except Exception as e:
        logger.debug(f"Storage query error: {e}")
        return {
            "path": target_path,
            "total_gb": 0,
            "free_gb": 0,
            "used_gb": 0,
            "free_percent": 0,
            "summary": "Unknown"
        }

def get_ffmpeg_version(ffmpeg_exe: str = "ffmpeg") -> Dict[str, Any]:
    try:
        res = subprocess.run([ffmpeg_exe, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, **get_win_subprocess_kwargs())
        if res.returncode == 0:
            first_line = res.stdout.splitlines()[0] if res.stdout else "FFmpeg installed"
            return {
                "available": True,
                "version": first_line,
                "executable": ffmpeg_exe
            }
    except Exception as e:
        logger.debug(f"FFmpeg check error: {e}")
    return {
        "available": False,
        "version": "Not found",
        "executable": ffmpeg_exe
    }

def get_nvidia_gpu_info() -> Dict[str, Any]:
    """
    Detect NVIDIA GPU name, driver version, and VRAM using nvidia-smi.
    """
    info = {
        "available": False,
        "name": "Unknown",
        "driver_version": "Unknown",
        "vram_total_mb": 0,
        "vram_free_mb": 0
    }
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,memory.free",
            "--format=csv,noheader,nounits"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, **get_win_subprocess_kwargs())
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                info["available"] = True
                info["name"] = parts[0]
                info["driver_version"] = parts[1]
                info["vram_total_mb"] = int(float(parts[2]))
                info["vram_free_mb"] = int(float(parts[3]))
    except Exception as e:
        logger.debug(f"nvidia-smi query error: {e}")
    return info

def check_whisper_cuda() -> Dict[str, Any]:
    """
    Verify if faster-whisper (CTranslate2) can genuinely allocate on CUDA (including cuBLAS DLL presence).
    """
    try:
        import ctranslate2
        import numpy as np
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            # Verify CUDA runtime allocation works without missing cublas64_12.dll
            _test = ctranslate2.StorageView.from_array(np.zeros((1, 4), dtype=np.float32)).to_device(ctranslate2.Device.cuda)
            del _test
            return {
                "available": True,
                "device": "cuda",
                "compute_type": "float16",
                "device_count": cuda_count,
                "description": f"CUDA Accelerated ({cuda_count} GPU)"
            }
    except Exception as e:
        logger.warning(f"CUDA compatibility check fell back to CPU: {e}")

    return {
        "available": False,
        "device": "cpu",
        "compute_type": "int8",
        "device_count": 0,
        "description": "CPU (Optimized int8 quantization)"
    }

def detect_best_ffmpeg_encoder(ffmpeg_exe: str = "ffmpeg") -> Dict[str, str]:
    """
    Test FFmpeg video encoders by running actual micro-renders to verify what works without crashing.
    Prioritizes: h264_nvenc -> h264_mf (Windows Media Foundation HW) -> libx264.
    """
    candidates = [
        ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "22"], "NVIDIA NVENC Hardware"),
        ("h264_mf", ["-c:v", "h264_mf"], "Hardware Accelerated (Windows Media Foundation / D3D11)"),
        ("libx264", ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"], "CPU libx264 (veryfast)")
    ]

    for enc_name, enc_args, desc in candidates:
        test_cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=0.1:size=64x64:rate=30",
        ] + enc_args + [
            "-pix_fmt", "yuv420p",
            "-f", "null",
            "-"
        ]
        try:
            res = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, **get_win_subprocess_kwargs())
            if res.returncode == 0:
                logger.info(f"Verified working FFmpeg encoder: {enc_name} ({desc})")
                return {
                    "encoder": enc_name,
                    "args": enc_args,
                    "description": desc,
                    "is_hardware": enc_name in ("h264_nvenc", "h264_mf")
                }
        except Exception:
            continue

    # Fallback default
    return {
        "encoder": "libx264",
        "args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"],
        "description": "CPU libx264",
        "is_hardware": False
    }

def clear_hardware_cache():
    global _HARDWARE_CACHE
    _HARDWARE_CACHE = None

def get_system_hardware_profile(ffmpeg_exe: str = "ffmpeg") -> Dict[str, Any]:
    global _HARDWARE_CACHE
    if _HARDWARE_CACHE is not None:
        return _HARDWARE_CACHE

    gpu_info = get_nvidia_gpu_info()
    whisper_cuda = check_whisper_cuda()
    best_enc = detect_best_ffmpeg_encoder(ffmpeg_exe)
    cpu_info = get_cpu_info()
    ram_info = get_ram_info()
    storage_info = get_storage_info()
    ffmpeg_info = get_ffmpeg_version(ffmpeg_exe)

    _HARDWARE_CACHE = {
        "gpu": gpu_info,
        "whisper": whisper_cuda,
        "video_encoder": best_enc,
        "cpu": cpu_info,
        "ram": ram_info,
        "storage": storage_info,
        "ffmpeg": ffmpeg_info,
        "is_gpu_accelerated": whisper_cuda["available"] or best_enc["is_hardware"]
    }
    return _HARDWARE_CACHE

def run_gpu_test() -> Dict[str, Any]:
    """
    Run diagnostic GPU test: checks nvidia-smi, VRAM status, and CUDA capabilities.
    """
    t0 = time.time()
    gpu = get_nvidia_gpu_info()
    whisper = check_whisper_cuda()
    dt = round(time.time() - t0, 3)

    if gpu["available"]:
        msg = f"NVIDIA GPU Active: {gpu['name']} ({gpu['vram_free_mb']}MB / {gpu['vram_total_mb']}MB VRAM free, Driver {gpu['driver_version']})."
        if whisper["available"]:
            msg += f" Faster-Whisper CUDA acceleration is available."
        else:
            msg += f" Note: Whisper is operating on CPU int8 for optimal stability."
        return {
            "success": True,
            "status": "PASS",
            "device": gpu["name"],
            "driver": gpu["driver_version"],
            "vram_total_mb": gpu["vram_total_mb"],
            "vram_free_mb": gpu["vram_free_mb"],
            "whisper_device": whisper["device"],
            "duration_sec": dt,
            "message": msg
        }
    else:
        return {
            "success": True,
            "status": "INFO",
            "device": "Integrated / CPU",
            "whisper_device": "cpu",
            "duration_sec": dt,
            "message": "No discrete NVIDIA GPU detected via nvidia-smi. System is operating in CPU mode (int8 optimized)."
        }

def run_ffmpeg_test(ffmpeg_exe: str = "ffmpeg") -> Dict[str, Any]:
    """
    Run diagnostic FFmpeg test by encoding a synthetic test pattern.
    """
    t0 = time.time()
    enc_info = detect_best_ffmpeg_encoder(ffmpeg_exe)
    enc_name = enc_info["encoder"]
    args = enc_info["args"]

    test_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=1.0:size=640x360:rate=30",
    ] + args + [
        "-pix_fmt", "yuv420p",
        "-f", "null",
        "-"
    ]

    try:
        res = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, **get_win_subprocess_kwargs())
        dt = round(time.time() - t0, 3)
        if res.returncode == 0:
            return {
                "success": True,
                "status": "PASS",
                "encoder": enc_name,
                "description": enc_info["description"],
                "duration_sec": dt,
                "message": f"FFmpeg pipeline functional. Verified encoder: {enc_name} ({enc_info['description']}) in {dt}s."
            }
        else:
            return {
                "success": False,
                "status": "FAIL",
                "encoder": enc_name,
                "error": res.stderr[-300:] if res.stderr else "Unknown error",
                "duration_sec": dt,
                "message": f"FFmpeg test failed: {res.stderr[-200:] if res.stderr else 'Return code non-zero'}"
            }
    except Exception as e:
        return {
            "success": False,
            "status": "ERROR",
            "error": str(e),
            "message": f"FFmpeg execution failed: {e}"
        }


