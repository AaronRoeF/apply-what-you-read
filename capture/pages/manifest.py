#!/usr/bin/env python3
"""capture/pages/manifest.py — the corpus manifest for photographed pages.

    python capture/pages/manifest.py --pages pages/ --out out/manifest.json

Input: one folder per book under `--pages`, holding the page photos and an optional sidecar:

    pages/<book-slug>/page-01.jpg …
    pages/<book-slug>/notes.md          optional; frontmatter title / author / asin,
                                        body = notes typed while reading

Output: `manifest.json` in the shape `corpus/build_bookcorpus.py` consumes — one record per
book folder (the "note"), with its images — plus the manifest's own `root`, so liveness can be
re-checked later against the folder that produced it, not against anyone's vault.

Two rules:
  THE FOLDER IS THE TITLE EVIDENCE. The book a page belongs to is the folder it sits in (or
  the sidecar's `title:`), never a guess from the image. A header-less page has no other
  claim to a title.
  BASENAMES ARE UNIQUE ACROSS THE CORPUS. Downstream stages key images by basename; two
  folders both holding `page-01.jpg` would silently merge two books. Refused, loudly.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

RASTER = {".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".gif", ".tiff", ".tif", ".bmp"}


def read_sidecar(path: pathlib.Path) -> tuple[dict, str]:
    """Frontmatter keys + body of notes.md (both may be empty)."""
    if not path.exists():
        return {}, ""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"\A---\n(.*?)\n---\n?(.*)\Z", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).split("\n"):
        k = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if k:
            fm[k.group(1)] = k.group(2).strip().strip('"')
    return fm, m.group(2)


def humanize(slug: str) -> str:
    return re.sub(r"[-_]+", " ", slug).strip().title()


def build(pages_root: pathlib.Path) -> dict:
    pages_root = pathlib.Path(pages_root).resolve()
    if not pages_root.is_dir():
        sys.exit(f"manifest: pages dir not found: {pages_root}")
    notes, seen = [], {}
    for folder in sorted(p for p in pages_root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        fm, body = read_sidecar(folder / "notes.md")
        images = []
        for f in sorted(folder.iterdir()):
            if not f.is_file() or f.suffix.lower() not in RASTER:
                continue
            if f.name in seen:
                sys.exit(f"manifest: REFUSED — duplicate image basename {f.name!r} in {folder.name}/ and "
                         f"{seen[f.name]}/ (downstream keys images by basename; rename one)")
            seen[f.name] = folder.name
            images.append({"name": f.name, "path": str(f.relative_to(pages_root)), "bytes": f.stat().st_size, "raster": True})
        if not images:
            continue
        title = fm.get("title") or humanize(folder.name)
        notes.append({
            "id": folder.name,
            "book": title,
            "author": fm.get("author", ""),
            "asin": fm.get("asin", ""),
            "path": str((folder / "notes.md").relative_to(pages_root)) if (folder / "notes.md").exists() else folder.name,
            "title": title,
            "folder": folder.name,
            "created": None,
            "modified": dt.datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds"),
            "words": len(body.split()),
            "chars": len(body),
            "images": images,
            "n_images": len(images),
            "links": [],
            "tags": [],
            "excerpt": " ".join(body.split())[:200],
        })
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "root": str(pages_root),
        "source": "pages",
        "stats": {
            "notes": len(notes),
            "notes_with_images": len(notes),
            "raster_images": sum(n["n_images"] for n in notes),
            "sidecars": sum(1 for n in notes if n["path"].endswith("notes.md")),
        },
        "broken_embeds": [],
        "orphan_files": [],
        "notes": notes,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pages", required=True, help="folder holding one sub-folder per book")
    ap.add_argument("--out", required=True, help="manifest JSON destination (usually $RG_OUT/manifest.json)")
    args = ap.parse_args(argv)
    man = build(pathlib.Path(args.pages))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in man["stats"].items():
        print(f"  {k:<18} {v}")
    if not man["notes"]:
        print("manifest: WARNING — no book folders with images found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
