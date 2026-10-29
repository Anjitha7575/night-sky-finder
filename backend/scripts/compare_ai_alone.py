"""Compare: Muse Spark ALONE (just looks at the clip) vs our agent (measurements + tools).

Run from backend/:
  python scripts/compare_ai_alone.py --limit 1 --how video    # try 1 clip first
  python scripts/compare_ai_alone.py --how frames             # all clips, 8 frames each
  python scripts/compare_ai_alone.py --how frames --run-ours  # also run our agent where no saved answer exists

"AI alone" gets no numbers and no tools. "Ours" comes from data/answers.json (saved when you
click a clip in the UI with AI_MODE=meta), or is run now with --run-ours.
Results are printed and saved to results/compare_<time>.json.
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skyfinder.agent import investigate
from skyfinder.classify import parse_reply
from skyfinder.measure import measure, read_frames

load_dotenv()

VIDEO_TYPES = {".mp4", ".mov", ".avi", ".gif"}
ALONE_GUIDE = """You check clips from fixed night-sky cameras and say what moving object was seen.
You get only the clip itself: no measurements, no other help.

Categories: meteor, satellite, plane, bird, insect, cloud, flash, not_sky, unsure.
If unsure, say "unsure" or use low confidence.

Reply with JSON only:
{"category": "...", "confidence": "high|medium|low", "reason": "1-2 short sentences", "next_step": "none|watch_video|ask_human"}"""


def expert_label(name):
    if name.startswith("meteor__"):
        return "meteor"
    if name.startswith("non_meteor__"):
        return "not meteor"
    return None  # no expert label for this clip


def frames_input(path, count=8, side=768):
    frames, _, _ = read_frames(path)
    picks = [frames[int(i)] for i in np.linspace(0, len(frames) - 1, count)]
    content = [{"type": "input_text", "text": f"{count} frames from the clip, in time order."}]
    for f in picks:
        scale = min(1.0, side / max(f.shape))
        f = cv2.resize(f, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        ok, png = cv2.imencode(".png", f)
        content.append({"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()})
    return [{"role": "user", "content": content}]


def video_input(path):
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return [{"role": "user", "content": [
        {"type": "input_text", "text": "The full clip is attached."},
        {"type": "input_file", "filename": Path(path).name, "file_data": "data:video/mp4;base64," + data},
    ]}]


def ai_alone(client, path, how):
    use_video = how == "video" and Path(path).suffix.lower() != ".gif"  # GIFs always go as frames
    resp = client.responses.create(
        model=os.getenv("META_MODEL", "muse-spark-1.3"),
        instructions=ALONE_GUIDE,
        input=video_input(path) if use_video else frames_input(path),
        reasoning={"effort": os.getenv("META_EFFORT", "low")},
    )
    verdict = parse_reply(resp.output_text or "", "meta")
    tokens = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
    return verdict, tokens, "video" if use_video else "frames"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--how", choices=["video", "frames"], default="frames")
    parser.add_argument("--limit", type=int, default=0, help="only the first N clips (0 = all)")
    parser.add_argument("--run-ours", action="store_true", help="run our agent when no saved answer exists (costs tokens)")
    args = parser.parse_args()

    from openai import OpenAI
    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.getenv("META_API_KEY"))

    samples = Path(os.getenv("SAMPLES_DIR", "data/sample"))
    clips = sorted(p for p in samples.rglob("*") if p.suffix.lower() in VIDEO_TYPES)
    if args.limit:
        clips = clips[:args.limit]
    saved = {}
    answers_file = Path(os.getenv("ANSWERS_FILE", "data/answers.json"))
    if answers_file.exists():
        saved = json.loads(answers_file.read_text())

    print(f"{len(clips)} clip(s), AI alone sees: {args.how}\n")
    rows = []
    total = {"input": 0, "output": 0}
    for path in clips:
        name = str(path.relative_to(samples))
        row = {"file": name, "expert": expert_label(path.name)}
        try:
            verdict, tokens, sent = ai_alone(client, path, args.how)
            row["alone"] = verdict.model_dump()
            row["alone_sent"] = sent
            row["alone_tokens"] = tokens
            total["input"] += tokens["input"]
            total["output"] += tokens["output"]
        except Exception as e:  # e.g. Meta does not accept the video format
            row["alone"] = {"category": "error", "reason": str(e)[:300]}

        ours = saved.get(f"meta:{name}")
        if ours is None and args.run_ours:
            answer = investigate(path, measure(path), mode="meta")
            ours = {"verdict": answer["verdict"].model_dump(), "steps": answer["steps"], "usage": answer.get("usage")}
            u = answer.get("usage") or {}
            total["input"] += u.get("input_tokens", 0)
            total["output"] += u.get("output_tokens", 0)
        row["ours"] = ours["verdict"] if ours else None
        row["ours_checks"] = len(ours["steps"]) if ours else None
        rows.append(row)

        a = row["alone"]["category"]
        o = row["ours"]["category"] if row["ours"] else "-"
        print(f"{name[:55]:55}  expert: {str(row['expert']):10}  alone: {a:9}  ours: {o}")
        if a == "error":
            print("   alone error:", row["alone"]["reason"])

    cost = total["input"] / 1e6 * 1.25 + total["output"] / 1e6 * 4.25  # muse-spark-1.3 prices per 1M tokens
    print(f"\ntokens used now: {total}  (about ${cost:.2f})")

    out = Path("results")
    out.mkdir(exist_ok=True)
    file = out / f"compare_{args.how}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    file.write_text(json.dumps({"how": args.how, "tokens": total, "rows": rows}, indent=1))
    print("saved:", file)


if __name__ == "__main__":
    main()
