import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.classify import classify
from skyfinder.evaluate import score
from skyfinder.measure import measure

load_dotenv()
mode = os.getenv("AI_MODE", "mock")
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
files = sorted(Path("data/test_set").glob("*.mp4"))[:limit]
out = Path("results") / f"eval_{mode}_{time.strftime('%Y%m%d_%H%M')}.json"
out.parent.mkdir(exist_ok=True)

rows = []
for i, f in enumerate(files, 1):
    label = f.name.split("__")[0]
    m = measure(f)
    v = classify(m)
    m.pop("image", None)
    m.pop("preview", None)
    rows.append({"file": f.name, "label": label, **v.model_dump(), "measured": m})
    mark = "ok " if (v.category == "meteor") == (label == "meteor") else "XX "
    print(f"{i:3}/{len(files)} {mark} {label:10} -> {v.category:9} {v.confidence}")

summary = score(rows)
out.write_text(json.dumps({"mode": mode, "summary": summary, "rows": rows}, indent=2))
print(json.dumps(summary, indent=2))
print("saved", out)
