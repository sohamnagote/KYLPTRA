import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ffmpeg_service import probe_video, extract_audio, render_clip
from backend.config import FFMPEG_EXE

def test_probe_and_render_clip(tmp_path):
    synth_video = tmp_path / "test_synth.mp4"
    # Generate 3-second test video dynamically in tmp_path
    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(synth_video)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert synth_video.exists()
    
    # 1. Test probe_video
    meta = probe_video(str(synth_video))
    assert meta["width"] == 1920
    assert meta["height"] == 1080
    assert meta["duration"] >= 2.9
    assert meta["has_audio"] is True
    
    # 2. Test extract_audio
    audio_out = tmp_path / "audio.wav"
    extracted = extract_audio(str(synth_video), str(audio_out))
    assert Path(extracted).exists()
    assert Path(extracted).stat().st_size > 1000
    
    # 3. Test render_clip (9:16 vertical 720p output)
    clip_out = tmp_path / "rendered_9_16.mp4"
    rendered = render_clip(
        source_path=str(synth_video),
        output_path=str(clip_out),
        start_time=0.5,
        duration=2.0,
        aspect_ratio="9:16",
        crop_x=0.5,
        resolution="720p",
        fps=30,
        volume=1.0,
        use_gpu=True
    )
    
    assert Path(rendered["output_path"]).exists()
    assert rendered["width"] == 720
    assert rendered["height"] == 1280
    assert rendered["duration"] >= 1.8
