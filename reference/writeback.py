#!/usr/bin/env python3
"""Write recognised text and provenance into the imported notes.

This is the step that actually makes the vault agent-readable. Everything before it
produced data ABOUT the corpus; this puts that data where an agent reading the vault will
find it.

Three invariants, each learned the hard way:

1. APPLE'S HANDWRITING TEXT IS AUTHORITATIVE AND IS NEVER OVERWRITTEN. Apple Pencil notes
   are stroke data, and Apple's stroke recogniser beats image OCR badly on the same file
   (measured: Apple recovered a numbered list and clean technical terms that Vision
   mangled). The importer already placed that text in the note body. `Drawing*` embeds are
   therefore skipped entirely -- adding a Vision callout there would bury better text
   under worse.

2. IDEMPOTENT. Re-running must not duplicate callouts or corrupt frontmatter. Insertion is
   gated on a sentinel, so the script can be run repeatedly as classification data
   improves.

3. BODY TEXT IS NEVER REWRITTEN. Only frontmatter is replaced and callouts appended after
   embeds. The note's own content is not touched -- it is the irreplaceable part.

    python3 writeback.py --vault ~/Vault                 # dry run
    python3 writeback.py --vault ~/Vault --apply
"""
from __future__ import annotations

import argparse, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EMBED_RE = re.compile(r"!\[\[([^\]|]+?)(\|[^\]]*)?\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z][\w/-]*)")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SENTINEL = "[!ocr]"          # presence after an embed means we already wrote one


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def load_jsonl(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text().split("\n"):
            if line.strip():
                r = json.loads(line)
                out[Path(r["path"]).name] = r
    return out


def callout(name: str, rec: dict, cls: dict | None) -> str:
    """Collapsed callout: clean for a human, plain text on disk for grep and agents."""
    text = (rec.get("text") or "").strip()
    if not text:
        return ""
    conf = rec.get("mean_conf")
    kind = rec.get("kind", "image")
    bits = [f"{kind} · {len(text):,} chars"]
    if conf is not None:
        bits.append(f"confidence {conf:.2f}")
    if cls:
        if cls.get("ocr_verdict"):
            bits.append(f"reviewed: {cls['ocr_verdict']}")
        if cls.get("annotations"):
            bits.append("**annotated — image retained**")
    body = "\n".join("> " + l for l in text.splitlines())
    return f"\n> {SENTINEL}- Recognised text · {' · '.join(bits)}\n{body}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Write recognised text + provenance into notes")
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--notes-dir", default="apple-notes")
    ap.add_argument("--out-dir", default=None, help="dir holding ocr.jsonl / docs.jsonl / judged_v2.jsonl")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    vault = args.vault.expanduser()
    notes = vault / args.notes_dir
    out = Path(args.out_dir) if args.out_dir else Path("out")

    ocr = load_jsonl(out / "ocr.jsonl") | load_jsonl(out / "docs.jsonl")
    cls = load_jsonl(out / "judged_v2.jsonl")

    stats = Counter()
    changed = []
    for md in sorted(notes.rglob("*.md")):
        if "_purged" in md.parts or "_review" in md.parts:
            continue
        original = md.read_text(errors="replace")
        text = original
        stats["notes"] += 1

        fm_m = FM_RE.match(text)
        fm_raw = fm_m.group(1) if fm_m else ""
        body = text[fm_m.end():] if fm_m else text
        note_id = next((l.split(":", 1)[1].strip() for l in fm_raw.splitlines()
                        if l.startswith("apple-notes-id:")), None)

        # --- insert callouts after embeds that don't already have one ---
        pieces, last, n_img, n_ann, verdicts = [], 0, 0, 0, []
        for m in EMBED_RE.finditer(body):
            name = m.group(1)
            pieces.append(body[last:m.end()])
            last = m.end()
            rec, c = ocr.get(name), cls.get(name)
            if rec:
                n_img += 1
                if c and c.get("annotations"):
                    n_ann += 1
                if c and c.get("ocr_verdict"):
                    verdicts.append(c["ocr_verdict"])
            if name.startswith("Drawing"):
                stats["skipped_apple_drawings"] += 1
                continue                                    # invariant 1
            following = body[m.end():m.end() + 400]
            if SENTINEL in following:
                stats["callout_already_present"] += 1
                continue                                    # invariant 2
            if rec:
                block = callout(name, rec, c)
                if block:
                    pieces.append(block)
                    stats["callouts_added"] += 1
        pieces.append(body[last:])
        body = "".join(pieces)

        # --- frontmatter (replaced wholesale; body never touched) ---
        st = md.stat()
        rel = md.relative_to(notes)
        folder = str(rel.parent) if str(rel.parent) != "." else ""
        tags = sorted(set(TAG_RE.findall(body)))
        ocr_state = ("none" if n_img == 0 else
                     "apple-native" if all(EMBED_RE.findall(body)) and n_img == 0 else
                     "partial" if any(v in ("partial", "mismatch") for v in verdicts) else "full")
        fm = ["---"]
        if note_id:
            fm.append(f"apple-notes-id: {note_id}")
        fm += [
            "type: note",
            "source: apple-notes",
            f'folder: "{folder}"',
            f"created: {iso(getattr(st, 'st_birthtime', st.st_ctime))}",
            f"modified: {iso(st.st_mtime)}",
            f"imported: {__import__('datetime').date.today().isoformat()}",
            f"attachments: {n_img}",
            f"images_annotated: {n_ann}",
            f"ocr: {ocr_state}",
            f"words: {len(body.split())}",
            f"tags: [{', '.join(tags)}]",
            "related: []",          # RESERVED — the agent project fills this, not the importer
            "---",
        ]
        new = "\n".join(fm) + "\n" + body.lstrip("\n")
        if new != original:
            changed.append(md)
            if args.apply:
                # The importer preserved Apple's original created/modified dates as
                # birthtime/mtime -- the filesystem IS the provenance record. Writing the
                # file clobbers mtime, so restore it. Without this the script destroys the
                # very timestamps it just wrote into frontmatter, and each re-run stamps
                # every note with the time of the previous run.
                import os
                st_before = md.stat()
                md.write_text(new)
                os.utime(md, (st_before.st_atime, st_before.st_mtime))

    for k in ("notes", "callouts_added", "callout_already_present", "skipped_apple_drawings"):
        print(f"  {k:<26} {stats[k]}")
    print(f"  {'notes changed':<26} {len(changed)}")
    if not args.apply:
        print("\n  DRY RUN — nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
