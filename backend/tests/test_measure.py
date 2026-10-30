import cv2
import numpy as np
import pytest

from skyfinder.measure import (
    read_frames, track, longest_track, speed, straightness, blink_detect, measure,
)


def make_video(path, show=lambda i: True, frames=30, step=6):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(frames):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        if show(i):
            cv2.circle(frame, (10 + i * step, 50), 3, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return path


def points_of(path):
    frames, _, _ = read_frames(path)
    points, _ = track(frames)
    return points


def test_moving_dot(tmp_path):
    pts = points_of(make_video(tmp_path / "dot.avi"))
    assert len(pts) > 20
    assert speed(pts) == pytest.approx(6, abs=0.3)
    assert straightness(pts) == pytest.approx(1.0, abs=0.02)
    assert blink_detect(pts)["blinking"] is False


def test_blinking_dot(tmp_path):
    pts = points_of(make_video(tmp_path / "blink.avi", show=lambda i: i % 10 == 0))
    assert blink_detect(pts)["blinking"] is True
    assert speed(pts) == pytest.approx(6, abs=0.3)


def test_empty_video(tmp_path):
    pts = points_of(make_video(tmp_path / "empty.avi", show=lambda i: False))
    assert pts == []
    assert speed(pts) == 0
    assert straightness(pts) is None
    assert blink_detect(pts) is None


def test_far_jump_starts_new_track():
    pts = [
        {"frame": 1, "x": 10, "y": 10},
        {"frame": 2, "x": 12, "y": 10},
        {"frame": 3, "x": 14, "y": 10},
        {"frame": 4, "x": 90, "y": 80},
    ]
    assert len(longest_track(pts, max_jump=5)) == 3


def test_whole_frame_flash(tmp_path):
    path = tmp_path / "flash.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(10):
        value = 200 if i == 5 else 0
        writer.write(np.full((100, 200, 3), value, dtype=np.uint8))
    writer.release()
    r = measure(path)
    assert 5 in r["flash_frames"]


def test_single_photo(tmp_path):
    path = tmp_path / "photo.png"
    cv2.imwrite(str(path), np.zeros((50, 80), dtype=np.uint8))
    r = measure(path)
    assert r["input_type"] == "image"
    assert r["speed_px_per_frame"] is None
    assert "single image" in r["note"]

def test_long_video_is_read_to_the_end(tmp_path):
    # 400 frames, object only near the end: with max_frames=300 it used to be cut off
    path = tmp_path / "long.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(400):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        if 350 <= i < 380:
            cv2.circle(frame, (10 + (i - 350) * 6, 50), 3, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    r = measure(path)
    assert r["camera"]["fps"] == 12.5  # every 2nd frame kept, so time per frame doubles
    assert r["visible_sec"] == pytest.approx(30 / 25, abs=0.2)


def test_faint_object_on_bright_sky(tmp_path):
    # grey sky (150) and an object only 30 brighter: below the normal threshold of 40
    path = tmp_path / "faint.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(30):
        frame = np.full((100, 200, 3), 150, dtype=np.uint8)
        cv2.circle(frame, (10 + i * 6, 50), 3, (180, 180, 180), -1)
        writer.write(frame)
    writer.release()
    r = measure(path)
    assert r["straightness"] == pytest.approx(1.0, abs=0.05)
    assert "lower threshold" in r["note"]


def test_sky_slowly_lights_up(tmp_path):
    # a dot moves, then the whole sky brightens step by step (each step < 40, total > 40)
    path = tmp_path / "glow.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(40):
        sky = 20 + max(0, i - 30) * 15  # frames 31..39 get brighter and brighter
        frame = np.full((100, 200, 3), min(sky, 255), dtype=np.uint8)
        if i < 30:
            cv2.circle(frame, (10 + i * 6, 50), 3, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    r = measure(path)
    assert "whole sky got brighter" in r["note"]
    assert r["flash_frames"] == []  # not a sudden one-frame flash
