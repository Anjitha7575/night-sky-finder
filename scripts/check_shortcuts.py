import re
from pathlib import Path
import cv2
import pandas as pd

DATA = Path("PATH_TO/cr_dataset")

def key(name):
    m = re.match(r"(.+)-trim-?(\d+)-crop", name)
    return (m.group(1), int(m.group(2)))

files = {key(f.name): f for f in (DATA / "raw/samples").rglob("*.mp4")}

df = pd.read_csv(DATA / "dataset.csv", sep=";")
test = df[df["subset"] == "test"].copy()

def info(sid):
    f = files.get(key(sid))
    if f is None:
        return pd.Series([None, None])
    v = cv2.VideoCapture(str(f))
    frames = v.get(cv2.CAP_PROP_FRAME_COUNT)
    width = v.get(cv2.CAP_PROP_FRAME_WIDTH)
    v.release()
    return pd.Series([frames, width])

test[["frames", "width"]] = test["sample_id"].apply(info)
test = test.dropna(subset=["frames"])

print("Clips checked:", len(test))
print("\nFrames per class:")
print(test.groupby("class")["frames"].describe()[["min", "50%", "max"]])
print("\nWidth per class:")
print(test.groupby("class")["width"].value_counts().unstack(fill_value=0))

best = 0
for t in range(5, 150):
    guess = (test["frames"] < t).map({True: "meteor", False: "non_meteor"})
    acc = (guess == test["class"]).mean()
    if acc > best:
        best, best_t = acc, t
print(f"\nCheat rule 'frames < {best_t} = meteor' is right {best:.0%} of the time")