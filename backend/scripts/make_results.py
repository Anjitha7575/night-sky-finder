"""Build the data for the website's Results tab. No API calls, no cost.

Run from backend/ after the tests:
  python scripts/make_results.py

Reads (whichever exist):
  results/NightSkyUCP_results.json  -> Night Sky Finder + AI watching the video   (checked by 5 experts)
  results/NightSkyUCP_frames.json   -> AI looking at 8 photos
  results/AllSky7_results.json      -> AllSky7 clips (some also used for tuning), answers named by the AllSky7 network
Writes ../frontend/public/results.json
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
R = Path("results")
OUT = Path("../frontend/public/results.json")
PRICE_IN, PRICE_OUT = 1.25 / 1e6, 4.25 / 1e6  # muse-spark-1.3, dollars per token


def load(name):
    f = R / name
    return json.loads(f.read_text())["rows"] if f.exists() else []


def cat(answer):
    if not answer or answer.get("category") == "error":
        return None
    return answer["category"]


def group(rows, frames_rows, gid, title, who, label_key="expert"):
    frames = {Path(r["file"]).name: r for r in frames_rows}
    out, cost, n = [], 0.0, 0
    for r in rows:
        name = Path(r["file"]).name
        out.append([name, r.get(label_key), cat(r.get("ours")), cat(r.get("alone")),
                    cat(frames.get(name, {}).get("alone"))])
        t = r.get("ours_tokens") or {}
        if t:
            cost += t.get("input_tokens", 0) * PRICE_IN + t.get("output_tokens", 0) * PRICE_OUT
            n += 1
    return {"id": gid, "title": title, "who": who, "rows": out,
            "cost_per_clip": round(cost / n, 4) if n else None}


groups = []
ucp = load("NightSkyUCP_results.json")
if ucp:
    groups.append(group(ucp, load("NightSkyUCP_frames.json"), "nightskyucp",
                        "Checked by 5 experts", "NightSkyUCP dataset (AllSky7 cameras): every answer checked by 5 experts"))
as7 = load("AllSky7_results.json")
if as7:
    groups.append(group(as7, load("AllSky7_frames.json"), "allsky7",
                        "Named by the AllSky7 network", "Clips from allsky7.net, named by the network team. Some of these clips also helped us tune the code, so this is not a blind test"))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"tested": time.strftime("%d %b %Y"),
                           "model": os.getenv("META_MODEL", "muse-spark-1.3"),
                           "groups": groups}, indent=1))
print(f"wrote {OUT}: " + ", ".join(f"{g['title']} ({len(g['rows'])} clips)" for g in groups))