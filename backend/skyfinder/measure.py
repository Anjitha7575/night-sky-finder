from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageSequence

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_frames(path, max_frames=300, max_side=1024):
    path = Path(path)
    ext = path.suffix.lower()
    frames = []
    fps = None

    if ext in IMAGE_TYPES:
        input_type = "image"
        img = cv2.imread(str(path))
        if img is not None:
            frames = [cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)]
    elif ext == ".gif":
        input_type = "gif"
        with Image.open(path) as gif:
            ms = gif.info.get("duration") or 100
            fps = 1000 / ms
            for i, page in enumerate(ImageSequence.Iterator(gif)):
                if i >= max_frames:
                    break
                frames.append(np.array(page.convert("L")))
    else:
        input_type = "video"
        video = cv2.VideoCapture(str(path))
        fps = video.get(cv2.CAP_PROP_FPS) or None
        while len(frames) < max_frames:
            ok, frame = video.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        video.release()

    if frames:
        h, w = frames[0].shape
        shrink = max_side / max(h, w)
        if shrink < 1:
            frames = [cv2.resize(f, None, fx=shrink, fy=shrink, interpolation=cv2.INTER_AREA) for f in frames]

    return frames, fps, input_type


def track(frames, threshold=40, gap=1, flash_share=0.2, min_area=3, edge=0.03):
    points = []
    flash_frames = []
    if not frames:
        return points, flash_frames
    h, w = frames[0].shape
    mask = np.zeros((h, w), dtype=np.uint8)
    eh, ew = int(h * edge), int(w * edge)
    mask[eh:h - eh, ew:w - ew] = 1

    for i in range(gap, len(frames)):
        brighter = cv2.subtract(frames[i], frames[i - gap])
        changed = (brighter > threshold).astype(np.uint8) * mask
        if changed.mean() > flash_share:
            flash_frames.append(i)
            continue
        n, labels, stats, _ = cv2.connectedComponentsWithStats(changed)
        if n < 2:
            continue
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        if stats[biggest, cv2.CC_STAT_AREA] < min_area:
            continue
        ys, xs = np.where(labels == biggest)
        points.append({
            "frame": i,
            "x": float(round(xs.mean(), 1)),
            "y": float(round(ys.mean(), 1)),
            "brightness": float(round(frames[i][ys, xs].mean(), 1)),
        })
    return points, flash_frames


def longest_track(points, max_jump):
    tracks = []
    for p in points:
        if tracks:
            last = tracks[-1][-1]
            jump = np.hypot(p["x"] - last["x"], p["y"] - last["y"])
            if jump <= max_jump * (p["frame"] - last["frame"]):
                tracks[-1].append(p)
                continue
        tracks.append([p])
    return max(tracks, key=len) if tracks else []


def speed(points):
    if len(points) < 2:
        return 0
    total = 0
    for a, b in zip(points, points[1:]):
        total += np.hypot(b["x"] - a["x"], b["y"] - a["y"])
    frames = points[-1]["frame"] - points[0]["frame"]
    return float(round(total / frames, 2))


def straightness(points):
    if len(points) < 3:
        return None
    walked = 0
    for a, b in zip(points, points[1:]):
        walked += np.hypot(b["x"] - a["x"], b["y"] - a["y"])
    if walked == 0:
        return None
    first, last = points[0], points[-1]
    direct = np.hypot(last["x"] - first["x"], last["y"] - first["y"])
    return float(round(direct / walked, 2))


def blink_detect(points):
    if len(points) < 2:
        return None
    span = points[-1]["frame"] - points[0]["frame"] + 1
    seen_ratio = round(len(points) / span, 2)
    return {"seen_ratio": seen_ratio, "blinking": seen_ratio < 0.5}


def combined_image(frames, skip=(), out_side=512):
    if not frames:
        return None
    if len(frames) == 1:
        stack = frames[0]
    else:
        keep = [f for i, f in enumerate(frames) if i not in skip]
        background = np.median(np.stack(keep), axis=0).astype(np.uint8)
        stack = np.zeros_like(background)
        for f in keep:
            stack = np.maximum(stack, cv2.subtract(f, background))
    if len(frames) > 1:
        floor = np.percentile(stack, 99)
        stack = cv2.subtract(stack, np.full_like(stack, int(floor)))
    top = stack.max()
    if top > 0:
        stack = (stack.astype(np.float32) * (255.0 / top)).astype(np.uint8)
    h, w = stack.shape
    scale = out_side / max(h, w)
    if scale < 1:
        size = int(round(1 / scale)) | 1
        stack = cv2.dilate(stack, np.ones((size, size), np.uint8))
        return cv2.resize(stack, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return cv2.resize(stack, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)


def measure(path):
    frames, fps, input_type = read_frames(path)
    if not frames:
        return {"input_type": input_type, "error": "could not read file"}

    h, w = frames[0].shape
    camera = {"width": w, "height": h, "fps": round(fps, 1) if fps else None, "frames": len(frames)}
    result = {"file": Path(path).name, "input_type": input_type, "camera": camera}

    if len(frames) == 1:
        result.update({
            "speed_px_per_frame": None,
            "speed_pct_per_sec": None,
            "straightness": None,
            "blink": None,
            "visible_sec": None,
            "flash_frames": [],
            "note": "single image: movement unknown",
            "image": combined_image(frames),
        })
        return result

    diag = (w ** 2 + h ** 2) ** 0.5
    raw_points, flash_frames = track(frames)
    points = longest_track(raw_points, max_jump=0.15 * diag)
    px = speed(points)
    pct = round(px * fps / diag * 100, 1) if fps and px else None
    visible = None
    if points and fps:
        visible = round((points[-1]["frame"] - points[0]["frame"] + 1) / fps, 2)

    notes = []
    if not points:
        notes.append("no moving object found")
    elif len(points) < 3:
        notes.append("object seen in fewer than 3 frames: numbers are not reliable")
    if flash_frames:
        notes.append(f"whole-sky flash in {len(flash_frames)} frame(s)")

    result.update({
        "speed_px_per_frame": px,
        "speed_pct_per_sec": pct,
        "straightness": straightness(points),
        "blink": blink_detect(points),
        "visible_sec": visible,
        "flash_frames": flash_frames,
        "note": "; ".join(notes) or None,
        "image": combined_image(frames, skip=set(flash_frames)),
    })
    return result