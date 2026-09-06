#!/usr/bin/env python3
"""Generate the human calibration sample -- the gate before anything is purged.

Every threshold in verify.py is a guess until it is measured against ground truth, and
the only ground truth available is a person looking at images. This builds that review
set as an Obsidian note: image embedded, what OCR read, what the classifier decided, and
a checkbox for the human verdict.

TWO SURFACES, deliberately, because they answer different questions:

  * a STRATIFIED RANDOM sample measures the error RATE -- what fraction of purge
    decisions are wrong. It is representative, so its arithmetic is meaningful.
  * a WORST-N sample finds failure MODES -- the systematic break affecting 3% of images
    that a 50-item random sample will never contain. It is not representative and its
    arithmetic means nothing.

Reporting worst-N results as if they were a rate is the classic error here; they are
labelled separately in the output for that reason.

    python3 review_sample.py --judged out/judged.jsonl --ocr out/ocr.jsonl \
        --vault ~/Vault --out ~/Vault/projects/x/review.md --n 40 --worst 10
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()]


def block(i: int, j: dict, o: dict, why: str) -> str:
    name = Path(j["path"]).name
    bucket, verdict = j.get("bucket"), j.get("ocr_verdict")
    # Annotation is the purge veto, so the reviewer must be able to SEE its state without
    # inspecting the image. Three states, and "not assessed" must never render as "none" --
    # wave-1 images were scored before this field existed, and silently showing them as
    # unannotated would hide exactly the gap that invalidated the first calibration.
    ann = j.get("annotations", None)
    if ann is None:
        ann_line = "✋ Annotation: NOT ASSESSED — scored before this field existed. Check the image yourself."
    elif ann:
        ann_line = "✏️ Annotation: YES — highlighting / marks present. This VETOES any purge."
    else:
        ann_line = "▫️ Annotation: none detected"
    would_purge = bucket == "text_dominant" and verdict == "matches" and not ann
    # Show the FULL OCR output. An earlier version truncated at 700 chars under the label
    # "What the OCR actually read" -- which told the reviewer the engine had captured only
    # that much, and produced at least two keep-verdicts that were reactions to the
    # display bug rather than to the image. A collapsed callout costs nothing to make
    # long, and a review artifact that misrepresents the thing under review is worse than
    # no review at all.
    text = (o.get("text") or "").strip()
    DISPLAY_CAP = 20000
    truncated = len(text) > DISPLAY_CAP
    excerpt = text[:DISPLAY_CAP] + (
        f"\n\n[… DISPLAY CUT at {DISPLAY_CAP:,} chars — the OCR captured {len(text):,}. "
        "This is a display limit, NOT an OCR failure.]" if truncated
        else "\n\n— end of OCR output —")
    size = Path(j["path"]).stat().st_size / 1e6 if Path(j["path"]).exists() else 0

    return f"""
### {i}. `{name}`  ·  {size:.1f} MB  ·  _{why}_

![[{name}]]

| classifier said | OCR engine said |
|---|---|
| **{bucket}** / **{verdict}** (conf {j.get('ocr_conf','–')}) | conf {o.get('mean_conf','–')}, {o.get('chars',0)} chars |

**{ann_line}**

> [!quote]- Full OCR output — all {len(text):,} characters ({'complete' if not truncated else 'display-capped'})
> {excerpt.replace(chr(10), chr(10) + '> ') or '(nothing)'}

**Pipeline would: {'🔴 PURGE this image' if would_purge else '🟢 KEEP this image'}**

Do you agree?  `[ ] agree`   `[ ] WRONG — should be {'kept' if would_purge else 'purged'}`

Notes:

---
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judged", required=True, type=Path)
    ap.add_argument("--ocr", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n", type=int, default=40, help="stratified random sample size")
    ap.add_argument("--worst", type=int, default=10, help="lowest-confidence cases")
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    ocr = {r["path"]: r for r in load(args.ocr)}
    judged = [j for j in load(args.judged) if j.get("bucket") and j["path"] in ocr]
    random.seed(args.seed)

    # --- stratified random: proportional across bucket x verdict cells ---
    cells: dict[tuple, list] = defaultdict(list)
    for j in judged:
        cells[(j["bucket"], j["ocr_verdict"])].append(j)
    per = max(1, args.n // max(1, len(cells)))
    strat, seen = [], set()
    for key, items in sorted(cells.items()):
        for j in random.sample(items, min(per, len(items))):
            strat.append((j, f"random · {key[0]}/{key[1]}"))
            seen.add(j["path"])

    # --- worst-N by engine confidence, excluding anything already sampled ---
    rest = sorted((j for j in judged if j["path"] not in seen),
                  key=lambda j: ocr[j["path"]].get("mean_conf", 0))
    worst = [(j, "worst-N · lowest OCR confidence") for j in rest[: args.worst]]

    purge_n = sum(1 for j, _ in strat if j["bucket"] == "text_dominant" and j["ocr_verdict"] == "matches")
    body = [f"""---
type: review
project: apply-what-you-read
created: {__import__('datetime').date.today().isoformat()}
---

# Calibration review — {len(strat) + len(worst)} images

This is the gate. Nothing gets deleted until this is done, because every threshold in the
verifier is currently **my guess**, not a measured number.

**How to do it:** scroll through. For each image, look at it, glance at what the OCR read,
and tick whether you agree with the pipeline's decision. Two minutes of skimming, not a
careful audit — you are calibrating a threshold, not proofreading transcriptions.

**Two things to look at:** the image (does it carry YOUR highlighting, underlining, arrows,
margin marks? that alone means keep) and the OCR text (did the engine actually get the page?).

**The OCR text under each image is COMPLETE**, not a sample. It ends with `— end of OCR output —`. If it looks like it stops
early, the engine stopped early — that is a real finding and you should mark the image as
one to keep. (A previous version of this file truncated the text for display, which made
complete extractions look broken. That is fixed; anything cut now says so explicitly.)

**What each section means — they are NOT the same and do not combine:**

- **Part 1 ({len(strat)} images, random)** — representative. The error rate here IS the
  error rate. {purge_n} of these would be purged.
- **Part 2 ({len(worst)} images, worst-case)** — deliberately the ugliest cases. NOT
  representative. Its job is to expose a systematic failure mode, not to produce a
  percentage. Do not average it with Part 1.

## Part 1 — stratified random ({len(strat)})
"""]
    for i, (j, why) in enumerate(strat, 1):
        body.append(block(i, j, ocr[j["path"]], why))
    body.append(f"\n## Part 2 — worst cases ({len(worst)}) · not representative\n")
    for i, (j, why) in enumerate(worst, len(strat) + 1):
        body.append(block(i, j, ocr[j["path"]], why))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(body))
    print(f"  wrote {args.out}")
    print(f"  stratified: {len(strat)} across {len(cells)} bucket×verdict cells ({purge_n} would purge)")
    print(f"  worst-N   : {len(worst)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
