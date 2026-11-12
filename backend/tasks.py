import threading
import uuid
import time
from typing import Dict, Any, Optional, Callable

# Thread-safe in-memory task tracker
_TASKS_LOCK = threading.Lock()
_TASKS: Dict[str, Dict[str, Any]] = {}

def create_task(task_type: str, title: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    task_id = str(uuid.uuid4())
    with _TASKS_LOCK:
        _TASKS[task_id] = {
            "id": task_id,
            "type": task_type,
            "title": title,
            "status": "pending",
            "progress": 0.0,
            "message": "Initializing...",
            "metadata": metadata or {},
            "result": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
            "cancelled": False
        }
    return task_id

def update_task(task_id: str, progress: Optional[float] = None, message: Optional[str] = None, status: Optional[str] = None, result: Any = None, error: Optional[str] = None):
    with _TASKS_LOCK:
        if task_id in _TASKS:
            t = _TASKS[task_id]
            if progress is not None:
                t["progress"] = max(0.0, min(100.0, progress))
            if message is not None:
                t["message"] = message
            if status is not None:
                t["status"] = status
            if result is not None:
                t["result"] = result
            if error is not None:
                t["error"] = error
                t["status"] = "error"
            t["updated_at"] = time.time()

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with _TASKS_LOCK:
        return _TASKS.get(task_id)

def cancel_task(task_id: str) -> bool:
    with _TASKS_LOCK:
        if task_id in _TASKS:
            _TASKS[task_id]["cancelled"] = True
            _TASKS[task_id]["status"] = "cancelled"
            _TASKS[task_id]["message"] = "Operation cancelled by user."
            return True
        return False

def is_task_cancelled(task_id: str) -> bool:
    with _TASKS_LOCK:
        t = _TASKS.get(task_id)
        return t.get("cancelled", False) if t else False

def run_in_background(target: Callable, *args, **kwargs) -> threading.Thread:
    thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread

