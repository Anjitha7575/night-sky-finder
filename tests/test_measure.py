import cv2
import numpy as np
import pytest

from skyfinder.measure import track, speed, straightness, blink_detect


def make_video(path, show=lambda i: True, frames=30, step=6):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (200, 100))
    for i in range(frames):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        if show(i):
            cv2.circle(frame, (10 + i * step, 50), 3, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return path


def test_moving_dot(tmp_path):
    pts = track(make_video(tmp_path / "dot.avi"))
    assert len(pts) > 20
    assert speed(pts) == pytest.approx(6, abs=0.3)
    assert straightness(pts) == pytest.approx(1.0, abs=0.02)
    assert blink_detect(pts)["blinking"] is False


def test_blinking_dot(tmp_path):
    video = make_video(tmp_path / "blink.avi", show=lambda i: i % 10 == 0)
    pts = track(video)
    assert blink_detect(pts)["blinking"] is True
    assert speed(pts) == pytest.approx(6, abs=0.3)


def test_empty_video(tmp_path):
    video = make_video(tmp_path / "empty.avi", show=lambda i: False)
    pts = track(video)
    assert pts == []
    assert speed(pts) == 0
    assert straightness(pts) is None
    assert blink_detect(pts) is None