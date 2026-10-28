import cv2
import numpy as np
from pathlib import Path


def track(path, threshold=40, gap=1):
    video = cv2.VideoCapture(str(path))
    history = []
    frame_no = 0
    points = []

    while True:
        ok, frame = video.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        history.append(gray)

        if len(history) > gap:
            old = history[-gap - 1]
            brighter = cv2.subtract(gray, old)
            ys, xs = np.where(brighter > threshold)
            if len(xs) > 0:
                points.append({
                    "frame": frame_no,
                    "x": float(round(xs.mean(), 1)),
                    "y": float(round(ys.mean(), 1)),
                    "brightness": float(round(gray[ys, xs].mean(), 1)),
                })

        if len(history) > gap + 1:
            history.pop(0)

        frame_no += 1

    video.release()
    return points


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

def combined_image(path, scale=4):
    video = cv2.VideoCapture(str(path))
    first = None
    stack = None
    while True:
        ok, frame = video.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if first is None:
            first = gray
            stack = np.zeros_like(gray)
            continue
        diff = cv2.subtract(gray, first)
        stack = np.maximum(stack, diff)
    video.release()
    if stack is None:
        return None
    stack = cv2.normalize(stack, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.resize(stack, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    