"""Copy N meteors + N non-meteors from the NightSkyUCP expert-checked TEST set into data/nightskyucp_test/.

Run from backend/:  python scripts/pick_test_set.py 100
Skips the clips already in data/sample/ (so the big test uses clips we never looked at).
Same random pick every time (seed 42).
"""
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

DATA = Path("data/cr_dataset")  # your NightSkyUCP folder
OUT = Path("data/nightskyucp_test")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def key(name):
    m = re.match(r"(.+)-trim-?(\d+)-crop", name)
    return (m.group(1), int(m.group(2))) if m else None


files = {key(f.name): f for f in (DATA / "raw/samples").rglob("*.mp4")}
used = {key(f.name.split("__", 1)[-1]) for f in Path("data/sample").rglob("*.mp4")}

df = pd.read_csv(DATA / "dataset.csv", sep=";")
test = df[df["subset"] == "test"]
OUT.mkdir(parents=True, exist_ok=True)

for cls in ["meteor", "non_meteor"]:
    rows = test[test["class"] == cls].sample(frac=1, random_state=42)  # shuffled, same order every run
    copied = 0
    for sid in rows["sample_id"]:
        k = key(sid)
        src = files.get(k)
        if not src or k in used:
            continue
        shutil.copy(src, OUT / f"{cls}__{src.name}")
        copied += 1
        if copied == N:
            break
    print(f"{cls}: copied {copied}")
print("done:", OUT)
