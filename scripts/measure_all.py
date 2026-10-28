import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.measure import track, speed, straightness, blink_detect

for f in sorted(Path("data/sample").glob("*.mp4")):
    pts = track(f, gap=1)
    print(f"{f.name[:30]}  speed: {speed(pts):4}  straight: {straightness(pts)}  blink: {blink_detect(pts)}")