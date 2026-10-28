import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.classify import classify
from skyfinder.measure import measure

load_dotenv()
TYPES = {".mp4", ".avi", ".mov", ".gif", ".jpg", ".jpeg", ".png"}

for f in sorted(Path("data/sample").rglob("*")):
    if f.suffix.lower() not in TYPES:
        continue
    v = classify(measure(f))
    print(f"{f.name[:32]:32}  {v.category:9} {v.confidence:6} [{v.source}]  {v.reason}")