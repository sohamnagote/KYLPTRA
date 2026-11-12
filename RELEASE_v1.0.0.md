# KLYPTRA Studio v1.0.0 — Release Manifest

**Date:** November 12, 2026  
**Version:** `v1.0.0` (Tag: `v1.0.0`, Commit: `34b7be3`)  
**Target Architecture:** Native Windows x64 (Microsoft Edge WebView2 Desktop Shell — Zero Electron)

---

## 1. Distribution Artifacts & SHA-256 Checksums

The production build was compiled and packaged directly from the workspace without Electron overhead. The runtime uses the high-performance Microsoft Edge WebView2 control backed by a local loopback FastAPI backend.

| Artifact File | Size | Format | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`KLYPTRA-Setup-1.0.0-x64.exe`** | 289.10 MB (`303,144,640` B) | NSIS Standard Installer (Solid LZMA) | `6B7A428965398528ABB10B3E127581473F3E64D7DEC156CA4E3DE5819DC91931` |
| **`KLYPTRA-1.0.0-win-x64-portable.zip`** | 378.31 MB (`396,685,799` B) | Portable Standalone Archive (7-Zip) | `EE6A6E943698738730546B2AE35CB7528F0442BAE811929788434294285CBD9C` |
| **`KLYPTRA.exe`** | Direct Executable | Windows 64-bit Desktop Application | Packaged within `dist\KLYPTRA\` |

*Path to setup installer on disk:* `dist/KLYPTRA-Setup-1.0.0-x64.exe`  
*Path to portable zip on disk:* `dist/KLYPTRA-1.0.0-win-x64-portable.zip`

---

## 2. Core Architectural Upgrades

### Zero Electron Native Windows Shell
- **Runtime:** Completely replaced heavy Chromium packaging with native Windows `pywebview` utilizing the system's Microsoft Edge WebView2 runtime.
- **Backend Lifecycle:** Automatic ephemeral loopback port negotiation (`127.0.0.1:8000+`) with a secure 256-bit cryptographically randomized session token (`KLYPTRA_SESSION_TOKEN`).
- **Native Bridges:** Added native Windows WinForms folder and file dialogue pickers (`select_folder`, `select_video_file`) exposed directly to the web client.
- **Bundled Engine:** Includes offline `ffmpeg.exe` and `ffprobe.exe` in `resources/bin/`.

### KLYPTRA Flowfield GPU Shader (Continuous 60 FPS)
- **Engine:** WebGL 2.0 / WebGL 1.0 GPU shader with continuous domain-warped fractional Brownian motion (fBm) fluid ribbons and specular caustics.
- **Dynamic Lighting & Palettes:**
  - *Light Theme:* Pearl, silver, and soft muted lavender waves (`#F4F5F8` base).
  - *Dark Theme:* Deep graphite, slate charcoal, and subtle indigo ribbons.
- **Non-blocking Surfaces:** Translucent Liquid Glass cards (`backdrop-filter: blur(28px) saturate(180%)`) layered directly above the active shader canvas.
- **Diagnostic Verification Hook:** `window.__klyptraShader.getFrameState()` returns real-time rendering statistics, total active frames, and uptime.

### Original Brand Identity & Iconography
- Replaced all generic AI sparkle/wand icons with the **KLYPTRA Architectural 'K' Cut mark**:
  - Precision trimming cut geometry representing video keyframes and razor trimming.
  - Linear playhead pillar and timeline baseline.
- **Assets Generated:**
  - Vector masters: `public/brand/klyptra-logo.svg` and `public/brand/klyptra-wordmark.svg`.
  - Icon suite: PNG sizes at 16px, 24px, 32px, 48px, 64px, 128px, 256px, and 512px.
  - Multi-resolution Windows application icon: `build/icon.ico`.

### Motion Design System
- **Directional Parallax Navigation:** Workspace transitions slide forward or backward horizontally based on view hierarchy (`New Project` → `Clips` → `Editor` → `Projects` → `Settings`) rather than using generic crossfades.
- **3D Cursor-Reactive Tilt:** The video dropzone computes cursor angle and applies smooth 3D perspective rotation on hover with spring recovery.
- **Tactile Feedback:** Apple-inspired button compression scales (`scale: 0.97`) with micro-spring easing.
- **Launch Reveal:** Opening splash sequence that dissolves into the live application workspace.

---

## 3. GitHub Remote & Distribution Status

- **Git Commit:** `34b7be3` on branch `release/v1.0.0`
- **Git Tag:** `v1.0.0`
- **Remote Push Status:** The local Git repository currently has no remote endpoint configured (`git remote` is empty), and no GitHub Personal Access Token or SSH key is present in the environment.
- **Command to push when ready:**
  ```powershell
  git remote add origin https://github.com/<your-username>/klyptra.git
  git push -u origin release/v1.0.0
  git push origin v1.0.0
  ```

