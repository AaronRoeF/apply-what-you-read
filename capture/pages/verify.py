#!/usr/bin/env python3
"""Verifier for the OCR pass. Scores extraction trustworthiness; gates the purge.

You cannot confirm per-image OCR correctness without ground truth. So this does not try.
It answers the tractable question instead: *is this extraction trustworthy enough that
deleting the source image would be safe?* Below threshold, the image is kept and nothing
is lost. That reframing is the whole design.

Four independent signals, deliberately not collapsed into one number until the end:

  1. engine_conf     Apple Vision's own mean confidence. Free, weak alone, real in combination.
  2. word_validity   Fraction of alphabetic tokens found in a system dictionary. Garbage OCR
                     produces character soup, and soup scores near zero here. This is the
                     single best cheap detector of a failed extraction.
  3. density         Characters recovered per megapixel. A full-page scan yielding 12
                     characters is a failure even when the engine reports high confidence.
  4. agreement       Normalized similarity between Vision's text and an independent second
                     extractor (a vision model — `reference/classify.py`, or any engine emitting {path, text}). Two independent
                     engines converging is the strongest evidence available without ground
                     truth. Absent until a second engine runs.

None of these means anything in absolute terms until calibrated against a hand-verified
sample -- see --sample, which emits a stratified review set. Uncalibrated scores are just
numbers. Calibration is what makes the purge threshold defensible.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


def load_dictionary() -> set[str]:
    import os
    for cand in (os.environ.get("RG_DICT", ""), "/usr/share/dict/words", "/usr/dict/words"):
        if not cand:
            continue
        p = Path(cand)
        if p.exists():
            return {w.strip().lower() for w in p.read_text(errors="replace").split("\n") if w.strip()}
    return set()


def word_validity(text: str, words: set[str]) -> float | None:
    """Share of alphabetic tokens that are real words. None when unmeasurable."""
    if not words:
        return None
    toks = WORD_RE.findall(text)
    if len(toks) < 5:
        return None
    hits = sum(1 for t in toks if t.lower().strip("'-") in words)
    return round(hits / len(toks), 4)


def density(chars: int, w: int, h: int) -> float | None:
    mp = (w * h) / 1_000_000 if w and h else 0
    return round(chars / mp, 1) if mp > 0.01 else None


def agreement(a: str, b: str) -> float:
    na, nb = " ".join(a.split()).lower(), " ".join(b.split()).lower()
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return round(SequenceMatcher(None, na, nb).ratio(), 4)


def score(rec: dict, words: set[str], second: dict | None) -> dict:
    text = rec.get("text", "") or ""
    out = {
        "path": rec["path"],
        "ok": rec.get("ok", False),
        "chars": rec.get("chars", 0),
        "engine_conf": rec.get("mean_conf", 0.0),
        "word_validity": word_validity(text, words),
        "density": density(rec.get("chars", 0), rec.get("width", 0), rec.get("height", 0)),
        "agreement": None,
        "flags": [],
    }
    if second and second.get("text"):
        out["agreement"] = agreement(text, second["text"])

    f = out["flags"]
    if not out["ok"]:
        # Vision rejects sub-64px images as "too small". In a notes-app export these are
        # overwhelmingly email tracking pixels and spacer GIFs from forwarded mail -- junk,
        # not failed extraction. Labelling them ocr_failed would poison the calibration
        # corpus with ~300 phantom failures and hide any real engine fault behind them.
        err = (rec.get("error") or "").lower()
        tiny = rec.get("bytes", 0) and rec["bytes"] < 2048
        f.append("junk_pixel" if ("too small" in err or tiny) else "ocr_failed")
    if out["chars"] == 0:
        f.append("no_text")                      # not an error: most likely a non-text image
    if out["engine_conf"] and out["engine_conf"] < 0.60:
        f.append("low_engine_conf")
    if out["word_validity"] is not None and out["word_validity"] < 0.55:
        f.append("low_word_validity")            # strongest failed-extraction signal
    if out["density"] is not None and out["chars"] > 0 and out["density"] < 20:
        f.append("sparse_for_size")
    if out["agreement"] is not None and out["agreement"] < 0.60:
        f.append("engines_disagree")

    # An annotation is the owner's own signal layer -- which passages they highlighted,
    # flagged, or arrowed -- and it is invisible to OCR. On an annotated page a `matches`
    # verdict is measuring the wrong thing: the text is captured, the selection over that
    # text is not, and the selection is usually why the photo exists. Annotation is
    # therefore an absolute veto, checked before any confidence arithmetic.
    if rec.get("annotations"):
        f.append("has_annotation")
        out["purge_eligible"] = False
        return out

    # Otherwise purge eligibility is deliberately conservative: every check must pass, and
    # an image with no second opinion is never eligible. A wrongly kept image costs disk;
    # a wrongly purged one costs information.
    out["purge_eligible"] = bool(
        out["ok"]
        and out["chars"] >= 40
        and out["engine_conf"] >= 0.80
        and (out["word_validity"] is None or out["word_validity"] >= 0.70)
        and out["agreement"] is not None
        and out["agreement"] >= 0.75
        and not {"ocr_failed", "low_engine_conf", "low_word_validity"} & set(f)
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Score OCR trustworthiness and gate purge")
    ap.add_argument("--ocr", required=True, help="ocr.jsonl from capture/pages/ocr.py")
    ap.add_argument("--second", help="optional second-engine JSONL (path,text) from classify.py")
    ap.add_argument("--out", required=True, help="scored JSONL destination")
    ap.add_argument("--report", help="human-readable report destination")
    ap.add_argument("--sample", type=int, default=0, help="emit N stratified images for hand-verification")
    ap.add_argument("--worst", type=int, default=30, help="how many worst cases to surface")
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    words = load_dictionary()
    second = {}
    if args.second and Path(args.second).exists():
        for line in Path(args.second).read_text().split("\n"):
            if line.strip():
                r = json.loads(line)
                second[r["path"]] = r

    scored = []
    with open(args.ocr, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                scored.append(score(rec, words, second.get(rec["path"])))

    Path(args.out).write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in scored))

    total = len(scored)
    withtext = [s for s in scored if s["chars"] > 0]
    lines = [
        "# OCR verification report",
        "",
        f"dictionary loaded      : {'yes (%d words)' % len(words) if words else 'NO - word_validity unavailable'}",
        f"second engine loaded   : {'yes (%d)' % len(second) if second else 'NO - agreement unavailable, nothing can be purge-eligible'}",
        "",
        f"images scored          : {total}",
        f"  with recognized text : {len(withtext)}",
        f"  no text (non-text)   : {total - len(withtext)}",
        f"  OCR failed outright  : {sum(1 for s in scored if 'ocr_failed' in s['flags'])}",
        f"  junk pixels (email)  : {sum(1 for s in scored if 'junk_pixel' in s['flags'])}",
        f"  purge-eligible       : {sum(1 for s in scored if s['purge_eligible'])}",
        "",
        "## flag counts",
    ]
    fc = {}
    for s in scored:
        for f in s["flags"]:
            fc[f] = fc.get(f, 0) + 1
    for k, v in sorted(fc.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {k:<22} {v}")

    if withtext:
        for field in ("engine_conf", "word_validity", "agreement"):
            vals = sorted(v for v in (s[field] for s in withtext) if v is not None)
            if vals:
                q = lambda p: vals[min(len(vals) - 1, int(len(vals) * p))]  # noqa: E731
                lines += [
                    "",
                    f"## {field} distribution (n={len(vals)})",
                    f"  p10={q(.10):.2f}  p25={q(.25):.2f}  median={q(.50):.2f}  p75={q(.75):.2f}  p90={q(.90):.2f}",
                ]

    # Worst-N finds failure MODES. A random sample measures the rate but will miss a
    # systematic break affecting a small share of images. You need both surfaces.
    ranked = sorted(withtext, key=lambda s: (s["engine_conf"], s["word_validity"] if s["word_validity"] is not None else 1))
    lines += ["", f"## worst {args.worst} by confidence - review these for failure modes"]
    for s in ranked[: args.worst]:
        lines.append(f"  conf={s['engine_conf']:.2f} wv={s['word_validity']} chars={s['chars']:<5} {Path(s['path']).name}")

    if args.sample:
        random.seed(args.seed)
        buckets = {"high": [], "mid": [], "low": [], "none": []}
        for s in scored:
            if s["chars"] == 0:
                buckets["none"].append(s)
            elif s["engine_conf"] >= 0.9:
                buckets["high"].append(s)
            elif s["engine_conf"] >= 0.7:
                buckets["mid"].append(s)
            else:
                buckets["low"].append(s)
        per = max(1, args.sample // len(buckets))
        lines += ["", f"## stratified hand-verification sample (~{args.sample}) - CALIBRATION ANCHOR"]
        for name, items in buckets.items():
            for s in random.sample(items, min(per, len(items))):
                lines.append(f"  [{name}] conf={s['engine_conf']:.2f} chars={s['chars']:<5} {s['path']}")

    report = "\n".join(lines)
    if args.report:
        Path(args.report).write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
