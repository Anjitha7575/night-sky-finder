import base64
import os
import tempfile
from pathlib import Path

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from skyfinder.classify import classify
from skyfinder.measure import measure

load_dotenv()

SAMPLES = Path(os.getenv("SAMPLES_DIR", "data/sample"))
ALLOWED = {".mp4", ".avi", ".mov", ".gif", ".jpg", ".jpeg", ".png", ".webp"}
MAX_MB = 50

app = FastAPI(title="Night Sky Finder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def analyze(path, name):
    result = measure(path)
    verdict = classify(result)
    image = result.pop("image", None)
    image_b64 = None
    if image is not None:
        ok, png = cv2.imencode(".png", image)
        image_b64 = base64.b64encode(png.tobytes()).decode()
    result["file"] = name
    return {
        "file": name,
        "measured": result,
        "verdict": verdict.model_dump(),
        "image_png_base64": image_b64,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_mode": os.getenv("AI_MODE", "mock")}


@app.get("/api/samples")
def list_samples():
    if not SAMPLES.exists():
        return []
    files = [f for f in sorted(SAMPLES.rglob("*")) if f.suffix.lower() in ALLOWED]
    return [str(f.relative_to(SAMPLES)) for f in files]


@app.post("/api/samples/analyze")
def analyze_sample(name: str):
    path = (SAMPLES / name).resolve()
    if SAMPLES.resolve() not in path.parents or not path.is_file():
        raise HTTPException(404, "sample not found")
    return analyze(path, name)


@app.post("/api/analyze")
async def analyze_upload(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"file type {ext or 'unknown'} not supported")
    data = await file.read()
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"file is larger than {MAX_MB} MB")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{ext}"
        path.write_bytes(data)
        return analyze(path, file.filename)