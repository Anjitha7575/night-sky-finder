import base64
import os
import tempfile
from pathlib import Path

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from skyfinder.agent import investigate
from skyfinder.classify import classify
from skyfinder.measure import measure

load_dotenv()

SAMPLES = Path(os.getenv("SAMPLES_DIR", "data/sample"))
ALLOWED = {".mp4", ".avi", ".mov", ".gif", ".jpg", ".jpeg", ".png", ".webp"}
MAX_MB = 50

app = FastAPI(title="Night Sky Finder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_b64(image):
    if image is None:
        return None
    ok, png = cv2.imencode(".png", image)
    return base64.b64encode(png.tobytes()).decode() if ok else None


_measured = {}


def measured_payload(result, name):
    out = {k: v for k, v in result.items() if k not in ("image", "preview", "points")}
    out["file"] = name
    return {
        "file": name,
        "measured": out,
        "image_png_base64": to_b64(result.get("image")),
        "preview_png_base64": to_b64(result.get("preview")),
    }


def analyze(path, name):
    result = measure(path)
    answer = investigate(path, result)
    result.pop("points", None)
    image_b64 = to_b64(result.pop("image", None))
    preview_b64 = to_b64(result.pop("preview", None))
    result["file"] = name
    return {
        "file": name,
        "measured": result,
        "verdict": answer["verdict"].model_dump(),
        "steps": answer["steps"],
        "image_png_base64": image_b64,
        "preview_png_base64": preview_b64,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_mode": os.getenv("AI_MODE", "mock")}


FIRST = "first_look"  # hand-picked clips, shown first, in the order of first_look/order.txt


@app.get("/api/samples")
def list_samples():
    if not SAMPLES.exists():
        return []
    files = [str(f.relative_to(SAMPLES)) for f in sorted(SAMPLES.rglob("*")) if f.suffix.lower() in ALLOWED]
    first = [f for f in files if f.startswith(FIRST + "/")]
    order_file = SAMPLES / FIRST / "order.txt"
    if order_file.exists():
        wanted = [line.strip() for line in order_file.read_text().splitlines() if line.strip()]
        rank = {name: i for i, name in enumerate(wanted)}
        # listed clips in order.txt order; any not listed go after them
        first.sort(key=lambda f: rank.get(f.split("/", 1)[1], len(wanted)))
    return first + [f for f in files if not f.startswith(FIRST + "/")]


def sample_path(name):
    path = (SAMPLES / name).resolve()
    if SAMPLES.resolve() not in path.parents or not path.is_file():
        raise HTTPException(404, "sample not found")
    return path


@app.post("/api/samples/analyze")
def analyze_sample(name: str):
    return analyze(sample_path(name), name)


@app.post("/api/samples/measure")
def measure_sample(name: str):
    result = measure(sample_path(name))
    _measured[name] = result
    return measured_payload(result, name)


@app.post("/api/samples/classify")
def classify_sample(name: str):
    result = _measured.get(name)
    if result is None:
        result = measure(sample_path(name))
        _measured[name] = result
    return {"file": name, "verdict": classify(result).model_dump()}


@app.post("/api/samples/investigate")
def investigate_sample(name: str):
    path = sample_path(name)
    result = _measured.get(name)
    if result is None:
        result = measure(path)
        _measured[name] = result
    answer = investigate(path, result)  # always a fresh AI check; the browser keeps answers until refresh
    return {
        "file": name,
        "verdict": answer["verdict"].model_dump(),
        "steps": answer["steps"],
        "usage": answer.get("usage"),
    }


@app.get("/api/samples/file")
def sample_file(name: str):
    return FileResponse(sample_path(name))


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
