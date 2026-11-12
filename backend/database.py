import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from .config import DATABASE_PATH, init_storage_directories

def get_connection() -> sqlite3.Connection:
    init_storage_directories()
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                source_path TEXT NOT NULL,
                duration REAL NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                fps REAL NOT NULL,
                codec TEXT NOT NULL,
                has_audio INTEGER NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                error_message TEXT,
                language TEXT,
                transcript_path TEXT
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS clips (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration REAL NOT NULL,
                score INTEGER NOT NULL,
                score_reasons TEXT NOT NULL,
                hook_summary TEXT,
                transcript_text TEXT,
                aspect_ratio TEXT NOT NULL DEFAULT '9:16',
                crop_x REAL DEFAULT 0.5,
                crop_y REAL DEFAULT 0.5,
                captions_enabled INTEGER NOT NULL DEFAULT 1,
                caption_text TEXT,
                caption_font TEXT DEFAULT 'Inter',
                caption_size INTEGER DEFAULT 24,
                caption_color TEXT DEFAULT '#FFFFFF',
                caption_highlight_color TEXT DEFAULT '#8B5CF6',
                caption_position TEXT DEFAULT 'bottom',
                volume REAL DEFAULT 1.0,
                is_muted INTEGER DEFAULT 0,
                preview_path TEXT,
                status TEXT NOT NULL DEFAULT 'candidate',
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS exports (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                clip_id TEXT NOT NULL,
                output_filename TEXT NOT NULL,
                output_path TEXT NOT NULL,
                resolution TEXT NOT NULL DEFAULT '1080p',
                aspect_ratio TEXT NOT NULL DEFAULT '9:16',
                fps INTEGER NOT NULL DEFAULT 30,
                file_size INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'completed',
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (clip_id) REFERENCES clips(id) ON DELETE CASCADE
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS caption_presets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_builtin INTEGER NOT NULL DEFAULT 0,
                font_name TEXT NOT NULL DEFAULT 'Inter',
                font_size INTEGER NOT NULL DEFAULT 24,
                primary_color TEXT NOT NULL DEFAULT '#FFFFFF',
                highlight_color TEXT NOT NULL DEFAULT '#8273D6',
                bg_color TEXT DEFAULT '',
                outline_color TEXT DEFAULT '#181818',
                position TEXT NOT NULL DEFAULT 'bottom',
                animation TEXT NOT NULL DEFAULT 'Fade',
                words_per_line INTEGER NOT NULL DEFAULT 4,
                max_line_length INTEGER NOT NULL DEFAULT 26,
                created_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS brand_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                logo_path TEXT,
                primary_color TEXT NOT NULL DEFAULT '#8273D6',
                secondary_color TEXT NOT NULL DEFAULT '#F0EDFC',
                caption_font TEXT NOT NULL DEFAULT 'Inter',
                caption_preset_id TEXT,
                watermark_path TEXT,
                watermark_position TEXT NOT NULL DEFAULT 'top-right',
                watermark_opacity REAL NOT NULL DEFAULT 0.85,
                intro_path TEXT,
                outro_path TEXT,
                default_aspect_ratio TEXT NOT NULL DEFAULT '9:16',
                default_quality TEXT NOT NULL DEFAULT '1080p',
                created_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS broll_assets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'video',
                category TEXT NOT NULL DEFAULT 'General',
                tags TEXT,
                duration REAL DEFAULT 0.0,
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                thumbnail_path TEXT,
                created_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS voiceovers (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                clip_id TEXT,
                text TEXT NOT NULL,
                voice TEXT NOT NULL DEFAULT 'Microsoft David',
                speed INTEGER NOT NULL DEFAULT 0,
                pitch INTEGER NOT NULL DEFAULT 0,
                volume REAL NOT NULL DEFAULT 1.0,
                file_path TEXT NOT NULL,
                duration REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
            """)

            # Safe column migrations for existing projects table
            prj_cols = [c[1] for c in conn.execute("PRAGMA table_info(projects)").fetchall()]
            if "custom_instruction" not in prj_cols:
                conn.execute("ALTER TABLE projects ADD COLUMN custom_instruction TEXT")
            if "silence_ranges_json" not in prj_cols:
                conn.execute("ALTER TABLE projects ADD COLUMN silence_ranges_json TEXT")
            if "filler_words_json" not in prj_cols:
                conn.execute("ALTER TABLE projects ADD COLUMN filler_words_json TEXT")

            # Safe column migrations for existing clips table
            clip_cols = [c[1] for c in conn.execute("PRAGMA table_info(clips)").fetchall()]
            new_clip_fields = {
                "custom_instruction": "TEXT",
                "score_breakdown": "TEXT",
                "titles_json": "TEXT",
                "hooks_json": "TEXT",
                "description": "TEXT",
                "hashtags": "TEXT",
                "caption_preset": "TEXT",
                "caption_animation": "TEXT DEFAULT 'Fade'",
                "caption_speed": "REAL DEFAULT 1.0",
                "caption_intensity": "REAL DEFAULT 1.0",
                "caption_words_per_line": "INTEGER DEFAULT 4",
                "caption_highlight_words": "INTEGER DEFAULT 1",
                "reframing_mode": "TEXT DEFAULT 'single'",
                "audio_denoise": "INTEGER DEFAULT 0",
                "audio_normalize": "INTEGER DEFAULT 0",
                "audio_clarity": "INTEGER DEFAULT 0",
                "filler_removal": "INTEGER DEFAULT 0",
                "music_ducking": "INTEGER DEFAULT 0",
                "bg_music_path": "TEXT",
                "bg_music_volume": "REAL DEFAULT 0.2",
                "overlays_json": "TEXT",
                "brand_profile_id": "TEXT",
                "transcript_edits_json": "TEXT"
            }
            for f_name, f_type in new_clip_fields.items():
                if f_name not in clip_cols:
                    conn.execute(f"ALTER TABLE clips ADD COLUMN {f_name} {f_type}")

            # Populate built-in presets if empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM caption_presets WHERE is_builtin = 1")
            if cur.fetchone()[0] == 0:
                _seed_builtin_presets(conn)
    finally:
        conn.close()

def create_project(
    project_id: str,
    name: str,
    source_filename: str,
    source_path: str,
    duration: float,
    width: int,
    height: int,
    fps: float,
    codec: str,
    has_audio: bool,
    file_size: int
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO projects (
                id, name, created_at, updated_at, source_filename, source_path,
                duration, width, height, fps, codec, has_audio, file_size, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'created')
            """, (
                project_id, name, now, now, source_filename, source_path,
                duration, width, height, fps, codec, 1 if has_audio else 0, file_size
            ))
        return get_project(project_id)
    finally:
        conn.close()

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        res["has_audio"] = bool(res["has_audio"])
        return res
    finally:
        conn.close()

def list_projects() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = cur.fetchall()
        projects = []
        for r in rows:
            d = dict(r)
            d["has_audio"] = bool(d["has_audio"])
            # Get clip count
            c_cur = conn.cursor()
            c_cur.execute("SELECT COUNT(*) as count FROM clips WHERE project_id = ?", (d["id"],))
            d["clip_count"] = c_cur.fetchone()["count"]
            projects.append(d)
        return projects
    finally:
        conn.close()

def update_project_status(
    project_id: str,
    status: str,
    error_message: Optional[str] = None,
    language: Optional[str] = None,
    transcript_path: Optional[str] = None
):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            fields = ["status = ?", "updated_at = ?"]
            vals = [status, now]
            if error_message is not None:
                fields.append("error_message = ?")
                vals.append(error_message)
            if language is not None:
                fields.append("language = ?")
                vals.append(language)
            if transcript_path is not None:
                fields.append("transcript_path = ?")
                vals.append(transcript_path)
            vals.append(project_id)
            query = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
            conn.execute(query, tuple(vals))
    finally:
        conn.close()

def delete_project(project_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cur.rowcount > 0
    finally:
        conn.close()

def create_clips_batch(clips_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            for c in clips_data:
                score_breakdown_str = json.dumps(c.get("score_breakdown", {})) if isinstance(c.get("score_breakdown"), dict) else (c.get("score_breakdown") or "{}")
                titles_str = json.dumps(c.get("titles", [])) if isinstance(c.get("titles"), list) else (c.get("titles_json") or "[]")
                hooks_str = json.dumps(c.get("hooks", [])) if isinstance(c.get("hooks"), list) else (c.get("hooks_json") or "[]")
                overlays_str = json.dumps(c.get("overlays", [])) if isinstance(c.get("overlays"), list) else (c.get("overlays_json") or "[]")
                edits_str = json.dumps(c.get("transcript_edits", [])) if isinstance(c.get("transcript_edits"), list) else (c.get("transcript_edits_json") or "[]")

                conn.execute("""
                INSERT INTO clips (
                    id, project_id, title, start_time, end_time, duration,
                    score, score_reasons, hook_summary, transcript_text,
                    aspect_ratio, crop_x, crop_y, captions_enabled,
                    caption_text, caption_font, caption_size, caption_color,
                    caption_highlight_color, caption_position, volume, is_muted,
                    preview_path, status, created_at,
                    custom_instruction, score_breakdown, titles_json, hooks_json,
                    description, hashtags, caption_preset, caption_animation,
                    caption_speed, caption_intensity, caption_words_per_line,
                    caption_highlight_words, reframing_mode, audio_denoise,
                    audio_normalize, audio_clarity, filler_removal, music_ducking,
                    bg_music_path, bg_music_volume, overlays_json, brand_profile_id,
                    transcript_edits_json
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?
                )
                """, (
                    c["id"], c["project_id"], c["title"], c["start_time"], c["end_time"], c["duration"],
                    c["score"], json.dumps(c.get("score_reasons", [])), c.get("hook_summary", ""), c.get("transcript_text", ""),
                    c.get("aspect_ratio", "9:16"), c.get("crop_x", 0.5), c.get("crop_y", 0.5),
                    1 if c.get("captions_enabled", True) else 0,
                    c.get("caption_text", c.get("transcript_text", "")),
                    c.get("caption_font", "Inter"), c.get("caption_size", 24),
                    c.get("caption_color", "#FFFFFF"), c.get("caption_highlight_color", "#8B5CF6"),
                    c.get("caption_position", "bottom"), c.get("volume", 1.0),
                    1 if c.get("is_muted", False) else 0,
                    c.get("preview_path"), c.get("status", "candidate"), now,
                    c.get("custom_instruction", ""),
                    score_breakdown_str,
                    titles_str,
                    hooks_str,
                    c.get("description", ""),
                    c.get("hashtags", ""),
                    c.get("caption_preset", "Minimal Clean"),
                    c.get("caption_animation", "Fade"),
                    float(c.get("caption_speed", 1.0)),
                    float(c.get("caption_intensity", 1.0)),
                    int(c.get("caption_words_per_line", 4)),
                    1 if c.get("caption_highlight_words", True) else 0,
                    c.get("reframing_mode", "single"),
                    1 if c.get("audio_denoise", False) else 0,
                    1 if c.get("audio_normalize", False) else 0,
                    1 if c.get("audio_clarity", False) else 0,
                    1 if c.get("filler_removal", False) else 0,
                    1 if c.get("music_ducking", False) else 0,
                    c.get("bg_music_path", ""),
                    float(c.get("bg_music_volume", 0.2)),
                    overlays_str,
                    c.get("brand_profile_id", ""),
                    edits_str
                ))
        return list_clips_for_project(clips_data[0]["project_id"]) if clips_data else []
    finally:
        conn.close()

def _format_clip_row(d: Dict[str, Any]) -> Dict[str, Any]:
    try:
        d["score_reasons"] = json.loads(d["score_reasons"])
    except Exception:
        d["score_reasons"] = []
    try:
        d["score_breakdown"] = json.loads(d.get("score_breakdown") or "{}")
    except Exception:
        d["score_breakdown"] = {}
    try:
        d["titles"] = json.loads(d.get("titles_json") or "[]")
    except Exception:
        d["titles"] = []
    try:
        d["hooks"] = json.loads(d.get("hooks_json") or "[]")
    except Exception:
        d["hooks"] = []
    try:
        d["overlays"] = json.loads(d.get("overlays_json") or "[]")
    except Exception:
        d["overlays"] = []
    try:
        d["transcript_edits"] = json.loads(d.get("transcript_edits_json") or "[]")
    except Exception:
        d["transcript_edits"] = []

    d["captions_enabled"] = bool(d["captions_enabled"])
    d["is_muted"] = bool(d["is_muted"])
    d["caption_highlight_words"] = bool(d.get("caption_highlight_words", 1))
    d["audio_denoise"] = bool(d.get("audio_denoise", 0))
    d["audio_normalize"] = bool(d.get("audio_normalize", 0))
    d["audio_clarity"] = bool(d.get("audio_clarity", 0))
    d["filler_removal"] = bool(d.get("filler_removal", 0))
    d["music_ducking"] = bool(d.get("music_ducking", 0))
    return d

def get_clip(clip_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
        row = cur.fetchone()
        if not row:
            return None
        return _format_clip_row(dict(row))
    finally:
        conn.close()

def list_clips_for_project(project_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clips WHERE project_id = ? ORDER BY score DESC, start_time ASC", (project_id,))
        rows = cur.fetchall()
        return [_format_clip_row(dict(r)) for r in rows]
    finally:
        conn.close()

def update_clip(clip_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn:
            allowed_fields = [
                "title", "start_time", "end_time", "duration", "aspect_ratio",
                "crop_x", "crop_y", "captions_enabled", "caption_text",
                "caption_font", "caption_size", "caption_color",
                "caption_highlight_color", "caption_position", "volume",
                "is_muted", "preview_path", "status", "error_message",
                "custom_instruction", "score_breakdown", "titles_json", "hooks_json",
                "description", "hashtags", "caption_preset", "caption_animation",
                "caption_speed", "caption_intensity", "caption_words_per_line",
                "caption_highlight_words", "reframing_mode", "audio_denoise",
                "audio_normalize", "audio_clarity", "filler_removal", "music_ducking",
                "bg_music_path", "bg_music_volume", "overlays_json", "brand_profile_id",
                "transcript_edits_json"
            ]
            fields = []
            vals = []
            for k, v in updates.items():
                if k in allowed_fields:
                    fields.append(f"{k} = ?")
                    if isinstance(v, bool):
                        vals.append(1 if v else 0)
                    elif isinstance(v, (dict, list)):
                        vals.append(json.dumps(v))
                    else:
                        vals.append(v)
            if not fields:
                return get_clip(clip_id)
            vals.append(clip_id)
            query = f"UPDATE clips SET {', '.join(fields)} WHERE id = ?"
            conn.execute(query, tuple(vals))
        return get_clip(clip_id)
    finally:
        conn.close()

def create_export(export_data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO exports (
                id, project_id, clip_id, output_filename, output_path,
                resolution, aspect_ratio, fps, file_size, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                export_data["id"], export_data["project_id"], export_data["clip_id"],
                export_data["output_filename"], export_data["output_path"],
                export_data.get("resolution", "1080p"),
                export_data.get("aspect_ratio", "9:16"),
                export_data.get("fps", 30),
                export_data.get("file_size", 0),
                export_data.get("status", "completed"),
                now
            ))
        return get_export(export_data["id"])
    finally:
        conn.close()

def get_export(export_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM exports WHERE id = ?", (export_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def list_exports() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT e.*, c.title as clip_title, p.name as project_name
        FROM exports e
        LEFT JOIN clips c ON e.clip_id = c.id
        LEFT JOIN projects p ON e.project_id = p.id
        ORDER BY e.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def delete_export(export_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM exports WHERE id = ?", (export_id,))
            return cur.rowcount > 0
    finally:
        conn.close()

def delete_clips_for_project(project_id: str):
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM clips WHERE project_id = ?", (project_id,))
    finally:
        conn.close()

DEFAULT_SETTINGS = {
    "profile": "balanced",
    "whisper_model": "base",
    "device_preference": "auto",
    "cpu_fallback": "true",
    "vad_filter": "true",
    "language": "auto",
    "default_clip_duration": "30-60",
    "default_clip_count": "5",
    "export_resolution": "1080p",
    "export_aspect_ratio": "9:16",
    "export_fps": "30",
    "export_encoder": "auto",
    "export_quality": "high",
    "export_caption_format": "burned",
    "export_dir": "",
    "theme_mode": "light",
    "shader_enabled": "true",
    "reduced_motion": "false",
    "auto_start": "false",
    "first_launch_completed": "false"
}

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM app_settings")
        saved = {row["key"]: row["value"] for row in cur.fetchall()}
        result = dict(DEFAULT_SETTINGS)
        result.update(saved)
        return result
    finally:
        conn.close()

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        if row:
            return row["value"]
        return DEFAULT_SETTINGS.get(key, default)
    finally:
        conn.close()

def set_setting(key: str, value: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (key, str(value), now))
    finally:
        conn.close()

def update_settings(settings_dict: Dict[str, Any]) -> Dict[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            for k, v in settings_dict.items():
                conn.execute("""
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """, (k, str(v), now))
        return get_all_settings()
    finally:
        conn.close()

def reset_settings() -> Dict[str, str]:
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM app_settings")
        return dict(DEFAULT_SETTINGS)
    finally:
        conn.close()

# ----------------- Built-in Caption Presets Seeder -----------------

BUILTIN_CAPTION_PRESETS = [
    {
        "id": "preset-minimal-clean",
        "name": "Minimal Clean",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 24,
        "primary_color": "#FFFFFF",
        "highlight_color": "#8273D6",
        "bg_color": "",
        "outline_color": "#181818",
        "position": "bottom",
        "animation": "Fade",
        "words_per_line": 5,
        "max_line_length": 28
    },
    {
        "id": "preset-bold-highlight",
        "name": "Bold Highlight",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 32,
        "primary_color": "#FFFFFF",
        "highlight_color": "#FACC15",
        "bg_color": "",
        "outline_color": "#000000",
        "position": "bottom",
        "animation": "Pop",
        "words_per_line": 4,
        "max_line_length": 22
    },
    {
        "id": "preset-karaoke",
        "name": "Karaoke",
        "is_builtin": 1,
        "font_name": "Nirmala UI",
        "font_size": 28,
        "primary_color": "#D1D5DB",
        "highlight_color": "#48A77A",
        "bg_color": "",
        "outline_color": "#111827",
        "position": "bottom",
        "animation": "Karaoke",
        "words_per_line": 4,
        "max_line_length": 24
    },
    {
        "id": "preset-podcast-pro",
        "name": "Podcast Pro",
        "is_builtin": 1,
        "font_name": "Plus Jakarta Sans",
        "font_size": 26,
        "primary_color": "#F0EDFC",
        "highlight_color": "#8273D6",
        "bg_color": "",
        "outline_color": "#0F172A",
        "position": "bottom",
        "animation": "Word Reveal",
        "words_per_line": 5,
        "max_line_length": 28
    },
    {
        "id": "preset-cinematic",
        "name": "Cinematic",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 22,
        "primary_color": "#F3F4F6",
        "highlight_color": "#F59E0B",
        "bg_color": "",
        "outline_color": "#1F2937",
        "position": "bottom",
        "animation": "Minimal Fade",
        "words_per_line": 6,
        "max_line_length": 34
    },
    {
        "id": "preset-pop-animation",
        "name": "Pop Animation",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 30,
        "primary_color": "#38BDF8",
        "highlight_color": "#F43F5E",
        "bg_color": "",
        "outline_color": "#0F172A",
        "position": "middle",
        "animation": "Elastic Pop",
        "words_per_line": 3,
        "max_line_length": 18
    },
    {
        "id": "preset-typewriter",
        "name": "Typewriter",
        "is_builtin": 1,
        "font_name": "JetBrains Mono",
        "font_size": 24,
        "primary_color": "#A7F3D0",
        "highlight_color": "#10B981",
        "bg_color": "#111827B0",
        "outline_color": "#064E3B",
        "position": "bottom",
        "animation": "Typewriter",
        "words_per_line": 4,
        "max_line_length": 24
    },
    {
        "id": "preset-neon-focus",
        "name": "Neon Focus",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 30,
        "primary_color": "#F472B6",
        "highlight_color": "#A855F7",
        "bg_color": "",
        "outline_color": "#581C87",
        "position": "bottom",
        "animation": "Highlight Sweep",
        "words_per_line": 4,
        "max_line_length": 22
    },
    {
        "id": "preset-boxed-captions",
        "name": "Boxed Captions",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 24,
        "primary_color": "#FFFFFF",
        "highlight_color": "#FBBF24",
        "bg_color": "#18181BE6",
        "outline_color": "#000000",
        "position": "bottom",
        "animation": "Slide Up",
        "words_per_line": 4,
        "max_line_length": 25
    },
    {
        "id": "preset-gradient-text",
        "name": "Gradient Text",
        "is_builtin": 1,
        "font_name": "Plus Jakarta Sans",
        "font_size": 28,
        "primary_color": "#C084FC",
        "highlight_color": "#818CF8",
        "bg_color": "",
        "outline_color": "#312E81",
        "position": "bottom",
        "animation": "Gradient Highlight",
        "words_per_line": 4,
        "max_line_length": 22
    },
    {
        "id": "preset-split-lines",
        "name": "Split Lines",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 24,
        "primary_color": "#FFFFFF",
        "highlight_color": "#60A5FA",
        "bg_color": "",
        "outline_color": "#1E293B",
        "position": "bottom",
        "animation": "Slide Down",
        "words_per_line": 3,
        "max_line_length": 18
    },
    {
        "id": "preset-minimal-outline",
        "name": "Minimal Outline",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 26,
        "primary_color": "#FFFFFF",
        "highlight_color": "#E2E8F0",
        "bg_color": "",
        "outline_color": "#000000",
        "position": "bottom",
        "animation": "Smooth Zoom",
        "words_per_line": 5,
        "max_line_length": 30
    },
    {
        "id": "preset-gaming-style",
        "name": "Gaming Style",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 32,
        "primary_color": "#22C55E",
        "highlight_color": "#FACC15",
        "bg_color": "",
        "outline_color": "#052E16",
        "position": "bottom",
        "animation": "Bounce",
        "words_per_line": 3,
        "max_line_length": 18
    },
    {
        "id": "preset-creator-style",
        "name": "Creator Style",
        "is_builtin": 1,
        "font_name": "Plus Jakarta Sans",
        "font_size": 28,
        "primary_color": "#FFFFFF",
        "highlight_color": "#6366F1",
        "bg_color": "#4338CA40",
        "outline_color": "#1E1B4B",
        "position": "middle",
        "animation": "Scale",
        "words_per_line": 4,
        "max_line_length": 22
    },
    {
        "id": "preset-news-style",
        "name": "News Style",
        "is_builtin": 1,
        "font_name": "Inter",
        "font_size": 22,
        "primary_color": "#FFFFFF",
        "highlight_color": "#EF4444",
        "bg_color": "#DC2626E6",
        "outline_color": "#7F1D1D",
        "position": "bottom",
        "animation": "Character Reveal",
        "words_per_line": 6,
        "max_line_length": 35
    }
]

def _seed_builtin_presets(conn: sqlite3.Connection):
    now = datetime.now(timezone.utc).isoformat()
    for p in BUILTIN_CAPTION_PRESETS:
        conn.execute("""
        INSERT OR IGNORE INTO caption_presets (
            id, name, is_builtin, font_name, font_size, primary_color,
            highlight_color, bg_color, outline_color, position, animation,
            words_per_line, max_line_length, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["id"], p["name"], p["is_builtin"], p["font_name"], p["font_size"],
            p["primary_color"], p["highlight_color"], p["bg_color"], p["outline_color"],
            p["position"], p["animation"], p["words_per_line"], p["max_line_length"], now
        ))

# ----------------- Caption Presets CRUD -----------------

def list_caption_presets() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM caption_presets ORDER BY is_builtin DESC, name ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_caption_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM caption_presets WHERE id = ?", (preset_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_caption_preset(data: Dict[str, Any]) -> Dict[str, Any]:
    import uuid
    preset_id = data.get("id") or f"custom-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO caption_presets (
                id, name, is_builtin, font_name, font_size, primary_color,
                highlight_color, bg_color, outline_color, position, animation,
                words_per_line, max_line_length, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                preset_id,
                data.get("name", "Custom Preset"),
                0,
                data.get("font_name", "Inter"),
                data.get("font_size", 24),
                data.get("primary_color", "#FFFFFF"),
                data.get("highlight_color", "#8273D6"),
                data.get("bg_color", ""),
                data.get("outline_color", "#181818"),
                data.get("position", "bottom"),
                data.get("animation", "Fade"),
                data.get("words_per_line", 4),
                data.get("max_line_length", 26),
                now
            ))
        return get_caption_preset(preset_id)
    finally:
        conn.close()

def update_caption_preset(preset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn:
            # Prevent modifying builtin flag
            clean_updates = {k: v for k, v in updates.items() if k not in ("id", "is_builtin", "created_at")}
            if not clean_updates:
                return get_caption_preset(preset_id)
            set_clause = ", ".join(f"{k} = ?" for k in clean_updates.keys())
            values = list(clean_updates.values()) + [preset_id]
            conn.execute(f"UPDATE caption_presets SET {set_clause} WHERE id = ?", values)
        return get_caption_preset(preset_id)
    finally:
        conn.close()

def delete_caption_preset(preset_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM caption_presets WHERE id = ? AND is_builtin = 0", (preset_id,))
            return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Brand Profiles CRUD -----------------

def list_brand_profiles() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM brand_profiles ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_brand_profile(brand_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM brand_profiles WHERE id = ?", (brand_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_brand_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    import uuid
    brand_id = data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO brand_profiles (
                id, name, logo_path, primary_color, secondary_color,
                caption_font, caption_preset_id, watermark_path,
                watermark_position, watermark_opacity, intro_path, outro_path,
                default_aspect_ratio, default_quality, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                brand_id,
                data.get("name", "New Brand Profile"),
                data.get("logo_path"),
                data.get("primary_color", "#8273D6"),
                data.get("secondary_color", "#F0EDFC"),
                data.get("caption_font", "Inter"),
                data.get("caption_preset_id", "preset-minimal-clean"),
                data.get("watermark_path"),
                data.get("watermark_position", "top-right"),
                float(data.get("watermark_opacity", 0.85)),
                data.get("intro_path"),
                data.get("outro_path"),
                data.get("default_aspect_ratio", "9:16"),
                data.get("default_quality", "1080p"),
                now
            ))
        return get_brand_profile(brand_id)
    finally:
        conn.close()

def update_brand_profile(brand_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn:
            clean_updates = {k: v for k, v in updates.items() if k not in ("id", "created_at")}
            if not clean_updates:
                return get_brand_profile(brand_id)
            set_clause = ", ".join(f"{k} = ?" for k in clean_updates.keys())
            values = list(clean_updates.values()) + [brand_id]
            conn.execute(f"UPDATE brand_profiles SET {set_clause} WHERE id = ?", values)
        return get_brand_profile(brand_id)
    finally:
        conn.close()

def delete_brand_profile(brand_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM brand_profiles WHERE id = ?", (brand_id,))
            return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- B-Roll Assets CRUD -----------------

def list_broll_assets(category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if category and category.lower() != "all":
            cur.execute("SELECT * FROM broll_assets WHERE LOWER(category) = LOWER(?) ORDER BY created_at DESC", (category,))
        else:
            cur.execute("SELECT * FROM broll_assets ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_broll_asset(asset_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM broll_assets WHERE id = ?", (asset_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_broll_asset(data: Dict[str, Any]) -> Dict[str, Any]:
    import uuid
    asset_id = data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO broll_assets (
                id, name, file_path, asset_type, category, tags,
                duration, width, height, thumbnail_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset_id,
                data.get("name", "Asset"),
                data.get("file_path"),
                data.get("asset_type", "video"),
                data.get("category", "General"),
                data.get("tags", ""),
                float(data.get("duration", 0.0)),
                int(data.get("width", 0)),
                int(data.get("height", 0)),
                data.get("thumbnail_path"),
                now
            ))
        return get_broll_asset(asset_id)
    finally:
        conn.close()

def delete_broll_asset(asset_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM broll_assets WHERE id = ?", (asset_id,))
            return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Voiceover CRUD -----------------

def list_voiceovers(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if project_id:
            cur.execute("SELECT * FROM voiceovers WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        else:
            cur.execute("SELECT * FROM voiceovers ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_voiceover(vo_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM voiceovers WHERE id = ?", (vo_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_voiceover(data: Dict[str, Any]) -> Dict[str, Any]:
    import uuid
    vo_id = data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO voiceovers (
                id, project_id, clip_id, text, voice, speed, pitch, volume, file_path, duration, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vo_id,
                data.get("project_id"),
                data.get("clip_id"),
                data.get("text", ""),
                data.get("voice", "Microsoft David"),
                int(data.get("speed", 0)),
                int(data.get("pitch", 0)),
                float(data.get("volume", 1.0)),
                data.get("file_path"),
                float(data.get("duration", 0.0)),
                now
            ))
        return get_voiceover(vo_id)
    finally:
        conn.close()

def delete_voiceover(vo_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM voiceovers WHERE id = ?", (vo_id,))
            return cur.rowcount > 0
    finally:
        conn.close()



