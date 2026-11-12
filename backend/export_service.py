import html
from pathlib import Path
from typing import List, Dict, Any, Optional

def fmt_srt_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def fmt_vtt_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def generate_srt(segments: List[Dict[str, Any]], output_path: str) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    idx = 1
    for s in segments:
        text = s.get("text", "").strip()
        if not text:
            continue
        start_t = max(0.0, float(s.get("start", 0.0)))
        end_t = max(start_t + 0.2, float(s.get("end", 0.0)))

        lines.append(f"{idx}\n")
        lines.append(f"{fmt_srt_timestamp(start_t)} --> {fmt_srt_timestamp(end_t)}\n")
        lines.append(f"{text}\n\n")
        idx += 1

    with open(out, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return str(out.resolve())

def generate_vtt(segments: List[Dict[str, Any]], output_path: str) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = ["WEBVTT\n\n"]
    for idx, s in enumerate(segments, 1):
        text = s.get("text", "").strip()
        if not text:
            continue
        start_t = max(0.0, float(s.get("start", 0.0)))
        end_t = max(start_t + 0.2, float(s.get("end", 0.0)))

        lines.append(f"{idx}\n")
        lines.append(f"{fmt_vtt_timestamp(start_t)} --> {fmt_vtt_timestamp(end_t)}\n")
        lines.append(f"{text}\n\n")

    with open(out, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return str(out.resolve())

def generate_premiere_xml(
    project_name: str,
    clip_title: str,
    source_file_path: str,
    start_time: float,
    end_time: float,
    fps: float,
    width: int,
    height: int,
    output_xml_path: str
) -> str:
    """
    Generates standard Apple FCP7 / Premiere Pro XML format compatible with
    Adobe Premiere Pro, DaVinci Resolve, and Final Cut Pro.
    """
    out = Path(output_xml_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fps_int = int(round(fps)) if fps > 0 else 30
    duration_frames = int(round((end_time - start_time) * fps_int))
    in_frames = int(round(start_time * fps_int))
    out_frames = int(round(end_time * fps_int))

    safe_title = html.escape(clip_title)
    safe_proj = html.escape(project_name)
    src_path_obj = Path(source_file_path)
    safe_src_name = html.escape(src_path_obj.name)
    safe_src_url = "file://localhost/" + str(src_path_obj.resolve()).replace("\\", "/")

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>{safe_proj} - {safe_title}</name>
    <duration>{duration_frames}</duration>
    <rate>
      <timebase>{fps_int}</timebase>
      <ntsc>FALSE</ntsc>
    </rate>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <width>{width}</width>
            <height>{height}</height>
            <rate>
              <timebase>{fps_int}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
          </samplecharacteristics>
        </format>
        <track>
          <clipitem id="clipitem-1">
            <name>{safe_src_name}</name>
            <duration>{out_frames}</duration>
            <rate>
              <timebase>{fps_int}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>0</start>
            <end>{duration_frames}</end>
            <in>{in_frames}</in>
            <out>{out_frames}</out>
            <file id="file-1">
              <name>{safe_src_name}</name>
              <pathurl>{safe_src_url}</pathurl>
              <rate>
                <timebase>{fps_int}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <duration>{out_frames}</duration>
              <media>
                <video>
                  <samplecharacteristics>
                    <width>{width}</width>
                    <height>{height}</height>
                  </samplecharacteristics>
                </video>
              </media>
            </file>
          </clipitem>
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml_content.strip())

    return str(out.resolve())

