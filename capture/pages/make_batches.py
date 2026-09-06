#!/usr/bin/env python3
"""Build agent-path batches (Path B). See docs/CLASSIFY-PATHS.md.

Each batch entry carries the image path AND the text Apple Vision already read
from it. The agent's job is to *judge* that text against the image, not to
reproduce it -- bulk verbatim transcription of personal documents reliably trips
output content filtering and kills the whole batch. Judging costs ~20 output
tokens per image instead of ~300, and yields the same agreement signal.

    python3 make_batches.py --ocr out/ocr.jsonl --min-bytes 1000000 --size 12
"""
from __future__ import annotations

import argparse, json, os, pathlib

# The agent judges `ocr_text` against the image, so a truncated excerpt is read as
# missing content and inflates "partial" verdicts. Cap high enough to cover the real
# distribution (median ~1.2k chars, tail to ~8k), and flag truncation explicitly on the
# rare record that exceeds it so the agent can discount rather than penalise it.
EXCERPT = 9000


def main() -> int:
    ap = argparse.ArgumentParser(description="Build classification batches for the agent path")
    ap.add_argument("--ocr", required=True)
    ap.add_argument("--docs", help="optional docs.jsonl to include")
    ap.add_argument("--out-dir", default=os.path.join(os.environ.get("RG_OUT") or "out", "batches"))
    ap.add_argument("--min-bytes", type=int, default=0, help="skip files smaller than this")
    ap.add_argument("--size", type=int, default=12, help="images per batch")
    ap.add_argument("--skip-done", help="existing classify jsonl; already-done paths are skipped")
    args = ap.parse_args()

    done = set()
    if args.skip_done and pathlib.Path(args.skip_done).exists():
        for line in pathlib.Path(args.skip_done).read_text().split("\n"):
            if line.strip():
                done.add(json.loads(line)["path"])

    rows = []
    for line in pathlib.Path(args.ocr).read_text().split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        p = pathlib.Path(r["path"])
        if r.get("chars", 0) <= 0 or str(p) in done or not p.exists():
            continue
        size = p.stat().st_size
        if size < args.min_bytes:
            continue
        rows.append({
            "path": str(p),
            "bytes": size,
            "ocr_conf": r.get("mean_conf", 0),
            "ocr_chars": r.get("chars", 0),
            "ocr_text": r.get("text", "")[:EXCERPT],
            "ocr_truncated": len(r.get("text", "")) > EXCERPT,
        })

    rows.sort(key=lambda r: -r["bytes"])   # biggest first: most reclaimable space per pass
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("batch_*.json"):
        old.unlink()

    batches = [rows[i:i + args.size] for i in range(0, len(rows), args.size)]
    for i, b in enumerate(batches, 1):
        (out / f"batch_{i:02d}.json").write_text(json.dumps(b, indent=1, ensure_ascii=False))
    print(f"{len(rows)} images -> {len(batches)} batches of <= {args.size}  "
          f"({sum(r['bytes'] for r in rows)/1e9:.2f} GB){'  [skipped %d done]' % len(done) if done else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
