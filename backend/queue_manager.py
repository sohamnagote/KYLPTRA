import threading
import queue
import time
import logging
from typing import Callable, Any, Dict, Optional
from .tasks import update_task, is_task_cancelled

logger = logging.getLogger(__name__)

# Concurrency limits: 1 heavy transcription at a time, 2 renders
_TRANSCRIPTION_SEMAPHORE = threading.Semaphore(1)
_RENDER_SEMAPHORE = threading.Semaphore(2)

def enqueue_transcription(task_id: str, fn: Callable[[], Any]):
    """
    Executes a transcription function with strict concurrency 1.
    If another transcription is running, task status updates to 'queued'.
    """
    def worker():
        if is_task_cancelled(task_id):
            return

        acquired = _TRANSCRIPTION_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            update_task(task_id, message="Queued for AI speech processing (waiting for active task)...", status="queued")
            _TRANSCRIPTION_SEMAPHORE.acquire(blocking=True)

        try:
            if is_task_cancelled(task_id):
                return
            update_task(task_id, status="processing")
            fn()
        finally:
            _TRANSCRIPTION_SEMAPHORE.release()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t

def enqueue_render(task_id: str, fn: Callable[[], Any]):
    """
    Executes a render function with controlled concurrency (max 2).
    """
    def worker():
        if is_task_cancelled(task_id):
            return

        acquired = _RENDER_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            update_task(task_id, message="Queued for video encoding...", status="queued")
            _RENDER_SEMAPHORE.acquire(blocking=True)

        try:
            if is_task_cancelled(task_id):
                return
            update_task(task_id, status="processing")
            fn()
        finally:
            _RENDER_SEMAPHORE.release()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t

