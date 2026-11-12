# KLYPTRA Studio

<p align="center">
  <strong>Personal AI Video Clipping Studio with Liquid Glass Desktop Experience</strong>
</p>

<p align="center">
  <img src="build/icon.png" width="128" height="128" alt="KLYPTRA Icon" />
</p>

---

## Overview

**KLYPTRA Studio** is a local, privacy-first desktop application designed for video creators, editors, and podcasters. Powered by OpenAI's Whisper model (via Faster-Whisper and CTranslate2) and hardware-accelerated FFmpeg, KLYPTRA automates the end-to-end workflow of transcribing long-form videos, identifying viral-worthy segments, reframing content to 9:16 vertical shorts, and rendering dynamic animated captions.

All AI inferencing and video processing execute 100% locally on your machine—no cloud API keys, monthly subscriptions, or external video uploads required.

---

## Key Features

- **Liquid Glass Interface**: Minimalist macOS/iOS-inspired translucent glass surfaces, dynamic backdrop blur, refined typography, and smooth 60 FPS spring physics.
- **Dual Themes**: Default clean Light Mode and optional Graphite Charcoal (`#1D1F24`) Dark Mode with instant hot-toggle.
- **Local AI Transcription**: Offline speech-to-text powered by `faster-whisper` (CTranslate2) with Tiny, Base, Small, and Medium models.
- **Smart Viral Clip Detection**: Natural language scoring heuristics evaluate pacing, hook strength, topic density, and engagement potential.
- **Active Speaker Tracking & Dynamic Cropping**: Automated facial detection and motion keyframing for 9:16 vertical re-framing.
- **Animated Captions**: Kinetic typography styling with custom word highlights, stroke outlines, and ASS subtitle generation.
- **Flexible Ingest**: Import local video files (`.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`) or ingest public YouTube links for offline processing.
- **Hardware Acceleration**: Automatic detection and utilization of NVIDIA NVENC (`h264_nvenc`), Intel QuickSync (`h264_qsv`), and AMD AMF (`h264_amf`).
- **Compact Settings & Diagnostics**: 5-metric hardware status overview (GPU, RAM, Storage, FFmpeg, Active Whisper Model) with collapsible deep diagnostic logs and synthetic tests.
- **Offline First-Launch Wizard**: Guided initial setup with customizable model storage directories and real-time download progress.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│               Electron Desktop Shell                   │
│   (Single instance, native dialogs, dynamic port)      │
└──────────────────────────┬─────────────────────────────┘
                           │ IPC & HTTP
┌──────────────────────────▼─────────────────────────────┐
│                 Frontend UI Layer                      │
│   (HTML5, Tailwind CSS, Motion Design System)          │
└──────────────────────────┬─────────────────────────────┘
                           │ Authenticated HTTP / WebSockets
┌──────────────────────────▼─────────────────────────────┐
│               FastAPI Python Sidecar                   │
│  ├── Whisper Engine (faster-whisper / ctranslate2)     │
│  ├── Media Engine (FFmpeg / FFprobe hardware pipeline) │
│  ├── Clip Engine (Transcript analysis & heuristics)   │
│  └── SQLite Database (%LOCALAPPDATA%\KLYPTRA)          │
└────────────────────────────────────────────────────────┘
```

---

## System Requirements

- **Operating System**: Windows 10 / 11 (64-bit)
- **Processor**: Multi-core Intel Core i5 / AMD Ryzen 5 or higher
- **Memory**: 8 GB RAM minimum (16 GB recommended for Whisper Small/Medium)
- **Storage**: 2 GB free disk space for base application; additional space recommended for media cache and AI models
- **Graphics (Optional)**: NVIDIA GeForce GTX 1060 or newer (CUDA support for accelerated inferencing and NVENC encoding)

---

## Quick Start (Pre-Built Installer)

1. Download `KLYPTRA-Setup-1.0.0-x64.exe` from the latest release.
2. Run the installer and launch KLYPTRA from your Desktop or Start Menu.
3. On first launch, select your preferred Whisper model (the **Base** model is recommended for general balance) and click **Initialize Studio**.
4. Drag and drop any video or enter a YouTube URL to create your first clip project!

---

## Documentation

- [Installation Guide](INSTALLATION.md)
- [Building from Source](BUILD.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

---

## License

KLYPTRA Studio is distributed under the proprietary and commercial software license. All rights reserved.

