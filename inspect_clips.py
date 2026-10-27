import cv2
from pathlib import Path

for f in sorted(Path("data/sample").glob("*.mp4")):
    v = cv2.VideoCapture(str(f))
    frames = v.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = v.get(cv2.CAP_PROP_FPS)
    w = v.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = v.get(cv2.CAP_PROP_FRAME_HEIGHT)
    v.release()
    label = f.name.split("__")[0]
    print(f"{label:11} {frames:4.0f} frames  {fps:4.1f} fps  {frames/fps:4.1f} sec  {w:.0f}x{h:.0f}")