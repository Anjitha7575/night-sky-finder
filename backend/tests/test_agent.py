import cv2
import numpy as np

from skyfinder.agent import investigate
from skyfinder.measure import measure
from skyfinder.tools import TOOLS, run_tool


def make_video(path, start, step, frames=30, size=(200, 200)):
    w, h = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (w, h))
    for i in range(frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        if 5 <= i < 20:  # seen for 15 frames = 0.6 s
            x, y = start[0] + i * step[0], start[1] + i * step[1]
            cv2.circle(frame, (int(x), int(y)), 2, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return path


def test_every_tool_returns_text(tmp_path):
    path = make_video(tmp_path / "dot.avi", (40, 100), (6, 0))
    result = measure(path)
    for name in TOOLS:
        out = run_tool(name, path, result)
        assert out["text"]
    assert run_tool("nope", path, result)["text"].startswith("Unknown tool")


def test_where_in_sky_edge_and_centre(tmp_path):
    edge = make_video(tmp_path / "edge.avi", (180, 20), (0.5, 0.3))
    centre = make_video(tmp_path / "centre.avi", (90, 95), (0.5, 0))
    assert run_tool("where_in_sky", edge, measure(edge))["pct"] >= 70
    assert run_tool("where_in_sky", centre, measure(centre))["pct"] <= 35


def test_mock_agent_clear_case_is_one_step(tmp_path):
    path = make_video(tmp_path / "fast.avi", (20, 100), (10, 0))
    answer = investigate(path, measure(path), mode="mock")
    assert [s["tool"] for s in answer["steps"]] == ["first_look"]
    assert answer["verdict"].category == "meteor"


def test_mock_agent_checks_horizon(tmp_path):
    # slow, short, straight streak near the edge: looks slow only because it is low
    path = make_video(tmp_path / "low.avi", (150, 20), (2, 1.2))
    answer = investigate(path, measure(path), mode="mock")
    assert "where_in_sky" in [s["tool"] for s in answer["steps"]]
    assert answer["verdict"].category == "meteor"
    assert answer["verdict"].key_clue == "near the horizon"


# ---- Muse Spark loop, tested with a fake API (no key, no money) ----

class FakeCall:
    def __init__(self, name, why):
        self.id = "call_1"
        self.function = type("F", (), {"name": name, "arguments": '{"why": "%s"}' % why})()


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True):
        return {"role": "assistant", "content": self.content or ""}


class FakeClient:
    """First reply asks for a tool, second reply gives the final JSON."""

    def __init__(self, **kwargs):
        self.replies = [
            FakeMessage(tool_calls=[FakeCall("where_in_sky", "Is it near the horizon?")]),
            FakeMessage(content='{"category": "meteor", "confidence": "high", "reason": "Short and straight.",'
                                ' "next_step": "none", "key_clue": "near the horizon"}'),
        ]
        self.seen = []
        self.chat = type("C", (), {"completions": self})()

    def create(self, **kwargs):
        self.seen.append(kwargs)
        msg = self.replies.pop(0)
        return type("R", (), {"choices": [type("Ch", (), {"message": msg})()]})()


def test_meta_agent_loop(tmp_path, monkeypatch):
    import openai
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    path = make_video(tmp_path / "low.avi", (150, 20), (2, 1.2))
    answer = investigate(path, measure(path), mode="meta")
    assert [s["tool"] for s in answer["steps"]] == ["first_look", "where_in_sky"]
    assert answer["steps"][1]["why"] == "Is it near the horizon?"
    assert answer["verdict"].category == "meteor"
    assert answer["verdict"].source == "meta"
    assert answer["verdict"].key_clue == "near the horizon"
