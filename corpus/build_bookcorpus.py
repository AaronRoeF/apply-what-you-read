#!/usr/bin/env python3
"""Join OCR text + agent catalog enrichment into one JSON per book.

Membership rule (see the comment block below): folder membership alone was wrong
-- it silently dropped the three largest book notes in the vault.
"""
import json, os, pathlib, re, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]   # repo root; out/ lives here (RG_OUT overrides)
BASE = ROOT
OUT = pathlib.Path(os.environ.get("RG_OUT") or str(ROOT / "out"))   # empty RG_OUT must not mean cwd

ocr = {}
for l in (OUT / "ocr.jsonl").read_text(encoding="utf-8").split("\n"):
    if l.strip():
        r = json.loads(l); ocr[pathlib.Path(r["path"]).name] = r

cat = {}
for f in sorted(OUT.glob("book_0*.jsonl")):
    for l in f.read_text(encoding="utf-8").split("\n"):
        if l.strip():
            r = json.loads(l); cat[pathlib.Path(r["path"]).name] = r

man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))

# Where the manifest's note paths are relative to. A pages manifest records its own `root`;
# an older notes-app import recorded `vault`. Only as a last resort, the VAULT env.
LIVE_ROOT = pathlib.Path(man.get("root") or man.get("vault") or os.environ.get("VAULT") or ".")
BOOK_FOLDER = os.environ.get("RG_BOOK_FOLDER", "Book Notes")   # the notes folder whose membership marks a note as a book
MIN_PAGES = int(os.environ.get("RG_MIN_PAGES", "1"))           # books with fewer OCR'd pages are dropped (the reference corpus used 3)


def note_is_live(n):
    """Has this note survived since the snapshot that produced the manifest?

    `manifest.json` is a frozen record of a walk that already happened, and nothing
    re-checks it. A note the reader DELETES therefore keeps producing a book entry and a
    book node forever -- the deletion is real everywhere except here. It surfaced when a
    clipping the reader had removed kept reappearing as a book. A snapshot is evidence of
    the past, not a claim about the present.

    This lives here because this file owns membership. Putting it downstream would mean
    two files deciding what counts as a book, which is the bug that dropped the three
    largest sources in the corpus.
    """
    rel = n.get("path")
    return bool(rel) and (LIVE_ROOT / rel).exists()


def canon(t):
    t = re.sub(r"\s*\d+$", "", t.strip())
    t = re.sub(r'^[^\w"“]+', "", t).strip(' "“”')
    t = re.sub(r"\s*(by|By)\s+[A-Z].*$", "", t)
    return re.sub(r"\s+", " ", t).strip()


def strip_author(b):
    """`Some Title -- Author Name` -> `Some Title`.

    Catalog agents wrote the author inconsistently (three variants for one author
    alone), which fragments the join key. The em-dash suffix is the author every
    time, so cutting at it is safe and makes the variants collapse.
    """
    b = re.split(r"\s+[—–]\s+", b)[0]
    b = re.split(r"\s*:\s+", b)[0]
    return re.sub(r"\s+", " ", b).strip()


# Membership. `"Book Notes" in folder` was the whole rule and it was too tight:
# `Book D` (115 images), `Book C` (34) and `Book E`
# (21) all sit directly in `Archived Notes`, so the largest book corpus in
# the vault silently vanished from the rebuild. The earlier >=5-images heuristic
# was too loose in the other direction -- it promoted work decks to books.
# So: trust the catalog. An agent that read the page and named a book is
# evidence; a folder name is a guess. Fold in folder membership for notes the
# catalog never reached. A note that DECLARES its book (a pages manifest built from
# one-folder-per-book, or a sidecar's title:) is the strongest evidence of all.
def note_book(n):
    named = [strip_author(cat[im["name"]]["book"])
             for im in n.get("images", [])
             if im["name"] in cat and cat[im["name"]].get("book")]
    if len(named) >= 3:
        return collections.Counter(named).most_common(1)[0][0], "catalog"
    if n.get("book"):
        return n["book"].strip(), "declared"
    if BOOK_FOLDER in n.get("folder", ""):
        b = canon(n["title"])
        if len(b) >= 3:
            return b, "folder"
    return None, None


books = collections.defaultdict(lambda: {"pages": [], "chars": 0, "sources": set(), "notes": []})
deleted = []
for n in man["notes"]:
    if not note_is_live(n):
        deleted.append(n.get("title") or n.get("path"))
        continue
    b, how = note_book(n)
    if not b:
        continue
    books[b]["sources"].add(how)
    books[b]["notes"].append({"title": n["title"], "n_images": len(n.get("images", []))})
    for im in n.get("images", []):
        o = ocr.get(im["name"]); c = cat.get(im["name"], {})
        if not o or not o.get("text"):
            continue
        books[b]["pages"].append({
            "path": o["path"], "text": o["text"], "ocr_conf": o.get("mean_conf"),
            # null != empty. `[]` means catalogued and nothing found; `null` means
            # never assessed. Collapsing them makes an unexamined page look like a
            # clean one -- an agent reasonably read `marks: []` as a failed
            # extractor and reported a bug that did not exist.
            "catalogued": bool(c),
            "gist": c.get("gist") if c else None,
            "ann": c.get("annotations") if c else None,
            "colors": c.get("highlight_colors", []) if c else None,
            "marks": c.get("marks", []) if c else None})
        books[b]["chars"] += len(o["text"])

dest = OUT / "bookcorpus"
if dest.exists():
    for f in dest.glob("*.json"):
        f.unlink()  # stale files from an older membership rule are worse than absent ones
dest.mkdir(exist_ok=True)

print("  %-44s %5s %5s %10s  %s" % ("BOOK", "pgs", "cat", "chars", "via"))
tot_p = tot_c = 0
for b, rec in sorted(books.items(), key=lambda kv: -kv[1]["chars"]):
    if len(rec["pages"]) < MIN_PAGES:
        continue
    ncat = sum(1 for p in rec["pages"] if p["catalogued"])
    tot_p += len(rec["pages"]); tot_c += ncat
    slug = re.sub(r"[^a-z0-9]+", "-", b.lower()).strip("-") or "book-" + __import__("hashlib").sha1(b.encode("utf-8")).hexdigest()[:8]
    (dest / f"{slug}.json").write_text(json.dumps(
        {"book": b, "notes": rec["notes"], "pages": rec["pages"], "chars": rec["chars"]},
        indent=1, ensure_ascii=False), encoding="utf-8")
    print("  %-44s %5d %5d %10s  %s" % (
        b[:44], len(rec["pages"]), ncat, f'{rec["chars"]:,}', "+".join(sorted(rec["sources"]))))
print("  %-44s %5d %5d" % ("TOTAL", tot_p, tot_c))
if deleted:
    print(f"\n  {len(deleted)} source note(s) deleted from the vault since import; excluded:")
    for x in sorted(deleted)[:10]:
        print(f"    {x}")
