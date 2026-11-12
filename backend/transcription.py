import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple

# Monkey-patch PyAV 19.0+ metadata_errors incompatibility before importing faster_whisper
import av
try:
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception as e:
    logging.warning(f"Could not patch av.open: {e}")

import ctranslate2
from faster_whisper import WhisperModel
from .config import get_models_dir
from .hardware import check_whisper_cuda
from .cache import compute_file_fingerprint, get_transcript_cache_key, get_cached_transcript, save_cached_transcript

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading weights across requests
_LOADED_MODELS: Dict[str, WhisperModel] = {}

PROFILES = {
    "fast": {
        "model": "base",
        "beam_size": 1,
        "word_timestamps": False,
        "vad_min_silence_ms": 400,
        "condition_on_previous_text": False
    },
    "balanced": {
        "model": "small",
        "beam_size": 1,
        "word_timestamps": True,
        "vad_min_silence_ms": 500,
        "condition_on_previous_text": True
    },
    "accurate": {
        "model": "medium",
        "beam_size": 2,
        "word_timestamps": True,
        "vad_min_silence_ms": 500,
        "condition_on_previous_text": True
    }
}

def load_whisper_model(model_size: str = "small", force_cpu: bool = False) -> Tuple[WhisperModel, str]:
    """
    Returns a cached or freshly initialized WhisperModel.
    Attempts GPU (CUDA float16) first; if GPU initialization or runtime fails (e.g. missing cuBLAS DLL),
    it automatically falls back to CPU (int8) with zero application crashing.
    """
    cache_key = f"{model_size}_{'cpu' if force_cpu else 'auto'}"
    if cache_key in _LOADED_MODELS:
        return _LOADED_MODELS[cache_key], "Cached"

    cuda_info = check_whisper_cuda()
    device = "cpu" if force_cpu or not cuda_info["available"] else cuda_info["device"]
    compute_type = "int8" if device == "cpu" else cuda_info["compute_type"]

    cur_models_dir = get_models_dir()
    cur_models_dir.mkdir(parents=True, exist_ok=True)

    if device == "cuda":
        try:
            logger.info(f"Attempting WhisperModel({model_size}) on CUDA ({compute_type})...")
            model = WhisperModel(
                model_size_or_path=model_size,
                device="cuda",
                compute_type=compute_type,
                download_root=str(cur_models_dir)
            )
            # Verify CUDA runtime doesn't throw cublas64_12.dll missing on first encode
            import numpy as np
            import ctranslate2
            dummy_features = ctranslate2.StorageView.from_array(np.zeros((1, 80, 100), dtype=np.float32))
            model.model.encode(dummy_features)
            
            _LOADED_MODELS[cache_key] = model
            return model, "NVIDIA GPU (CUDA, float16)"
        except Exception as e:
            logger.warning(f"CUDA initialization failed ({e}). Automatically switching to CPU fallback (int8).")
            device = "cpu"
            compute_type = "int8"

    # CPU Fallback
    logger.info(f"Loading WhisperModel({model_size}) on CPU ({compute_type})...")
    model = WhisperModel(
        model_size_or_path=model_size,
        device="cpu",
        compute_type="int8",
        download_root=str(cur_models_dir)
    )
    _LOADED_MODELS[cache_key] = model
    return model, "CPU (Optimized int8)"

def transcribe_audio_file(
    audio_path: str,
    output_json_path: str,
    profile: str = "balanced",
    model_size: Optional[str] = None,
    language: Optional[str] = None,
    source_video_path: Optional[str] = None,
    force_cpu: bool = False,
    vad_filter: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    High-performance speech transcription with caching, profile tuning, and CUDA/CPU fallback.
    """
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    out_file = Path(output_json_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    prof_config = PROFILES.get(profile.lower(), PROFILES["balanced"])
    chosen_model = model_size if model_size else prof_config["model"]

    # 1. Check Transcript Cache
    cache_key = None
    if source_video_path and Path(source_video_path).exists():
        fp = compute_file_fingerprint(source_video_path)
        cache_key = get_transcript_cache_key(fp, chosen_model, language, profile)
        cached = get_cached_transcript(cache_key)
        if cached:
            logger.info("Reusing cached transcript!")
            if progress_callback:
                progress_callback(100.0, "Loaded from cache (Instant)!")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(cached, f, indent=2, ensure_ascii=False)
            cached["from_cache"] = True
            return cached

    start_time = time.time()

    if progress_callback:
        progress_callback(10.0, f"Initializing Whisper '{chosen_model}' engine...")

    model, device_desc = load_whisper_model(chosen_model, force_cpu=force_cpu)

    if progress_callback:
        progress_callback(25.0, f"Transcribing audio on {device_desc}...")

    transcribe_opts = {
        "beam_size": prof_config["beam_size"],
        "word_timestamps": prof_config["word_timestamps"],
        "condition_on_previous_text": prof_config["condition_on_previous_text"],
        "vad_filter": vad_filter,
        "vad_parameters": dict(min_silence_duration_ms=prof_config["vad_min_silence_ms"])
    }
    if language and language != "auto":
        transcribe_opts["language"] = language

    try:
        segments_generator, info = model.transcribe(str(audio_file), **transcribe_opts)
        detected_lang = info.language
        lang_probability = round(info.language_probability, 3)
        duration = round(info.duration, 2)
        segments_list = list(segments_generator)
    except Exception as e:
        logger.warning(f"Transcription on {device_desc} failed: {e}. Retrying on CPU fallback...")
        model, device_desc = load_whisper_model(chosen_model, force_cpu=True)
        segments_generator, info = model.transcribe(str(audio_file), **transcribe_opts)
        detected_lang = info.language
        lang_probability = round(info.language_probability, 3)
        duration = round(info.duration, 2)
        segments_list = list(segments_generator)

    segments_data: List[Dict[str, Any]] = []
    total_words = 0

    for i, seg in enumerate(segments_list):
        words_list = []
        if hasattr(seg, "words") and seg.words:
            for w in seg.words:
                words_list.append({
                    "word": w.word,
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                    "probability": round(w.probability, 2)
                })
                total_words += 1

        segments_data.append({
            "id": i,
            "seek": seg.seek,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "words": words_list
        })

    full_transcript_text = " ".join(s["text"] for s in segments_data).strip()
    elapsed = round(time.time() - start_time, 2)

    result = {
        "language": detected_lang,
        "language_probability": lang_probability,
        "duration": duration,
        "total_segments": len(segments_data),
        "total_words": total_words,
        "device_used": device_desc,
        "profile": profile,
        "model": chosen_model,
        "processing_time_sec": elapsed,
        "from_cache": False,
        "full_text": full_transcript_text,
        "segments": segments_data
    }

    # Save to project transcript path
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Save to global cache
    if cache_key:
        save_cached_transcript(cache_key, result)

    if progress_callback:
        progress_callback(100.0, f"Transcription completed in {elapsed}s ({detected_lang.upper()}).")

    return result
