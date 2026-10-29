"""Run the AI detective on ONE clip and print every step. Costs real tokens.

Run from backend/:  python scripts/try_agent.py data/sample/goskysentinel/m20261028_090049_463.mp4
Add "mock" at the end to try without the API:  ... .mp4 mock
"""
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.agent import investigate
from skyfinder.measure import measure

load_dotenv()
path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "meta"

result = measure(path)
print("measured:", {k: result[k] for k in ("speed_pct_per_sec", "straightness", "visible_sec", "blink", "note")})

start = time.time()
answer = investigate(path, result, mode=mode)
print(f"\ntook {time.time() - start:.1f} s")

for i, step in enumerate(answer["steps"], 1):
    print(f"\nstep {i}: {step['title']}  ({step['tool']})")
    if step["tool"] != "first_look":
        print("  why:  ", step["why"])
        print("  found:", step["found"])

print("\nverdict:", json.dumps(answer["verdict"].model_dump(), indent=1))
print("usage:", answer.get("usage", "not counted (mock mode, or the call failed)"))
