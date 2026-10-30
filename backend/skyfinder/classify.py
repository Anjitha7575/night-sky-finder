import base64
import json
import os
from typing import Literal

import cv2
from pydantic import BaseModel, ValidationError

Category = Literal[
    "meteor", "satellite", "plane", "bird", "insect",
    "cloud", "flash", "not_sky", "unsure",
]


class Verdict(BaseModel):
    category: Category
    confidence: Literal["high", "medium", "low"]
    reason: str
    next_step: Literal["none", "watch_video", "ask_human"]
    key_clue: str = ""  # the one clue that decided it (filled by the agent)
    source: Literal["mock", "meta"] = "mock"


GUIDE = """You check clips from fixed night-sky cameras and say what moving object was seen.

What you get:
- One combined image: all frames stacked, still background removed, so a moving object shows as its whole path.
- Measurements made by code from the video (when it is a video or GIF), and a short camera description.

How objects usually look (compare speeds only within the same camera):
- meteor: fast, straight, usually seen for about a second or less, often brightens then fades. A fast meteor can look like a row of evenly spaced dots, because it jumps more than its own size between frames; it is still seen in almost every frame.
- fireball (answer "meteor"): a very bright meteor. It can last several seconds (2 to 10 s), often has a glowing head with a tail, flares or breaks into pieces, and can light up the sky. Do not rule out a meteor just because it lasts a few seconds if it is very bright and flares.
- plane: slow, straight, seen for several seconds, lights blink, so the path is a dotted line with gaps in time (low seen ratio).
- satellite: slow, straight, steady brightness, seen in almost every frame, no blinking, no tail. Usually crosses for much longer than a fireball. A satellite flare is a smooth brightening and fading of a small point, with no tail.
- bird or insect: curved or wavy path, often blurry, can be near the camera and look big.
- cloud: large soft patches, no clear point or line, changes slowly.
- flash: most of the sky lights up at once for a very short time (lightning, very bright fireball flash, or camera glitch).
- not_sky: the picture is not from a night-sky camera.

Rules:
- Use the image and the numbers together. If they disagree, say so in the reason.
- A fisheye all-sky lens bends straight paths near the edge of the circle.
- Numbers can be unreliable when the note says so; then rely more on the image.
- If unsure, use category "unsure" or a low confidence. Do not guess with high confidence.
- next_step: "none" if confident, "watch_video" if the full video would help, "ask_human" if even that would not help.
- Write the reason in 1 or 2 short, plain sentences.

Reply with JSON only, exactly these keys:
{"category": one of meteor|satellite|plane|bird|insect|cloud|flash|not_sky|unsure,
 "confidence": high|medium|low,
 "reason": "...",
 "next_step": none|watch_video|ask_human}"""


def describe(result):
    cam = result.get("camera", {})
    lines = [
        f"input type: {result.get('input_type')}",
        f"camera: {cam.get('width')}x{cam.get('height')} pixels, "
        f"{cam.get('fps') or 'unknown'} fps, {cam.get('frames')} frames",
    ]
    if result.get("lens"):
        lines.append(f"lens: {result['lens']}")
    if result.get("input_type") != "image":
        blink = result.get("blink") or {}
        lines += [
            f"speed: {result.get('speed_pct_per_sec')} % of the image diagonal per second",
            f"straightness: {result.get('straightness')} (1.0 = perfectly straight)",
            f"seen ratio: {blink.get('seen_ratio')} (1.0 = seen in every frame between first and last sighting)",
            f"visible for: {result.get('visible_sec')} seconds",
        ]
    if result.get("note"):
        lines.append(f"note: {result['note']}")
        if "faint object" in result["note"]:
            lines.append("so: gaps in the path (a low seen ratio) come from our measuring on a bright sky, "
                         "not from blinking lights")
    return "\n".join(lines)


def build_input(result):
    """The first message for Meta's /v1/responses API: text + the combined image.
    The GUIDE goes separately, as "instructions"."""
    ok, png = cv2.imencode(".png", result["image"])
    image_url = "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()
    text = "Attached: one combined image.\nMeasurements:\n" + describe(result)
    return [
        {"role": "user", "content": [
            {"type": "input_text", "text": text},
            {"type": "input_image", "image_url": image_url},
        ]},
    ]


def parse_reply(text, source):
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start:end + 1])
        data["source"] = source
        return Verdict.model_validate(data)
    except (ValueError, ValidationError):
        return Verdict(
            category="unsure", confidence="low",
            reason="The AI reply could not be read.",
            next_step="ask_human", source=source,
        )


def mock_classify(result):
    if result.get("flash_frames"):
        return Verdict(category="flash", confidence="medium",
                       reason="Most of the image lit up at once.", next_step="none")
    if result.get("input_type") == "image":
        return Verdict(category="unsure", confidence="low",
                       reason="Single photo: movement cannot be measured.", next_step="ask_human")
    blink = result.get("blink")
    if not blink:
        return Verdict(category="cloud", confidence="low",
                       reason="No clear moving object; something changes slowly.", next_step="watch_video")
    pct = result.get("speed_pct_per_sec") or 0
    straight = result.get("straightness") or 0
    if blink["blinking"]:
        return Verdict(category="plane", confidence="medium",
                       reason="Slow, straight and blinking.", next_step="none")
    if straight >= 0.95 and (result.get("visible_sec") or 99) <= 1.5 and pct >= 30:
        return Verdict(category="meteor", confidence="medium",
                       reason="Fast, straight and brief.", next_step="none")
    if straight >= 0.95:
        return Verdict(category="satellite", confidence="low",
                       reason="Straight and steady but not fast.", next_step="watch_video")
    return Verdict(category="unsure", confidence="low",
                   reason="Path is not straight; could be a bird or insect.", next_step="watch_video")


def meta_classify(result, model=None, effort=None):
    from openai import OpenAI

    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.getenv("META_API_KEY"))
    resp = client.responses.create(
        model=model or os.getenv("META_MODEL", "muse-spark-1.3"),
        instructions=GUIDE,
        input=build_input(result),
        reasoning={"effort": effort or os.getenv("META_EFFORT", "low")},
    )
    return parse_reply(resp.output_text or "", "meta")


def classify(result, mode=None):
    mode = mode or os.getenv("AI_MODE", "mock")
    if result.get("error") or result.get("image") is None:
        return Verdict(category="unsure", confidence="low",
                       reason="The file could not be read.", next_step="ask_human")
    if mode == "meta":
        return meta_classify(result)
    return mock_classify(result)