#!/usr/bin/env python3
"""Collapse byte-identical duplicate attachments, repointing note embeds at the keeper.

Deduplication is the cheapest reclaim in this pipeline: no model, no judgement, no
information loss -- a duplicate is the *same bytes*, so keeping one copy keeps
everything. It should run BEFORE classification, since every duplicate classified is a
wasted pass.

The non-trivial part is not finding duplicates, it is not breaking the vault. Obsidian
embeds resolve by bare filename (`![[Foo 1.jpg]]`), so moving a file silently breaks
every note that referenced it. This rewrites those embeds to the keeper first, then
moves, then verifies that zero embeds dangle.

Nothing is deleted. Duplicates move to a holding directory; reversing the run is a
`mv` back.

    python3 dedupe.py --vault ~/Vault --notes-dir apple-notes            # dry run
    python3 dedupe.py --vault ~/Vault --notes-dir apple-notes --apply
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

EMBED_RE = re.compile(r"!\[\[([^\]|]+?)(\|[^\]]*)?\]\]")


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def pick_keeper(paths: list[Path]) -> Path:
    """Deterministic: shortest name wins, ties broken alphabetically.

    Apple's duplicate convention appends " 1", " 2" to the stem, so the shortest name is
    reliably the original rather than a copy.
    """
    return sorted(paths, key=lambda p: (len(p.name), p.name))[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Collapse byte-identical attachments")
    ap.add_argument("--vault", required=True, type=Path)
    ap.add_argument("--notes-dir", default="apple-notes")
    ap.add_argument("--attach-dir", default="apple-notes/_attachments")
    ap.add_argument("--holding", default="apple-notes/_purged/duplicates")
    ap.add_argument("--apply", action="store_true", help="actually move files (default: dry run)")
    ap.add_argument("--report", help="write a JSON record of what was collapsed")
    args = ap.parse_args()

    vault = args.vault.expanduser()
    attach = vault / args.attach_dir
    notes = vault / args.notes_dir
    if not attach.is_dir():
        sys.exit(f"attachment dir not found: {attach}")

    by_hash: dict[str, list[Path]] = collections.defaultdict(list)
    for p in sorted(attach.rglob("*")):
        if p.is_file():
            by_hash[sha256(p)].append(p)

    groups = {h: ps for h, ps in by_hash.items() if len(ps) > 1}
    rename: dict[str, str] = {}      # duplicate filename -> keeper filename
    to_move: list[tuple[Path, Path]] = []
    reclaimed = 0
    holding = vault / args.holding

    for h, paths in groups.items():
        keeper = pick_keeper(paths)
        for dup in paths:
            if dup == keeper:
                continue
            rename[dup.name] = keeper.name
            to_move.append((dup, holding / dup.name))
            reclaimed += dup.stat().st_size

    # --- rewrite embeds BEFORE moving, so nothing dangles mid-run ---
    edits = 0
    touched: list[str] = []
    for md in sorted(notes.rglob("*.md")):
        if holding in md.parents:
            continue
        text = md.read_text(errors="replace")

        def swap(m: re.Match) -> str:
            nonlocal edits
            target, alias = m.group(1), m.group(2) or ""
            new = rename.get(target)
            if new and new != target:
                edits += 1
                return f"![[{new}{alias}]]"
            return m.group(0)

        updated = EMBED_RE.sub(swap, text)
        if updated != text:
            touched.append(str(md.relative_to(vault)))
            if args.apply:
                md.write_text(updated)

    print(f"  duplicate groups     : {len(groups)}")
    print(f"  redundant copies     : {len(to_move)}")
    print(f"  bytes reclaimed      : {reclaimed / 1e9:.2f} GB")
    print(f"  note embeds repointed: {edits} across {len(touched)} notes")

    if not args.apply:
        print("\n  DRY RUN — nothing moved. Re-run with --apply.")
        return 0

    holding.mkdir(parents=True, exist_ok=True)
    moved = 0
    for src, dst in to_move:
        if not src.exists():
            continue
        if dst.exists():                       # same basename from another subdir
            dst = dst.with_name(f"{dst.stem}__{sha256(src)[:8]}{dst.suffix}")
        shutil.move(str(src), str(dst))
        moved += 1
    print(f"  moved                : {moved} files -> {holding.relative_to(vault)}")

    # --- verify nothing dangles ---
    on_disk = {p.name for p in attach.rglob("*") if p.is_file()}
    broken = []
    for md in sorted(notes.rglob("*.md")):
        if holding in md.parents:
            continue
        for m in EMBED_RE.finditer(md.read_text(errors="replace")):
            if m.group(1) not in on_disk:
                broken.append((str(md.relative_to(vault)), m.group(1)))
    print(f"  broken embeds after  : {len(broken)}")
    for note, target in broken[:5]:
        print(f"      {note} -> {target}")

    if args.report:
        Path(args.report).write_text(json.dumps({
            "groups": len(groups), "moved": moved, "bytes_reclaimed": reclaimed,
            "embeds_repointed": edits, "notes_touched": touched,
            "broken_after": broken,
            "renames": rename,
        }, indent=1))
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
