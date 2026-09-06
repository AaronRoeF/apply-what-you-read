#!/usr/bin/env python3
"""Stage 3 -- the judgment step. Classifies each image and produces a second OCR opinion.

Why a model is needed here at all: you cannot decide keep-vs-purge from OCR output. A
whiteboard photo and a screenshot of a paragraph both return a wall of text. One must be
kept -- its meaning is spatial, and OCR destroys it -- and one is pure redundancy. Identical
signal, opposite verdict. No threshold separates them.

The response does double duty:
  * bucket        -> the keep/purge decision
  * transcription -> an INDEPENDENT second OCR opinion, which is what makes the verifier's
                     agreement signal possible. Two engines converging is the strongest
                     evidence available without ground truth.

Resumable by design: already-classified paths are skipped, so an interrupted run over
thousands of images costs nothing to restart.

    python3 classify.py --manifest out/manifest.json --ocr out/ocr.jsonl --out out/classify.jsonl
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

MAX_EDGE = 1568          # Anthropic's recommended long-edge cap; larger buys nothing
MIN_BYTES = 2048         # below this it's an email tracking pixel, never worth a call

PROMPT = """You are triaging one image from a personal notes archive. The reader
wants images whose information is fully captured by text to be replaced by that text, and
all other images kept.

Classify into exactly one bucket:

- "text_dominant": a document scan, screenshot of text, receipt, or handwritten page. Its
  value is the words. Transcribing it loses essentially nothing.
- "structural": a whiteboard, diagram, chart, slide, table, map, or annotated screenshot.
  It contains text, but the MEANING IS SPATIAL - layout, arrows, grouping, position. A
  transcription would destroy what makes it useful. When genuinely torn, choose this.
- "non_text": a photo of a person, place, object, or scene. Little or no meaningful text.

Then transcribe ALL text you can read, verbatim, preserving reading order. For handwriting,
transcribe as accurately as you can. If you cannot read a word, write [?]. Do not summarize,
correct, or paraphrase - this transcription is compared against another OCR engine, so any
"improvement" you make corrupts that comparison.

For "structural" only, add a one-sentence description of what the image depicts.

Respond with ONLY a JSON object:
{"bucket": "...", "transcription": "...", "description": "...", "confidence": 0.0-1.0}"""


def load_env(path: Path) -> None:
    """Read KEY=VALUE lines from a .env file into the environment. Never logs values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def encode(path: Path) -> tuple[str, str] | None:
    try:
        img = Image.open(path)
        img = img.convert("RGB")
        if max(img.size) > MAX_EDGE:
            img.thumbnail((MAX_EDGE, MAX_EDGE))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
    except Exception:
        return None


def classify_one(client, model: str, path: Path) -> dict:
    rec = {"path": str(path)}
    enc = encode(path)
    if enc is None:
        return {**rec, "error": "unreadable"}
    b64, media = enc
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
                {"type": "text", "text": PROMPT},
            ]}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json").strip()
        data = json.loads(raw)
        return {
            **rec,
            "bucket": data.get("bucket"),
            "text": data.get("transcription", ""),
            "description": data.get("description", ""),
            "model_conf": data.get("confidence"),
            "in_tokens": msg.usage.input_tokens,
            "out_tokens": msg.usage.output_tokens,
        }
    except Exception as exc:  # noqa: BLE001
        return {**rec, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify images and produce a second OCR opinion")
    ap.add_argument("--ocr", required=True, help="ocr.jsonl from capture/pages/ocr.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--env", default=".env")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="stop after N images (for cost probes)")
    ap.add_argument("--include-no-text", action="store_true",
                    help="also classify images where Vision found nothing (default: skip, auto-keep)")
    args = ap.parse_args()

    load_env(Path(args.env))
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(f"ANTHROPIC_API_KEY not found (looked in env and {args.env})")
    import anthropic
    client = anthropic.Anthropic()

    todo = []
    for line in Path(args.ocr).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        p = Path(r["path"])
        if not p.exists() or p.stat().st_size < MIN_BYTES:
            continue                                   # junk pixel
        if not args.include_no_text and r.get("chars", 0) == 0:
            continue                                   # non-text -> keep, no model call
        todo.append(p)

    done = set()
    outp = Path(args.out)
    if outp.exists():
        for line in outp.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["path"])
    todo = [p for p in todo if str(p) not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"to classify: {len(todo)}  (already done: {len(done)})", file=sys.stderr)
    if not todo:
        return 0

    tin = tout = 0
    with open(outp, "a", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(classify_one, client, args.model, p): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            tin += rec.get("in_tokens", 0) or 0
            tout += rec.get("out_tokens", 0) or 0
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 25 == 0:
                print(f"  classified {i}/{len(todo)}  tokens in={tin} out={tout}", file=sys.stderr)
    print(f"done: {len(todo)} images, tokens in={tin} out={tout}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
