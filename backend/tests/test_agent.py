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

class FakeItem:
    """Looks like one item in resp.output (a tool request)."""

    def __init__(self, name, why):
        self.type = "function_call"
        self.call_id = "call_1"
        self.name = name
        self.arguments = '{"why": "%s"}' % why

    def model_dump(self, exclude_none=True):
        return {"type": self.type, "call_id": self.call_id, "name": self.name, "arguments": self.arguments}


class FakeResponse:
    def __init__(self, output=(), text=""):
        self.output = list(output)
        self.output_text = text
        self.usage = type("U", (), {"input_tokens": 100, "output_tokens": 20})()


class FakeClient:
    """First reply asks for a tool, second reply gives the final JSON."""

    def __init__(self, **kwargs):
        self.replies = [
            FakeResponse(output=[FakeItem("where_in_sky", "Is it near the horizon?")]),
            FakeResponse(text='{"category": "meteor", "confidence": "high", "reason": "Short and straight.",'
                              ' "next_step": "none", "key_clue": "near the horizon"}'),
        ]
        self.seen = []
        self.responses = self

    def create(self, **kwargs):
        assert kwargs["tool_choice"] == "auto"  # the only value Meta accepts
        self.seen.append(kwargs)
        return self.replies.pop(0)


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
    assert answer["usage"] == {"calls": 2, "input_tokens": 200, "output_tokens": 40}


class GreedyClient(FakeClient):
    """Keeps asking for tools 5 times before answering."""

    def __init__(self, **kwargs):
        super().__init__()
        answer = self.replies[1]
        self.replies = [FakeResponse(output=[FakeItem("zoom_in", "more?")]) for _ in range(4)] + [answer]


def test_meta_agent_stops_after_max_steps(tmp_path, monkeypatch):
    import openai
    monkeypatch.setattr(openai, "OpenAI", GreedyClient)
    path = make_video(tmp_path / "low.avi", (150, 20), (2, 1.2))
    answer = investigate(path, measure(path), mode="meta")
    assert len(answer["steps"]) == 1 + 3  # first look + at most 3 checks
    assert answer["verdict"].category == "meteor"
    assert answer["usage"]["calls"] == 5
