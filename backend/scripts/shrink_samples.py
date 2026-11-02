"""Make the demo videos smaller (1024 px wide) so the small server opens them faster.
Our code shrinks every frame to 1024 px anyway, so the results stay the same.

Run from backend/ (needs: pip install imageio-ffmpeg):
  python scripts/shrink_samples.py
"""
import os
import subprocess
import sys
from pathlib import Path

import cv2
import imageio_ffmpeg

MAX_SIDE = 1024
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
samples = Path(os.getenv("SAMPLES_DIR", "data/sample"))

for path in sorted(samples.rglob("*.mp4")):
    video = cv2.VideoCapture(str(path))
    w, h = int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    if max(w, h) <= MAX_SIDE:
        continue
    scale = "scale=1024:-2" if w >= h else "scale=-2:1024"
    tmp = path.with_suffix(".tmp.mp4")
    done = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(path), "-vf", scale, "-an",
         "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(tmp)]
    )
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        print(f"FAILED {path}", file=sys.stderr)
        continue
    before = path.stat().st_size
    tmp.replace(path)
    print(f"shrunk {path}  {w}x{h}  {before // 1_000_000} MB -> {path.stat().st_size // 1_000_000} MB")