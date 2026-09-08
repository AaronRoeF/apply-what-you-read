#!/usr/bin/env python3
"""Merge photographed page OCR with Kindle highlight spans into one file per book.

WHY THIS EXISTS: the photographed pages are a *biased sample* of what the reader marked --
the reader photographed some of what they highlighted, not all of it. Distillations built on
photos alone produced "the reader never engaged with chapter N" findings that the Kindle data
falsifies outright (Book A: 0 photographed pages of one chapter, 22
Kindle highlights on that chapter). Absence of a photo is not absence of interest, and
any analysis that treats it as such will keep inventing gaps that aren't there.

Kindle gives span-level truth (exact sentence, colour, page/location, typed note).
Photos give what Kindle cannot: pen marks, marginalia, handwritten worksheets, and
books never read on Kindle. Neither is a superset. The merge is the corpus.
"""
import json, os, pathlib, re, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]   # repo root; out/ lives here (RG_OUT overrides)
BASE = ROOT
OUT = pathlib.Path(os.environ.get("RG_OUT") or str(ROOT / "out"))   # empty RG_OUT must not mean cwd
DEST = OUT / "merged"

def norm(s):
    s = re.split(r"[:(]", s.lower())[0]
    s = re.sub(r"^(the|a|an)\s+", "", s.strip())
    return re.sub(r"[^a-z0-9]+", "", s)


def match(title, kin):
    """The Kindle record for a title, or None. `kin` is the index main() builds; it used to be a
    module global, which is part of why importing this file did work rather than offering it."""
    n = norm(title)
    if n in kin:
        return kin[n]
    for k, v in kin.items():
        if k.startswith(n[:14]) or n.startswith(k[:14]):
            return v
    return None

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "book-" + __import__("hashlib").sha1(s.encode("utf-8")).hexdigest()[:8]

def disambiguate(rows):
    """Give every row a unique slug, keeping subtitles only where they are needed.

    Titles are truncated at the first `:` so that `Book: A Subtitle` and `Book` collapse to
    one work. That is right almost always and catastrophic occasionally: `A Book:
    The Subtitle` and `A Book: A Summary of That Book` (a third-party summary) are DIFFERENT works with different ASINs, and collapsing
    them meant the second write clobbered the first -- 2 highlights gone, and a manifest
    claiming 88 books over a directory holding 87. Nothing errored.

    Collisions are rare, so pay for the subtitle only when one occurs.
    """
    seen = collections.Counter(slug(r[0]) for r in rows)
    out, used = [], set()
    for title, notes, pages, k in rows:
        base = slug(title)
        if seen[base] > 1:
            full = (k or {}).get("title") or title
            cand = slug(full)
            if cand in used or cand == base:          # subtitle did not separate them
                cand = f"{base}-{slug(str((k or {}).get('asin') or 'x'))}"   # a provider id is data; it lands in a filename
            title, base = full, cand
        used.add(base)
        out.append((title, base, notes, pages, k))
    return out

def main() -> int:
    """Everything below used to run at import.

    That is a real defect and not a style point: `from corpus.merge_corpus import disambiguate`
    — which a test does, for one pure helper — deleted every file in out/merged and then raised
    if the Kindle export was absent. On a clean clone the suite failed three tests before the
    quickstart had ever run, and CI runs the tests first. A module you can import is a module
    that can be tested; a module that acts on import is a trap with a helper in it."""
    kindle = json.loads((OUT / "kindle-highlights.json").read_text(encoding="utf-8"))


    kin = {}
    for b in kindle["books"]:
        kin[norm(b["title"])] = b


    DEST.mkdir(exist_ok=True)
    for f in DEST.glob("*"): f.unlink()

    rows = []
    seen_kindle = set()
    for cf in sorted((OUT / "bookcorpus").glob("*.json")):
        c = json.loads(cf.read_text(encoding="utf-8"))
        k = match(c["book"], kin)
        if k: seen_kindle.add(k["asin"])
        rows.append((c["book"], c.get("notes", []), c["pages"], k))

    # Kindle books with no photographed counterpart are still books.
    for b in kindle["books"]:
        # `n >= 25` dropped 44 Kindle-only books holding 214 highlights and -- the part that
        # actually hurt -- 20 of the corpus's 44 typed notes, including Book C (9,
        # the densest note-taking anywhere in the library) and Book B (6). A
        # threshold tuned on highlight VOLUME silently discarded the highest-value signal,
        # because the two are uncorrelated. No volume floor: if the reader marked it, it is in.
        if b["asin"] not in seen_kindle and b["n"] >= 1:
            rows.append((re.split(r"[:(]", b["title"])[0].strip(), [], [], b))




    manifest = []
    for title, s_lug, notes, pages, k in disambiguate(rows):
        hl = k["annotations"] if k else []
        # Threshold was `kindle < 10 AND photos < 5`, which silently dropped books that have
        # real content in both channels but not much in either -- Book D
        # (9 highlights + 3 photographed pages) vanished, and its books/ node was left behind
        # pointing at nothing. Include anything with any Kindle layer or a real photo set.
        if not hl and len(pages) < 3:
            continue
        s = s_lug
        rec = {"book": title, "asin": k["asin"] if k else None,
               "author": (k["author"] if k else None), "source_notes": notes,
               "kindle_highlights": hl, "photo_pages": pages}
        (DEST / f"{s}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")

        col = collections.Counter(a["color"] for a in hl)
        colstr = ", ".join(f"{c}:{n}" for c, n in col.most_common() if c)
        md = [f"# {title}", ""]
        if k: md.append(f"*{k.get('author') or ''}* · ASIN {k['asin']}")
        md += ["",
            f"**{len(hl)} Kindle highlights**" + (f" ({colstr})" if colstr else "") + " · "
            f"**{len(pages)} photographed pages** ({sum(1 for p in pages if p.get('catalogued'))} catalogued)",
            "", "> Two channels, neither a superset of the other: a zero in either channel means nothing "
            "was captured there, never that the reader did not engage. Colour is counted, not "
            "interpreted — it means nothing until the reader declares a colour key.", ""]
        if hl:
            md += ["---", "", "## Kindle highlights (span-level, exact text)", ""]
            for a in hl:
                loc = f"p{a['page']}" if a.get("page") and a["page"] not in ("0", None) else f"loc{a.get('location')}"
                md.append(f"- **[{a.get('color') or 'none'} · {loc}]** {a['text']}")
                if a.get("note"):
                    md.append(f"  - ✍️ **READER NOTE:** {a['note']}")
            md.append("")
        if pages:
            md += ["---", "", "## Photographed pages (OCR + catalogued marks)", ""]
            for i, p in enumerate(pages, 1):
                tag = ("marks=" + ",".join(p.get("marks") or []) + " colors=" + ",".join(p.get("colors") or [])
                       if p.get("catalogued") else "NOT CATALOGUED — no mark data extracted; "
                       "absence here means unassessed, NOT unmarked")
                md += [f"### photo page {i} — {tag}", ""]
                if p.get("gist"): md += [f"*gist:* {p['gist']}", ""]
                if p.get("ann"):  md += [f"*annotations:* {p['ann']}", ""]
                md += ["```", (p.get("text") or "").strip(), "```", ""]
        (DEST / f"{s}.md").write_text("\n".join(md), encoding="utf-8")
        manifest.append({"slug": s, "book": title, "kindle": len(hl), "photos": len(pages),
                         "notes": sum(1 for a in hl if a.get("note")),
                         "nonyellow": sum(1 for a in hl if a.get("color") and a["color"] != "Yellow")})

    manifest.sort(key=lambda r: -(r["kindle"] + r["photos"] * 3))
    (DEST / "_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{'BOOK':<44}{'kindle':>7}{'photo':>6}{'note':>5}{'≠yel':>5}")
    for r in manifest:
        print(f"{r['book'][:44]:<44}{r['kindle']:>7}{r['photos']:>6}{r['notes']:>5}{r['nonyellow']:>5}")
    print(f"\n{len(manifest)} book(s) -> {DEST}/")

    return 0


if __name__ == "__main__":
    import sys
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip()); raise SystemExit(0)
    raise SystemExit(main())
