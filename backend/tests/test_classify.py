import numpy as np

from skyfinder.classify import Verdict, build_input, classify, describe, parse_reply


def fake_result(**extra):
    r = {
        "input_type": "video",
        "camera": {"width": 96, "height": 54, "fps": 25.0, "frames": 20},
        "speed_pct_per_sec": 120.0,
        "straightness": 1.0,
        "blink": {"seen_ratio": 1.0, "blinking": False},
        "visible_sec": 0.4,
        "flash_frames": [],
        "note": None,
        "image": np.zeros((54, 96), dtype=np.uint8),
    }
    r.update(extra)
    return r


def test_mock_meteor():
    assert classify(fake_result(), mode="mock").category == "meteor"


def test_mock_plane():
    r = fake_result(speed_pct_per_sec=6.0, visible_sec=4.4, blink={"seen_ratio": 0.1, "blinking": True})
    assert classify(r, mode="mock").category == "plane"


def test_mock_flash():
    assert classify(fake_result(flash_frames=[10]), mode="mock").category == "flash"


def test_unreadable_file():
    v = classify({"input_type": "video", "error": "could not read file"}, mode="mock")
    assert v.category == "unsure" and v.next_step == "ask_human"


def test_parse_good_reply():
    text = 'Sure: {"category": "plane", "confidence": "high", "reason": "Blinks.", "next_step": "none"}'
    v = parse_reply(text, "meta")
    assert v == Verdict(category="plane", confidence="high", reason="Blinks.", next_step="none", source="meta")


def test_parse_bad_reply_is_safe():
    v = parse_reply('{"category": "ufo"}', "meta")
    assert v.category == "unsure" and v.confidence == "low"


def test_prompt_has_image_and_numbers():
    items = build_input(fake_result())
    parts = items[0]["content"]
    assert parts[1]["image_url"].startswith("data:image/png;base64,")
    assert "120.0 %" in parts[0]["text"]


def test_photo_prompt_has_no_speed():
    text = describe(fake_result(input_type="image", note="single image: movement unknown"))
    assert "speed" not in text and "single image" in text

def test_faint_note_explains_gaps():
    text = describe(fake_result(note="faint object against a bright sky: found with a lower threshold"))
    assert "not from blinking" in text
