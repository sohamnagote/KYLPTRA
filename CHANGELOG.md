# Changelog

All notable changes to KLYPTRA Studio are documented in this file.

---

## [1.0.0] - 2026-11-12

### Added
- **Liquid Glass UI Redesign**: Apple-inspired translucent surfaces, frosted glass sidebars, subtle backdrop blur, and high-contrast typography across all screens.
- **Centralized Motion System**: 60 FPS spring physics, micro-interactions (hover, press, scale), smooth panel collapses, and seamless page transitions without video reloads.
- **Dual Themes**: Default clean Light Mode and optional Graphite Charcoal (`#1D1F24`) Dark Mode with instant hot-toggle and zero flash of unstyled content.
- **Streamlined Settings & Exports**:
  - Replaced oversized hardware cards with a compact 5-metric status bar (GPU, RAM, Storage, FFmpeg, Whisper Model).
  - Clear AI Processing Presets (Fast, Balanced, Accurate).
  - Compact Whisper Model Manager with real-time download status and directory selection.
  - Collapsible Advanced Diagnostics section with synthetic tests and live diagnostic logs.
- **First-Launch Onboarding Wizard**: Guided offline Whisper model selection, progress bar indicator, and custom storage folder selector.
- **Security & Desktop Hardening**:
  - Session token verification (`X-Klyptra-Token`) for loopback API calls.
  - Path traversal validation (`_validate_safe_media_path`) preventing directory escapes.
  - Subprocess window suppression (`CREATE_NO_WINDOW`) eliminating flashing CMD prompts.
  - 10 GB file size limit protection.
- **Distribution Packaging**:
  - PyInstaller backend sidecar integration (`klyptra-backend.exe`).
  - Electron Builder configuration for Windows NSIS Installer (`.exe`) and portable zip (`.zip`).
  - Bundled standalone FFmpeg and FFprobe binaries.
- **Automated Testing Suite**: 31 comprehensive backend tests covering hardware detection, SQLite operations, audio processing, FFmpeg integration, and task queuing.
