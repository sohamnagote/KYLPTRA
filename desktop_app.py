"""
KLYPTRA Studio — Native Windows Desktop Application
Powered by Microsoft Edge WebView2 (Zero Electron Architecture)
"""

import os
import sys
import time
import socket
import threading
import secrets
import webview

# PyInstaller Windows frozen multiprocessing & noconsole safety
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

def find_open_port(preferred=8000):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", preferred))
        s.close()
        return preferred
    except OSError:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

def run_server(port, session_token):
    import uvicorn
    from backend.main import app
    from backend.config import init_storage_directories
    from backend.database import init_db

    init_storage_directories()
    init_db()

    os.environ["KLYPTRA_PORT"] = str(port)
    os.environ["KLYPTRA_SESSION_TOKEN"] = session_token
    os.environ["KLYPTRA_ENV"] = "production"

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

class KlyptraNativeAPI:
    """Native Windows Bridges exposed to the frontend JavaScript runtime."""
    def __init__(self, window):
        self.window = window

    def select_folder(self):
        try:
            res = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            return res[0] if res and len(res) > 0 else None
        except Exception as e:
            print(f"[Desktop Bridge] select_folder error: {e}")
            return None

    def select_video_file(self):
        try:
            res = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=('Video Files (*.mp4;*.mov;*.mkv;*.webm;*.avi;*.m4v)', 'All Files (*.*)')
            )
            return res[0] if res and len(res) > 0 else None
        except Exception as e:
            print(f"[Desktop Bridge] select_video_file error: {e}")
            return None

def wait_for_server(port, retries=50):
    import urllib.request
    url = f"http://127.0.0.1:{port}/api/health"
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False

def main():
    import multiprocessing
    multiprocessing.freeze_support()

    port = find_open_port(8000)
    session_token = secrets.token_hex(32)
    os.environ["KLYPTRA_SESSION_TOKEN"] = session_token

    # Start FastAPI daemon thread
    server_thread = threading.Thread(
        target=run_server,
        args=(port, session_token),
        daemon=True,
        name="KlyptraBackendServer"
    )
    server_thread.start()

    if not wait_for_server(port):
        sys.exit(1)

    # Resolve application icon
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    
    icon_path = os.path.join(base_dir, "build", "icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_dir, "public", "brand", "klyptra-icon-256.png")

    target_url = f"http://127.0.0.1:{port}/"

    # Create Native Microsoft Edge WebView2 window
    window = webview.create_window(
        title="KLYPTRA Studio",
        url=target_url,
        width=1400,
        height=880,
        min_size=(1024, 680),
        background_color="#F4F5F8",
        easy_drag=False
    )
    window.expose(KlyptraNativeAPI(window).select_folder, KlyptraNativeAPI(window).select_video_file)

    # Launch native desktop application using WebView2 (edgechromium)
    webview.start(
        gui="edgechromium",
        debug=False,
        icon=icon_path if os.path.exists(icon_path) else None
    )

if __name__ == "__main__":
    main()

