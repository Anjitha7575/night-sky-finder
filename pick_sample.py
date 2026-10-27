import re
import shutil
from pathlib import Path
import pandas as pd

DATA = Path("/Users/anjitha/Downloads/16451625/cr_dataset")
OUT = Path("data/sample")
OUT.mkdir(parents=True, exist_ok=True)

def key(name):
    m = re.match(r"(.+)-trim-?(\d+)-crop", name)
    return (m.group(1), int(m.group(2)))

files = {}
for f in (DATA / "raw/samples").rglob("*.mp4"):
    files[key(f.name)] = f

df = pd.read_csv(DATA / "dataset.csv", sep=";")
test = df[df["subset"] == "test"]

for cls in ["meteor", "non_meteor"]:
    rows = test[test["class"] == cls].head(5)
    for sid in rows["sample_id"]:
        src = files.get(key(sid))
        if src:
            shutil.copy(src, OUT / f"{cls}__{src.name}")
            print("copied", cls, src.name)
        else:
            print("NOT FOUND", sid)