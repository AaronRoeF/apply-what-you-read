#!/usr/bin/env python3
"""Deterministic highlight detection. No model, no API.

A highlighter mark is a saturated colour band on a page that is otherwise near-neutral
(black text, white/grey paper). That is a signal-processing problem, not a judgement
problem -- and the pipeline's governing principle is that search and detection stay
deterministic while the model is reserved for judgement.

Validated against agent labels before use; see --validate.
"""
from __future__ import annotations
import argparse, colorsys, json, pathlib
from PIL import Image

def highlight_stats(path: pathlib.Path, max_edge: int = 500) -> dict:
    try:
        im = Image.open(path).convert("RGB")
    except Exception as e:
        return {"ok": False, "error": str(e)[:60]}
    im.thumbnail((max_edge, max_edge))
    px = list(im.getdata())
    n = len(px)
    if not n:
        return {"ok": False, "error": "empty"}
    yellow = pink = other_sat = bright = 0
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        if v > 0.55:
            bright += 1
        # a highlighter is bright AND saturated; ink and paper are not
        if s < 0.22 or v < 0.45:
            continue
        deg = h * 360
        if 35 <= deg <= 75:        yellow += 1
        elif 280 <= deg <= 350:    pink += 1
        elif 0 <= deg <= 20:       pink += 1        # warm magenta/red wrap
        else:                      other_sat += 1
    denom = max(1, bright)
    return {"ok": True, "n": n,
            "yellow_frac": round(yellow/denom, 4),
            "pink_frac": round(pink/denom, 4),
            "other_frac": round(other_sat/denom, 4),
            "highlight_frac": round((yellow+pink)/denom, 4)}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", help="judged jsonl with agent 'annotations' labels")
    ap.add_argument("--ocr", help="ocr.jsonl (to enumerate images)")
    ap.add_argument("--out")
    ap.add_argument("--threshold", type=float, default=0.012)
    a = ap.parse_args()

    if a.validate:
        rows = [json.loads(l) for l in open(a.validate) if l.strip()]
        tp = fp = tn = fn = 0
        for r in rows:
            p = pathlib.Path(r["path"])
            if not p.exists() or r.get("annotations") is None: continue
            st = highlight_stats(p)
            if not st.get("ok"): continue
            pred = st["highlight_frac"] >= a.threshold
            truth = bool(r["annotations"])
            if pred and truth: tp += 1
            elif pred and not truth: fp += 1
            elif not pred and truth: fn += 1
            else: tn += 1
        tot = tp+fp+tn+fn
        print(f"  validated on {tot} agent-labelled images (threshold {a.threshold})")
        print(f"    true pos {tp}   false pos {fp}   true neg {tn}   false neg {fn}")
        if tp+fp: print(f"    precision {tp/(tp+fp)*100:.0f}%")
        if tp+fn: print(f"    recall    {tp/(tp+fn)*100:.0f}%")
        if tot:   print(f"    accuracy  {(tp+tn)/tot*100:.0f}%")
        return 0

    paths = [pathlib.Path(json.loads(l)["path"]) for l in open(a.ocr) if l.strip()]
    paths = [p for p in paths if p.exists()]
    with open(a.out, "w") as fh:
        for i, p in enumerate(paths, 1):
            st = highlight_stats(p); st["path"] = str(p)
            fh.write(json.dumps(st) + "\n")
            if i % 250 == 0: print(f"    {i}/{len(paths)}", flush=True)
    print(f"  scanned {len(paths)} images -> {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
