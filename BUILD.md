# KLYPTRA Studio | Build Guide

This document describes how to build KLYPTRA Studio from source code, produce the standalone Python sidecar with PyInstaller, and package the final Windows Electron installer with electron-builder.

---

## 1. Prerequisites

- **Windows 10 or 11 (64-bit)**
- **Node.js**: v18.0.0 or higher (`node -v`, `npm -v`)
- **Python**: 3.10 to 3.14 (64-bit) with `pip`
- **FFmpeg & FFprobe**: Static Windows builds placed in `resources/bin/` or accessible via PATH
- **Git**

---

## 2. Environment Setup

### Clone the Repository
```bash
git clone https://github.com/your-org/klyptra-studio.git
cd klyptra-studio
```

### Install Node Dependencies
```bash
npm install
```

### Install Python Dependencies
```bash
pip install -r backend/requirements.txt
pip install pyinstaller pillow pytest
```

---

## 3. Running in Development Mode

To run KLYPTRA in development mode with live reload:

### Terminal 1: Start Backend
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Start Electron Shell
```bash
npm start
```

Or execute the provided batch script:
```bash
start.bat
```

---

## 4. Building the Production Windows Distribution

Building the production executable is a two-step process:

### Step 4.1: Generate App Icon
```bash
python scripts/generate_icon.py
```
This generates `build/icon.ico` and `build/icon.png`.

### Step 4.2: Copy FFmpeg & FFprobe Binaries
Ensure `ffmpeg.exe` and `ffprobe.exe` are present in `resources/bin/`:
```bash
mkdir -p resources/bin
# Copy binaries into resources/bin/
```

### Step 4.3: Compile Python Backend Sidecar
Compile the Python backend into a single directory containing `klyptra-backend.exe`:
```bash
python -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name klyptra-backend ^
  --add-data "backend;backend" ^
  --add-data "index.html;." ^
  --add-data "app;app" ^
  --hidden-import uvicorn ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import fastapi ^
  --hidden-import ctranslate2 ^
  --hidden-import faster_whisper ^
  --hidden-import yt_dlp ^
  --hidden-import cv2 ^
  --hidden-import onnxruntime ^
  backend_entry.py
```

Move or copy the generated `dist/klyptra-backend` into `resources/backend/`:
```bash
xcopy /E /I /Y dist\klyptra-backend resources\backend
```

### Step 4.4: Package with Electron Builder
Run the electron packaging script:
```bash
npm run dist
```
This produces:
- `dist/KLYPTRA-Setup-1.0.0-x64.exe` (NSIS One-Click / Assisted Windows Installer)
- `dist/KLYPTRA-1.0.0-win-x64-portable.zip` (Standalone Portable Archive)

---

## 5. Verification & Testing

Run the automated backend test suite:
```bash
python -m pytest backend/tests/ -v
```

Run the visual and motion layout test suite:
```bash
node test_app_motion.js
```
