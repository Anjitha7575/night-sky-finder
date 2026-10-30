"""Build the data for the website's Results tab from your comparison runs.

Run from backend/ (after compare_ai_alone.py):
  python scripts/make_results.py

It takes the newest FULL run of each kind from results/:
  compare_video_*.json   -> "AI watching the video" + Night Sky Finder answers
  compare_frames_*.json  -> "AI looking at 8 photos"
and writes ../frontend/public/results.json. No API calls, no cost.
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
RESULTS = Path("results")
OUT = Path("../frontend/public/results.json")


def best_run(kind):
    """Newest file of this kind among the ones with the most clips (skips 1-clip trials)."""
    runs = []
    for f in RESULTS.glob(f"compare_{kind}_*.json"):
        rows = json.loads(f.read_text())["rows"]
        runs.append((len(rows), f.name, f, rows))
    if not runs:
        raise SystemExit(f"No results/compare_{kind}_*.json found. Run compare_ai_alone.py first.")
    count, name, f, rows = max(runs)
    print(f"{kind}: using {name} ({count} clips)")
    return f, rows


def category(answer):
    if not answer or answer.get("category") == "error":
        return None
    return answer["category"]


video_file, video_rows = best_run("video")
frames_file, frames_rows = best_run("frames")
by_name = lambda rows: {Path(r["file"]).name: r for r in rows}
frames = by_name(frames_rows)

rows = []
for r in video_rows:
    name = Path(r["file"]).name
    f = frames.get(name, {})
    ours = r.get("ours") or f.get("ours")
    rows.append([name, r.get("expert"), category(r.get("alone")), category(f.get("alone")), category(ours)])

stamp = video_file.stem.split("_", 2)[2]  # e.g. 20261029_222700
tested = time.strftime("%d %b %Y", time.strptime(stamp, "%Y%m%d_%H%M%S"))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"tested": tested, "model": os.getenv("META_MODEL", "muse-spark-1.3"), "rows": rows}, indent=1))
print(f"wrote {OUT} with {len(rows)} clips")
