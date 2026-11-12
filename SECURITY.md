# Security Policy for KLYPTRA Studio

KLYPTRA Studio is built around a privacy-first, zero-telemetry, zero-cloud architecture. All AI inferencing, audio extraction, transcript storage, and video rendering happen strictly on the user's local hardware.

---

## Security Model & Hardening

1. **Loopback Isolation**: The local API server is strictly bound to `127.0.0.1` (IPv4 loopback). It never binds to `0.0.0.0` or external network adapters.
2. **Per-Session Ephemeral Authorization**: When spawned from the Electron desktop shell, an unguessable 256-bit cryptographically secure token (`X-Klyptra-Token`) is generated in memory and injected into internal HTTP headers via Electron's `webRequest.onBeforeSendHeaders`. All non-health API endpoints reject any unauthorized request lacking this token.
3. **Strict Path Traversal Defenses**: All media streaming, project management, and asset loading routes invoke `_validate_safe_media_path()` to sanitize target paths against `..` escapes and ensure paths only originate from verified project roots or user-designated asset folders.
4. **Subprocess Window Suppression**: Subprocess invocations (FFmpeg, FFprobe, yt-dlp, powershell) enforce `subprocess.CREATE_NO_WINDOW` (flag `0x08000000`) on Windows to prevent console interception or flashing command prompt windows.
5. **No Telemetry / No Phone Home**: KLYPTRA does not track user behavior, upload crash dumps to third-party endpoints, or collect personally identifiable information.

---

## Reporting a Vulnerability

If you discover a security vulnerability in KLYPTRA Studio:

1. **Do not create a public issue on GitHub.**
2. Email your disclosure to `security@klyptra.local` or contact the lead maintainer privately.
3. Please include:
   - A description of the vulnerability.
   - Steps or proof-of-concept script to reproduce.
   - The version of KLYPTRA and operating system.
4. You will receive an acknowledgment within 48 hours and regular updates until resolution.
