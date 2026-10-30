"""Save our measurements for every sample clip, so you can check a code change didn't alter them.

Run from backend/:
  python scripts/measure_snapshot.py before.json   # with the old code
  ...update the code...
  python scripts/measure_snapshot.py after.json    # with the new code
  python scripts/measure_snapshot.py --compare before.json after.json
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.measure import measure

KEYS = ("speed_pct_per_sec", "straightness", "visible_sec", "blink", "note")

if sys.argv[1] == "--compare":
    a, b = (json.loads(Path(f).read_text()) for f in sys.argv[2:4])
    changed = [k for k in a if a[k] != b.get(k)]
    print(f"{len(a)} clips, {len(changed)} changed")
    for k in changed:
        print(f"\n{k}\n  before: {a[k]}\n  after:  {b.get(k)}")
else:
    samples = Path(os.getenv("SAMPLES_DIR", "data/sample"))
    out = {}
    for p in sorted(samples.rglob("*")):
        if p.suffix.lower() in {".mp4", ".mov", ".avi", ".gif", ".png", ".jpg"}:
            r = measure(p)
            out[str(p.relative_to(samples))] = {k: r.get(k) for k in KEYS}
            print(".", end="", flush=True)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
    print(f"\nsaved {len(out)} clips to {sys.argv[1]}")
