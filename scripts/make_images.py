import sys
from pathlib import Path
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.measure import combined_image

out = Path("data/images")
out.mkdir(parents=True, exist_ok=True)

for f in sorted(Path("data/sample").glob("*.mp4")):
    img = combined_image(f)
    if img is not None:
        cv2.imwrite(str(out / (f.stem + ".png")), img)
        print("saved", f.stem[:40])