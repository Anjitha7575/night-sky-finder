import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.measure import measure

TYPES = {".mp4", ".avi", ".mov", ".gif", ".jpg", ".jpeg", ".png"}
out = Path("data/images")
out.mkdir(parents=True, exist_ok=True)

for f in sorted(Path("data/sample").rglob("*")):
    if f.suffix.lower() not in TYPES:
        continue
    r = measure(f)
    img = r.pop("image", None)
    r.pop("preview", None)
    if img is not None:
        cv2.imwrite(str(out / (f.stem + ".png")), img)
    print(f.name[:32])
    for k, v in r.items():
        if k != "file":
            print(f"    {k}: {v}")
