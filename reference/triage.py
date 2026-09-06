#!/usr/bin/env python3
"""Build the corpus manifest: one record per imported note, plus the note<->image map.

This is the artifact downstream agents actually scan. An agent cannot read thousands of
notes and thousands of images to answer one question; it reads this file, then targets
its reads. Without it, every agent burns its context re-crawling the same corpus.

The Obsidian Apple Notes importer writes exactly one frontmatter field (`apple-notes-id`)
and preserves the original created/modified timestamps as filesystem birthtime/mtime --
not as YAML. This script reads them off `stat` and puts them where they can be queried.

    python3 triage.py --vault ~/Vault --notes-dir apple-notes --out out/manifest.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EMBED_RE = re.compile(r"!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z][\w/-]*)")
ID_RE = re.compile(r"^apple-notes-id:\s*(\S+)\s*$", re.M)
RASTER = {".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".gif", ".tiff", ".tif", ".bmp"}


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def build(vault: Path, notes_dir: str, attach_dir: str) -> dict:
    root = vault / notes_dir
    if not root.is_dir():
        sys.exit(f"notes dir not found: {root}")

    attach_root = vault / attach_dir
    files_by_name: dict[str, Path] = {}
    for f in attach_root.rglob("*"):
        if f.is_file():
            files_by_name.setdefault(f.name, f)

    notes, broken, used = [], [], Counter()
    for p in sorted(root.rglob("*.md")):
        if attach_root in p.parents:
            continue
        text = p.read_text(errors="replace")
        st = p.stat()
        embeds = EMBED_RE.findall(text)
        images = []
        for e in embeds:
            used[e] += 1
            tgt = files_by_name.get(e)
            if tgt is None:
                broken.append({"note": str(p.relative_to(vault)), "embed": e})
                continue
            images.append(
                {
                    "name": e,
                    "path": str(tgt.relative_to(vault)),
                    "bytes": tgt.stat().st_size,
                    "raster": tgt.suffix.lower() in RASTER,
                }
            )
        body = text.split("---", 2)[-1] if text.startswith("---") else text
        m = ID_RE.search(text)
        rel = p.relative_to(root)
        notes.append(
            {
                "id": m.group(1) if m else None,
                "path": str(p.relative_to(vault)),
                "title": p.stem,
                "folder": str(rel.parent) if str(rel.parent) != "." else "",
                "created": iso(getattr(st, "st_birthtime", st.st_ctime)),
                "modified": iso(st.st_mtime),
                "words": len(body.split()),
                "chars": len(body),
                "images": images,
                "n_images": len(images),
                "links": WIKILINK_RE.findall(text),
                "tags": sorted(set(TAG_RE.findall(text))),
                "excerpt": " ".join(body.split())[:200],
            }
        )

    orphans = [n for n in files_by_name if used[n] == 0]
    return {
        "generated": iso(datetime.now().timestamp()),
        "vault": str(vault),
        "notes_dir": notes_dir,
        "stats": {
            "notes": len(notes),
            "notes_without_id": sum(1 for n in notes if not n["id"]),
            "attachment_files": len(files_by_name),
            "embed_refs": sum(used.values()),
            "distinct_embeds": len(used),
            "broken_embeds": len(broken),
            "orphan_files": len(orphans),
            "notes_with_images": sum(1 for n in notes if n["n_images"]),
            "raster_images": sum(1 for n in notes for i in n["images"] if i["raster"]),
        },
        "broken_embeds": broken[:200],
        "orphan_files": sorted(orphans)[:200],
        "notes": notes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the imported-notes manifest")
    ap.add_argument("--vault", required=True, type=Path, help="Obsidian vault root")
    ap.add_argument("--notes-dir", default="apple-notes", help="import subdirectory, relative to vault")
    ap.add_argument("--attach-dir", default="apple-notes/_attachments", help="attachment dir, relative to vault")
    ap.add_argument("--out", required=True, help="manifest JSON destination")
    args = ap.parse_args()

    man = build(args.vault.expanduser(), args.notes_dir, args.attach_dir)
    Path(args.out).write_text(json.dumps(man, ensure_ascii=False, indent=1))
    s = man["stats"]
    for k, v in s.items():
        print(f"  {k:<22} {v}")
    if s["broken_embeds"]:
        print(f"\n  WARNING: {s['broken_embeds']} embeds resolve to no file", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
