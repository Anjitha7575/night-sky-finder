"""Compare: Muse Spark ALONE (just looks at the clip) vs our agent (measurements + tools).

Big test, run from backend/:
  python scripts/compare_ai_alone.py --folder data/nightskyucp_test --name NightSkyUCP_results --run-ours --limit 10
  python scripts/compare_ai_alone.py --folder data/nightskyucp_test --name NightSkyUCP_results --run-ours

- Saves to results/<name>.json after EVERY clip, and skips clips already in that file,
  so stopping and re-running never pays twice.
- Stops by itself when this run's cost passes --max-cost (default $6).

"AI alone" gets no numbers and no tools. "Ours" (our agent) runs only with --run-ours.
Results are printed and saved to results/<name>.json.
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


def expert_label(path):
    """Known answer from the file name prefix (meteor__ / non_meteor__) or the folder name (meteor/ / non_meteor/)."""
    for part in (path.name.split("__")[0], path.parent.name):
        if part == "meteor":
            return "meteor"
        if part == "non_meteor":
            return "not meteor"
    return None  # no known answer for this clip


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
        store=False,  # big videos can't be saved on Meta's side; we don't need them saved
    )
    verdict = parse_reply(resp.output_text or "", "meta")
    tokens = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
    return verdict, tokens, "video" if use_video else "frames"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--how", choices=["video", "frames"], default="frames")
    parser.add_argument("--limit", type=int, default=0, help="only the first N clips (0 = all)")
    parser.add_argument("--run-ours", action="store_true", help="also run our agent (costs tokens)")
    parser.add_argument("--folder", default=os.getenv("SAMPLES_DIR", "data/sample"), help="folder with the clips")
    parser.add_argument("--name", default=None, help="results file name, e.g. NightSkyUCP_results")
    parser.add_argument("--redo-ours", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="after a measure change: run only our agent again on clips whose measurements changed "
                             "(two measure_snapshot.py files). The 'AI alone' answers are kept.")
    parser.add_argument("--max-cost", type=float, default=6.0, help="stop when this run has cost more than this many dollars")
    args = parser.parse_args()

    from openai import OpenAI
    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.getenv("META_API_KEY"))

    samples = Path(args.folder)
    clips = sorted(p for p in samples.rglob("*") if p.suffix.lower() in VIDEO_TYPES)
    if args.limit:
        clips = clips[:args.limit]
    out = Path("results")
    out.mkdir(exist_ok=True)
    file = out / f"{args.name or 'compare_' + args.how + '_' + time.strftime('%Y%m%d_%H%M%S')}.json"
    rows = json.loads(file.read_text())["rows"] if file.exists() else []
    rows = [r for r in rows if r["alone"]["category"] != "error"]  # failed clips run again
    done = {r["file"] for r in rows}
    todo = [p for p in clips if str(p.relative_to(samples)) not in done]
    if not args.redo_ours:
        print(f"{len(clips)} clip(s): {len(done)} already done, {len(todo)} to run. AI alone sees: {args.how}\n")

    def cost(t):
        return t["input"] / 1e6 * 1.25 + t["output"] / 1e6 * 4.25  # muse-spark-1.3 prices per 1M tokens

    def save():
        file.write_text(json.dumps({"how": args.how, "folder": str(samples), "rows": rows}, indent=1))

    if args.redo_ours:
        before, after = (json.loads(Path(f).read_text()) for f in args.redo_ours)
        changed = {k for k in after if before.get(k) != after[k]}
        redo = [r for r in rows if r["file"] in changed and not r.get("redone")]
        print(f"{len(changed)} clip(s) measured differently, {len(redo)} to run again (ours only)\n")
        total = {"input": 0, "output": 0}
        for row in redo:
            if cost(total) > args.max_cost:
                print(f"\nSTOPPED: this run cost more than ${args.max_cost}. Run again to continue.")
                break
            path = samples / row["file"]
            old = row["ours"]["category"] if row.get("ours") else "-"
            answer = investigate(path, measure(path), mode="meta")
            row["ours"] = answer["verdict"].model_dump()
            row["ours_checks"] = len(answer["steps"])
            row["ours_tokens"] = answer.get("usage")
            row["redone"] = True  # so a second run (after a stop) skips it
            u = answer.get("usage") or {}
            total["input"] += u.get("input_tokens", 0)
            total["output"] += u.get("output_tokens", 0)
            save()
            print(f"{row['file'][:55]:55}  expert: {str(row['expert']):10}  ours: {old:9} -> {row['ours']['category']}")
        print(f"\ntokens used in this run: {total}  (about ${cost(total):.2f})")
        return

    total = {"input": 0, "output": 0}
    for path in todo:
        if cost(total) > args.max_cost:
            print(f"\nSTOPPED: this run cost more than ${args.max_cost}. Run again to continue.")
            break
        name = str(path.relative_to(samples))
        row = {"file": name, "expert": expert_label(path)}
        try:
            verdict, tokens, sent = ai_alone(client, path, args.how)
            row["alone"] = verdict.model_dump()
            row["alone_sent"] = sent
            row["alone_tokens"] = tokens
            total["input"] += tokens["input"]
            total["output"] += tokens["output"]
        except Exception as e:  # e.g. Meta does not accept the video format
            row["alone"] = {"category": "error", "reason": str(e)[:300]}

        ours = None
        if args.run_ours:
            answer = investigate(path, measure(path), mode="meta")
            ours = {"verdict": answer["verdict"].model_dump(), "steps": answer["steps"], "usage": answer.get("usage")}
            u = answer.get("usage") or {}
            total["input"] += u.get("input_tokens", 0)
            total["output"] += u.get("output_tokens", 0)
        row["ours"] = ours["verdict"] if ours else None
        row["ours_checks"] = len(ours["steps"]) if ours else None
        row["ours_tokens"] = ours.get("usage") if ours else None
        rows.append(row)
        save()  # after every clip, so nothing is lost or paid twice

        a = row["alone"]["category"]
        o = row["ours"]["category"] if row["ours"] else "-"
        print(f"{name[:55]:55}  expert: {str(row['expert']):10}  alone: {a:9}  ours: {o}")
        if a == "error":
            print("   alone error:", row["alone"]["reason"])

    print(f"\ntokens used in this run: {total}  (about ${cost(total):.2f})")
    print(f"saved: {file}  ({len(rows)} clips in total)")


if __name__ == "__main__":
    main()