"""The AI detective: first look, then (only if needed) it asks for more evidence.

investigate(path, result) -> {"steps": [...], "verdict": Verdict}
- mock mode: simple rules pretend to be the agent (for testing without a key)
- meta mode: Muse Spark decides which tools to call, up to MAX_STEPS
"""
import base64
import json
import os

import cv2

from skyfinder.classify import GUIDE, Verdict, build_input, classify, describe, mock_classify, parse_reply
from skyfinder.tools import TOOLS, run_tool

MAX_STEPS = 3

AGENT_GUIDE = GUIDE + """

You can ask for more evidence before you answer, using the tools.
- Only call a tool if it could change your answer. If the first look is clear, answer right away.
- At most 3 tool calls. "watch_video" costs the most, so use it last.
- In each tool call, fill "why" with one short sentence: what you hope to learn.
In your final JSON also add "key_clue": the one clue that decided your answer, in a few words."""

# tool menu in the /v1/responses format
TOOL_SPECS = [
    {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {"why": {"type": "string", "description": "One short sentence: what you hope this check tells you."}},
            "required": ["why"],
        },
    }
    for name, (_, _, description) in TOOLS.items()
]


def to_b64(image):
    if image is None:
        return None
    ok, png = cv2.imencode(".png", image)
    return base64.b64encode(png.tobytes()).decode() if ok else None


def make_step(tool, title, why, found, image):
    return {"tool": tool, "title": title, "why": why, "found": found, "image_png_base64": to_b64(image)}


def first_look(result):
    return make_step("first_look", "First look", "Look at the whole path and the measurements.",
                     describe(result).replace("\n", "; "), result.get("image"))


def tool_step(name, why, path, result):
    out = run_tool(name, path, result)
    title = TOOLS[name][1] if name in TOOLS else name
    return make_step(name, title, why, out["text"], out.get("image")), out


# ---------- mock agent (no API key needed) ----------

def mock_investigate(path, result):
    steps = [first_look(result)]
    verdict = mock_classify(result)
    if verdict.confidence != "low" or not result.get("points"):
        verdict.key_clue = verdict.reason.rstrip(".").lower()
        return {"steps": steps, "verdict": verdict}

    step, out = tool_step("where_in_sky", "Is it slow because it is low near the horizon?", path, result)
    steps.append(step)
    straight = result.get("straightness") or 0
    short = (result.get("visible_sec") or 99) <= 1.5
    if out.get("pct", 0) >= 70 and straight >= 0.9 and short:
        verdict = Verdict(
            category="meteor", confidence="medium", next_step="watch_video",
            reason="Short and straight. It only looks slow because it is low near the horizon.",
            key_clue="near the horizon",
        )
        return {"steps": steps, "verdict": verdict}

    step, _ = tool_step("brightness_curve", "Does it flare like a meteor or stay steady?", path, result)
    steps.append(step)
    verdict.key_clue = "not enough clues"
    return {"steps": steps, "verdict": verdict}


# ---------- Muse Spark agent ----------

def meta_investigate(path, result, model=None, effort=None):
    from openai import OpenAI

    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.getenv("META_API_KEY"))
    items = build_input(result)  # the whole conversation so far, sent each round
    steps = [first_look(result)]
    usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    # Meta only accepts tool_choice="auto", so we can't forbid tools in the last round.
    # Instead, once the limit is reached, tool requests get "no more checks, answer now".
    for round_no in range(MAX_STEPS + 2):
        over = round_no >= MAX_STEPS
        resp = client.responses.create(
            model=model or os.getenv("META_MODEL", "muse-spark-1.3"),
            instructions=AGENT_GUIDE,
            input=items,
            tools=TOOL_SPECS,
            tool_choice="auto",
            reasoning={"effort": effort or os.getenv("META_EFFORT", "low")},
        )
        usage["calls"] += 1
        if getattr(resp, "usage", None):
            usage["input_tokens"] += resp.usage.input_tokens or 0
            usage["output_tokens"] += resp.usage.output_tokens or 0

        calls = [o for o in resp.output if o.type == "function_call"]
        if not calls:
            return {"steps": steps, "verdict": parse_reply(resp.output_text or "", "meta"), "usage": usage}

        # keep everything the model said (its thinking + tool requests) in the conversation
        items += [o.model_dump(exclude_none=True) for o in resp.output]
        pictures = []
        for call in calls:
            if over:
                items.append({"type": "function_call_output", "call_id": call.call_id,
                              "output": "No more checks allowed. Reply now with the final JSON only."})
                continue
            try:
                why = json.loads(call.arguments or "{}").get("why", "")
            except ValueError:
                why = ""
            step, out = tool_step(call.name, why, path, result)
            steps.append(step)
            items.append({"type": "function_call_output", "call_id": call.call_id, "output": out["text"]})
            if step["image_png_base64"]:
                pictures.append((step["title"], step["image_png_base64"]))
        # tool outputs carry text only, so pictures go in one user message after them
        if pictures:
            content = []
            for title, b64 in pictures:
                content.append({"type": "input_text", "text": f"Picture from: {title}"})
                content.append({"type": "input_image", "image_url": "data:image/png;base64," + b64})
            items.append({"role": "user", "content": content})

    return {"steps": steps, "verdict": parse_reply("", "meta"), "usage": usage}


def investigate(path, result, mode=None):
    mode = mode or os.getenv("AI_MODE", "mock")
    if result.get("error") or result.get("image") is None:
        return {"steps": [], "verdict": classify(result, mode)}
    try:
        if mode == "meta":
            return meta_investigate(path, result)
        return mock_investigate(path, result)
    except Exception as e:  # e.g. network or key problem: show it instead of crashing
        verdict = Verdict(category="unsure", confidence="low", next_step="ask_human",
                          reason=f"The AI check failed: {e}", source=mode if mode in ("mock", "meta") else "mock")
        return {"steps": [first_look(result)], "verdict": verdict}
