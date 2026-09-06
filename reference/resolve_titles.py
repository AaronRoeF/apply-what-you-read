#!/usr/bin/env python3
"""Resolve book titles for headerless pages from their parent note.

E-ink readers crop the running header, so a photographed page often carries no title at
all -- an agent looking at the image alone correctly refuses to guess. But the page is
embedded in a note, and in this archive those notes are named after the book
("Book Notes/Book F 1.md" holds 100 images of Book F).

So the title is recoverable deterministically from note membership. No model, no guessing:
the strongest evidence is the container, not the pixels.
"""
from __future__ import annotations
import json, pathlib, re, collections

def canon(t: str) -> str:
    t = re.sub(r'\s*\d+$', '', (t or "").strip())          # "Book F 1" -> "Book F"
    t = re.sub(r'\s+', ' ', t).strip(' .,-')
    return t

man = json.loads(pathlib.Path("out/manifest.json").read_text())
# image basename -> parent note title, restricted to notes that look like book notes
img2note = {}
for n in man["notes"]:
    folder, title = n.get("folder", ""), n.get("title", "")
    # ONLY trust Book Notes membership. An earlier version also accepted any note holding
    # >=5 images, which mis-titled work decks ("Deck A", "Deck B", "a vendor survey")
    # as books. Page count is not evidence of book-ness; folder placement is.
    if "book notes" not in folder.lower():
        continue
    for im in n.get("images", []):
        img2note.setdefault(im["name"], canon(title))

filled = collections.Counter(); untouched = 0; total = 0
for f in sorted(pathlib.Path("out").glob("book_0*.jsonl")):
    out, changed = [], False
    for l in f.read_text().split("\n"):
        if not l.strip(): continue
        r = json.loads(l); total += 1
        if not (r.get("book") or "").strip():
            cand = img2note.get(pathlib.Path(r["path"]).name)
            if cand and len(cand) > 3 and not cand.lower().startswith(("image", "snapshot", "pasted")):
                r["book"] = cand; r["book_source"] = "parent-note"
                filled[cand] += 1; changed = True
            else:
                untouched += 1
        out.append(json.dumps(r, ensure_ascii=False))
    if changed:
        f.write_text("\n".join(out) + "\n")

print(f"  catalogued pages: {total}")
print(f"  titles filled from parent note: {sum(filled.values())}")
for b, c in filled.most_common(10):
    print(f"     {c:>3}  {b[:56]}")
print(f"  still untitled (genuinely not books, or unresolvable): {untouched}")
