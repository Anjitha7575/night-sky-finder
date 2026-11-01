import base64
import json
import os
from typing import Literal

import cv2
from typing import Optional, get_args

from pydantic import BaseModel, ValidationError, field_validator

Category = Literal[
    "meteor", "satellite", "plane", "bird", "insect",
    "cloud", "flash", "aurora", "reentry", "not_sky", "unsure",
]


class Verdict(BaseModel):
    category: Category
    confidence: Literal["high", "medium", "low"]
    reason: str
    next_step: Literal["none", "watch_video", "ask_human"]
    key_clue: str = ""  # the one clue that decided it (filled by the agent)
    also: Optional[Category] = None  # second guess, only when torn between two answers

    @field_validator("also", mode="before")
    @classmethod
    def clean_also(cls, value):
        # an unknown second guess should not throw away the whole answer
        return value if value in get_args(Category) else None
    source: Literal["mock", "meta"] = "mock"


GUIDE = """You check clips from fixed night-sky cameras and say what moving object was seen.

What you get:
- Image 1: all frames stacked, still background removed, so a moving object shows as its whole path.
- Image 2: one normal frame from the middle of the clip: what the camera actually saw. Slow or large things
  (aurora, clouds, halos, the Moon) can be almost invisible in image 1 but clear in image 2.
- Measurements made by code from the video (when it is a video or GIF), and a short camera description.

How objects usually look (compare speeds only within the same camera):
- meteor: fast, straight, usually seen for about a second or less, often brightens then fades. A fast meteor can look like a row of evenly spaced dots, because it jumps more than its own size between frames; it is still seen in almost every frame.
- fireball (answer "meteor"): a very bright meteor. It can last several seconds (2 to 10 s), often has a glowing head with a tail, flares or breaks into pieces, and can light up the sky. Do not rule out a meteor just because it lasts a few seconds if it is very bright and flares.
- plane: slow, straight, seen for several seconds, lights blink, so the path is a dotted line with gaps in time (low seen ratio).
- satellite: slow, straight, steady brightness, seen in almost every frame, no blinking, no tail. Usually crosses for much longer than a fireball. A satellite flare is a smooth brightening and fading of a small point, with no tail.
- bird or insect: curved or wavy path, often blurry, can be near the camera and look big.
- cloud: large soft patches, no clear point or line, changes slowly.
- flash: most of the sky lights up at once for a very short time (lightning, very bright fireball flash, or camera glitch). Red sprites (short red flashes high above a thunderstorm) also count as flash.
- aurora: large soft glowing curtains, arcs or vertical rays (often green or red; grey on black-and-white cameras), usually low over the horizon, changing slowly over minutes to hours. No single moving point. Look for it in image 2.
- reentry: space junk or a rocket stage burning up. Much slower and longer than a fireball (tens of seconds to minutes), often breaking into many glowing pieces that travel together.
- not_sky: the picture is not from a night-sky camera.

Rules:
- Answer about the MAIN event in the clip. If image 2 shows aurora or lightning filling the sky, answer that,
  even if a few small dots (stars, noise, birds) are also tracked by our code.
- Use the image and the numbers together. If they disagree, say so in the reason.
- A fisheye all-sky lens bends straight paths near the edge of the circle.
- Numbers can be unreliable when the note says so; then rely more on the image.
- If unsure, use category "unsure" or a low confidence. Do not guess with high confidence.
- If you are torn between two answers (common: plane or satellite, bird or insect, meteor or reentry),
  put your best answer in "category" and the other one in "also". Otherwise "also" is null.
- next_step: "none" if confident, "watch_video" if the full video would help, "ask_human" if even that would not help.
- Write the reason in 1 or 2 short, plain sentences.

Reply with JSON only, exactly these keys:
{"category": one of meteor|satellite|plane|bird|insect|cloud|flash|aurora|reentry|not_sky|unsure,
 "also": null or one of the same values (your second guess),
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


def png_url(image):
    ok, png = cv2.imencode(".png", image)
    return "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()


def build_input(result):
    """The first message for Meta's /v1/responses API: text + image 1 (what moved) + image 2 (normal view).
    The GUIDE goes separately, as "instructions"."""
    content = [
        {"type": "input_text", "text": "Measurements:\n" + describe(result) + "\n\nImage 1: what moved (all frames stacked)."},
        {"type": "input_image", "image_url": png_url(result["image"])},
    ]
    if result.get("scene") is not None:
        content += [
            {"type": "input_text", "text": "Image 2: a normal frame from the middle of the clip."},
            {"type": "input_image", "image_url": png_url(result["scene"])},
        ]
    return [{"role": "user", "content": content}]


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
        return Verdict(category="satellite", confidence="low", also="plane",
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