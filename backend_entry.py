import os
import sys
import multiprocessing

# PyInstaller Windows frozen multiprocessing & noconsole safety
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

def main():
    multiprocessing.freeze_support()
    import uvicorn
    from backend.main import app

    port = int(os.environ.get("KLYPTRA_PORT", "8000"))
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False
    )

if __name__ == "__main__":
    main()
