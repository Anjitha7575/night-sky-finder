"""Small evidence tools the AI can ask for when it is not sure.

Each tool takes the clip path and the measure() result,
and returns {"text": what we found, "image": picture or None}.
"""
import cv2
import numpy as np

from skyfinder.measure import read_frames


def _box(points, w, h, pad=24, min_side=48):
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    # make small boxes at least min_side wide, so the crop is not tiny
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half_w = max(x1 - x0, min_side) / 2
    half_h = max(y1 - y0, min_side) / 2
    x0, x1 = int(max(0, cx - half_w)), int(min(w, cx + half_w))
    y0, y1 = int(max(0, cy - half_h)), int(min(h, cy + half_h))
    return x0, y0, x1, y1


def _fit(img, side=256):
    h, w = img.shape[:2]
    scale = side / max(h, w)
    interp = cv2.INTER_NEAREST if scale > 1 else cv2.INTER_AREA
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)


def zoom_in(path, result):
    points = result.get("points") or []
    if not points:
        return {"text": "No moving object to zoom in on.", "image": None}
    frames, _, _ = read_frames(path)
    h, w = frames[0].shape
    x0, y0, x1, y1 = _box(points, w, h)
    used = [frames[p["frame"]] for p in points]
    stack = np.max(np.stack(used), axis=0)[y0:y1, x0:x1]
    return {
        "text": f"Close-up of the path area ({x1 - x0}x{y1 - y0} pixels), all frames where the object was seen stacked.",
        "image": _fit(stack),
    }


def frames_over_time(path, result, count=4):
    points = result.get("points") or []
    if len(points) < 2:
        return {"text": "Object seen in too few frames to show it over time.", "image": None}
    frames, fps, _ = read_frames(path)
    h, w = frames[0].shape
    x0, y0, x1, y1 = _box(points, w, h)
    picks = [points[int(i)] for i in np.linspace(0, len(points) - 1, count)]
    tiles = []
    for p in picks:
        tile = _fit(frames[p["frame"]][y0:y1, x0:x1], 160)
        tiles.append(cv2.copyMakeBorder(tile, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=80))
    tiles = [cv2.resize(t, tiles[0].shape[::-1]) for t in tiles]
    times = ", ".join(f"{(p['frame'] - points[0]['frame']) / fps:.2f}s" if fps else f"frame {p['frame']}" for p in picks)
    return {"text": f"{count} moments from left to right, at {times} after first seen.", "image": np.hstack(tiles)}


def brightness_curve(path, result):
    points = result.get("points") or []
    if len(points) < 3:
        return {"text": "Too few points to see how brightness changes.", "image": None}
    values = np.array([p["brightness"] for p in points], dtype=float)
    peak = int(np.argmax(values))
    where = "near the start" if peak < len(values) / 3 else "near the end" if peak > 2 * len(values) / 3 else "in the middle"
    spread = (values.max() - values.min()) / max(values.max(), 1)
    shape = "almost steady" if spread < 0.15 else f"changes a lot, brightest {where}"
    # small line chart: x = time, y = brightness
    W, H = 320, 120
    chart = np.full((H, W), 20, np.uint8)
    lo, hi = values.min(), max(values.max(), values.min() + 1)
    pts = [(int(i * (W - 10) / (len(values) - 1)) + 5, int(H - 10 - (v - lo) / (hi - lo) * (H - 20)))
           for i, v in enumerate(values)]
    cv2.polylines(chart, [np.array(pts, np.int32)], False, 255, 2)
    return {
        "text": f"Brightness over {len(values)} sightings: {shape} (min {values.min():.0f}, max {values.max():.0f} of 255).",
        "image": chart,
    }


def where_in_sky(path, result):
    points = result.get("points") or []
    cam = result.get("camera") or {}
    w, h = cam.get("width"), cam.get("height")
    if not points or not w:
        return {"text": "No moving object to place in the sky.", "image": None}
    mid = points[len(points) // 2]
    # all-sky fisheye: the sky is a circle in the middle; its edge is the horizon
    cx, cy, r = w / 2, h / 2, min(w, h) / 2
    pct = round(min(np.hypot(mid["x"] - cx, mid["y"] - cy) / r, 1.5) * 100)
    if pct >= 70:
        meaning = "near the edge of the circle. On an all-sky camera that is low near the horizon, where objects look smaller and slower than they really are"
    elif pct <= 35:
        meaning = "near the centre, high in the sky, where speeds look most true"
    else:
        meaning = "between the centre and the edge"
    size = 200
    img = np.zeros((size, size), np.uint8)
    cv2.circle(img, (100, 100), 90, 90, 2)
    cv2.circle(img, (100, 100), 3, 90, -1)
    dx = (mid["x"] - cx) / r * 90
    dy = (mid["y"] - cy) / r * 90
    cv2.circle(img, (int(100 + dx), int(100 + dy)), 7, 255, -1)
    return {"text": f"The object is {pct}% of the way from the centre to the edge: {meaning}.", "image": img, "pct": pct}


def watch_video(path, result, count=8):
    frames, _, _ = read_frames(path)
    picks = [frames[int(i)] for i in np.linspace(0, len(frames) - 1, count)]
    tiles = [_fit(f, 160) for f in picks]
    tiles = [cv2.resize(t, tiles[0].shape[::-1]) for t in tiles]
    grid = np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])])
    return {"text": f"The full clip as {count} evenly spaced frames, left to right then the second row.", "image": grid}


# name -> (function, short title for the UI, description for the AI)
TOOLS = {
    "zoom_in": (zoom_in, "Zoomed in", "Close-up crop around the moving object's path."),
    "frames_over_time": (frames_over_time, "Checked frames over time", "4 close-up frames showing how the object moved and changed."),
    "brightness_curve": (brightness_curve, "Checked brightness", "How bright the object was in each frame: flare, fade, steady or blinking."),
    "where_in_sky": (where_in_sky, "Checked where in the sky", "How far the object is from the centre of the fisheye circle (edge = horizon)."),
    "watch_video": (watch_video, "Watched the full clip", "8 frames spread over the whole clip. Costs the most; use last."),
}


def run_tool(name, path, result):
    if name not in TOOLS:
        return {"text": f"Unknown tool {name}.", "image": None}
    fn = TOOLS[name][0]
    try:
        return fn(path, result)
    except Exception as e:  # a broken tool should not break the whole check
        return {"text": f"Tool failed: {e}", "image": None}
