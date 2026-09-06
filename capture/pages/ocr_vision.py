#!/usr/bin/env python3
"""Apple Vision OCR over a set of images. Local, free, no network, no API key.

Reads image paths (newline-delimited) from a file, a directory walk, or stdin and
emits one JSON object per image on stdout.

Per-image output includes mean/min recognition confidence. That confidence is the
calibration input for the purge gate downstream -- it is never discarded, because a
purge decision without a confidence attached is unfalsifiable.

Requires: pyobjc-framework-Vision, pyobjc-framework-Quartz (macOS 10.15+).

    python3 ocr_vision.py --dir /path/to/images --out ocr.jsonl
    find . -name '*.png' | python3 ocr_vision.py --stdin --out ocr.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import Vision
from Foundation import NSURL

RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".gif", ".tiff", ".tif", ".bmp"}


def recognize(path: Path, level: str = "accurate") -> dict:
    """Run VNRecognizeTextRequest against one image. Never raises."""
    rec = {"path": str(path), "ok": False}
    try:
        url = NSURL.fileURLWithPath_(str(path))
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
        req = Vision.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLevel_(
            Vision.VNRequestTextRecognitionLevelAccurate
            if level == "accurate"
            else Vision.VNRequestTextRecognitionLevelFast
        )
        req.setUsesLanguageCorrection_(True)

        ok, err = handler.performRequests_error_([req], None)
        if not ok:
            rec["error"] = str(err)
            return rec

        lines, confs = [], []
        for obs in req.results() or []:
            cands = obs.topCandidates_(1)
            if not cands:
                continue
            lines.append(str(cands[0].string()))
            confs.append(float(cands[0].confidence()))

        text = "\n".join(lines)
        rec.update(
            ok=True,
            n_obs=len(lines),
            mean_conf=round(sum(confs) / len(confs), 4) if confs else 0.0,
            min_conf=round(min(confs), 4) if confs else 0.0,
            chars=len(text),
            text=text,
        )
    except Exception as exc:  # noqa: BLE001 - a bad image must not kill a 3,500-image run
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def iter_paths(args) -> list[Path]:
    if args.stdin:
        raw = [Path(l.strip()) for l in sys.stdin if l.strip()]
    elif args.dir:
        raw = [p for p in Path(args.dir).rglob("*") if p.is_file()]
    else:
        raw = [Path(p) for p in args.paths]
    return [p for p in raw if p.suffix.lower() in RASTER_SUFFIXES]


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch Apple Vision OCR -> JSONL")
    ap.add_argument("paths", nargs="*", help="image paths")
    ap.add_argument("--dir", help="recursively OCR every raster image under this directory")
    ap.add_argument("--stdin", action="store_true", help="read newline-delimited paths from stdin")
    ap.add_argument("--out", help="write JSONL here instead of stdout")
    ap.add_argument("--level", choices=["accurate", "fast"], default="accurate")
    ap.add_argument("--progress-every", type=int, default=100, help="progress to stderr; 0 disables")
    args = ap.parse_args()

    paths = iter_paths(args)
    if not paths:
        print("no raster images found", file=sys.stderr)
        return 1

    sink = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        for i, p in enumerate(paths, 1):
            sink.write(json.dumps(recognize(p, args.level), ensure_ascii=False) + "\n")
            if args.progress_every and i % args.progress_every == 0:
                sink.flush()
                print(f"  ocr {i}/{len(paths)}", file=sys.stderr)
    finally:
        if args.out:
            sink.close()
    print(f"done: {len(paths)} images", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
