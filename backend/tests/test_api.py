import cv2
import numpy as np
from fastapi.testclient import TestClient

from skyfinder import api

client = TestClient(api.app)


def make_video(path):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(30):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        cv2.circle(frame, (10 + i * 6, 50), 3, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return path


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_analyze_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_MODE", "mock")
    video = make_video(tmp_path / "dot.avi")
    with open(video, "rb") as f:
        r = client.post("/api/analyze", files={"file": ("dot.avi", f, "video/x-msvideo")})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["category"] == "meteor"
    assert body["verdict"]["source"] == "mock"
    assert body["measured"]["camera"]["fps"] == 25.0
    assert body["image_png_base64"]
    assert body["preview_png_base64"]


def test_rejects_wrong_type():
    r = client.post("/api/analyze", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_samples_cannot_escape_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "SAMPLES", tmp_path)
    r = client.post("/api/samples/analyze", params={"name": "../../etc/passwd"})
    assert r.status_code == 404


def test_list_and_analyze_sample(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_MODE", "mock")
    monkeypatch.setattr(api, "SAMPLES", tmp_path)
    make_video(tmp_path / "dot.avi")
    assert client.get("/api/samples").json() == ["dot.avi"]
    r = client.post("/api/samples/analyze", params={"name": "dot.avi"})
    assert r.status_code == 200 and r.json()["file"] == "dot.avi"


def test_sample_file_download(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "SAMPLES", tmp_path)
    make_video(tmp_path / "dot.avi")
    r = client.get("/api/samples/file", params={"name": "dot.avi"})
    assert r.status_code == 200 and len(r.content) > 0
    assert client.get("/api/samples/file", params={"name": "../secret"}).status_code == 404


def test_measure_then_classify(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_MODE", "mock")
    monkeypatch.setattr(api, "SAMPLES", tmp_path)
    make_video(tmp_path / "dot.avi")
    m = client.post("/api/samples/measure", params={"name": "dot.avi"})
    assert m.status_code == 200
    assert m.json()["measured"]["camera"]["fps"] == 25.0
    assert m.json()["image_png_base64"]
    c = client.post("/api/samples/classify", params={"name": "dot.avi"})
    assert c.status_code == 200 and c.json()["verdict"]["category"] == "meteor"


def test_investigate_sample(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_MODE", "mock")
    monkeypatch.setattr(api, "SAMPLES", tmp_path)
    make_video(tmp_path / "dot2.avi")
    r = client.post("/api/samples/investigate", params={"name": "dot2.avi"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["category"] == "meteor"
    assert body["steps"][0]["tool"] == "first_look"
    assert body["steps"][0]["image_png_base64"]
