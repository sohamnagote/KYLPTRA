"""
KLYPTRA Backend Initialization
Ensures environment, hardware hooks, and PyAV compatibility patches are active at module load.
"""
import logging

logger = logging.getLogger(__name__)

# Monkey-patch PyAV 14+ / 19+ metadata_errors incompatibility before any library loads it
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception as e:
    logger.debug(f"PyAV monkey-patch check: {e}")
