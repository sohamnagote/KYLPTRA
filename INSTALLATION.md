# KLYPTRA Studio | Installation Guide

This guide details how to install and configure KLYPTRA Studio on Windows systems.

---

## Method 1: Windows NSIS Installer (Recommended)

1. Download **`KLYPTRA-Setup-1.0.0-x64.exe`** from the release distribution artifacts.
2. Double-click the installer.
3. Choose installation options:
   - Install for current user (recommended: no UAC elevation required) or all users.
   - Choose destination folder (default: `%LOCALAPPDATA%\Programs\klyptra-studio`).
4. Click **Install**. The installer configures Desktop and Start Menu shortcuts.
5. Launch **KLYPTRA Studio**.

---

## Method 2: Portable ZIP Package

For environments where installation is restricted or for portable USB drive operation:

1. Download **`KLYPTRA-1.0.0-win-x64-portable.zip`**.
2. Extract the archive into any preferred folder (e.g., `D:\Tools\KLYPTRA`).
3. Run **`KLYPTRA Studio.exe`** directly from the extracted directory.
4. User configurations and projects are persisted safely to `%LOCALAPPDATA%\KLYPTRA` by default.

---

## First-Launch Setup Wizard

When launching KLYPTRA Studio for the first time:

1. The **Welcome to KLYPTRA** wizard appears automatically.
2. Select an initial AI speech recognition model:
   - **Tiny (~75 MB)**: Fastest processing, lowest RAM footprint (~1 GB). Ideal for quick drafts and laptops.
   - **Base (~145 MB, Recommended)**: Excellent balance between transcription speed and English accuracy.
   - **Small (~480 MB)**: High accuracy for accented speech, multi-speaker dialogue, and background music.
   - **Medium (~1.5 GB)**: Maximum accuracy and punctuation quality for studio-grade transcription.
3. Review or customize the **AI Models Storage Location** (default: `%LOCALAPPDATA%\KLYPTRA\models\whisper`). You can specify an external SSD if disk space is limited.
4. Click **Download & Initialize Studio**. Once the progress indicator hits 100%, the full studio interface unlocks immediately.

---

## Storage & File Paths

KLYPTRA maintains all user data in a structured, isolated application directory:

| Content | Path | Description |
| :--- | :--- | :--- |
| **Database** | `%LOCALAPPDATA%\KLYPTRA\database\klyptra.db` | SQLite database storing project metadata, clip logs, and presets |
| **AI Models** | `%LOCALAPPDATA%\KLYPTRA\models\whisper` | Downloaded Whisper model weights |
| **Projects** | `%LOCALAPPDATA%\KLYPTRA\projects` | Ingested source videos, audio extractions, and project files |
| **Exports** | `%LOCALAPPDATA%\KLYPTRA\exports` | Rendered MP4 clips and subtitle tracks |
| **Cache** | `%LOCALAPPDATA%\KLYPTRA\cache` | Temporary audio chunks and intermediate render buffers |
| **Logs** | `%LOCALAPPDATA%\KLYPTRA\logs\klyptra.log` | Rotating diagnostic logs (max 5 MB x 3 backups) |

---

## Troubleshooting

### Antivirus False Positives
Because KLYPTRA bundles a Python CTranslate2 binary compiled via PyInstaller, third-party heuristics or Windows Defender may occasionally display an unrecognized binary alert.
- Click **More Info** -> **Run Anyway**.
- Alternatively, add an exclusion rule for `%LOCALAPPDATA%\Programs\klyptra-studio`.

### Port Conflicts
By default, KLYPTRA binds its internal API service to `127.0.0.1:8000`. If port 8000 is occupied by another local service, KLYPTRA automatically detects the collision and dynamically binds to the next available ephemeral port.

