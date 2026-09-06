#!/usr/bin/env python3
"""vault/build_nodes.py — one markdown node per book, generated from the merged corpus.

    python vault/build_nodes.py --vault /path/to/vault [--corpus out/merged] [--distill-dir DIR]

Reads every `<slug>.json` in the corpus directory (the output of corpus/merge_corpus.py) and
writes `<vault>/books/<slug>.md` with uniform frontmatter, so the whole library is one directory
of files any agent can grep. The vault can be an Obsidian vault or a plain folder.

Rules this builder enforces — each one is a defect that happened, not a preference:

  MEMBERSHIP IS DECIDED IN ONE PLACE. A book is a node iff it is in the corpus with at least one
  Kindle highlight or one photographed page. No second list.

  EMPTY CORPUS REFUSES. A missing or empty corpus directory would otherwise produce zero nodes and
  the orphan sweep would then move EVERY existing node aside. Refuse before the sweep.

  ORPHANS MOVE, NEVER DELETE. A node whose book left the corpus goes to `books/_orphaned/`,
  dated on collision. Git is the archive; the sweep is not.

  HAND-AUTHORED FIELDS SURVIVE. `related`, `outcome`, `applied_in`, `status` are carried from
  the existing node into the rebuilt one. `related:` is reserved for the Librarian; everything
  else in frontmatter belongs to this builder.

  NULL IS NOT EMPTY. `highlight_colors: null` / `marks: null` mean no page was ever catalogued;
  `[]` means catalogued and nothing found. Never collapse the two.

  WRITE ONLY ON CHANGE. Unchanged nodes keep their mtime, so "recently modified" stays meaningful.

  BASENAME COLLISIONS REFUSE. Wiki-style links resolve by basename across the whole vault; a
  second `<slug>.md` anywhere makes `[[slug]]` ambiguous. The colliding book is skipped, loudly,
  and the run exits non-zero — the other books are still written.

  THE DISTILLATION IS JOINED, NEVER WRITTEN. `<distill-dir>/distill-<slug>.md` is transcluded
  into the node body with its own frontmatter stripped; this builder never writes into that
  file, never adds a banner to it, and reports distillations that match no book slug.

  A NODE THAT CANNOT BE WRITTEN IS SPOOLED. If the vault is unwritable, the node lands in
  `$RG_OUT/spool/books/` with a loud line, and the run exits 3. Losing output silently is the
  failure this whole pipeline exists to prevent.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import re
import sys

PRESERVE = ("related", "outcome", "applied_in", "status")
ROOT = pathlib.Path(__file__).resolve().parents[1]


def kebab(s: str) -> str:
    """ASCII slug; a title with no ASCII letters (a non-Latin script) falls back to a stable hash
    instead of the empty string — two such books would otherwise both become `books/.md`."""
    import hashlib
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "book-" + hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def _synthetic_asin(title: str, author: str) -> str:
    """The stand-in id for a book with no provider id — the same function the Kindle parsers use
    (capture.kindle.schema.synthetic_asin), so a book seen later in a Kindle export keeps its id.
    No fallback: a checkout where capture/ is missing should fail here, loudly, not diverge ids."""
    import pathlib, sys
    root = str(pathlib.Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from capture.kindle.schema import synthetic_asin
    return synthetic_asin(title, author)


def _yaml_key(k) -> str:
    """A colour or mark name inside a flow list: letters, digits, space, - _ only, bounded. Names
    come from provider cells and catalogue output — data, which must not become a YAML line."""
    return re.sub(r"[^A-Za-z0-9_ -]+", "", str(k)).strip()[:32] or "unknown"


def yaml_str(s: str) -> str:
    """A double-quoted YAML scalar. JSON string syntax is valid YAML, so quotes, backslashes and
    control characters in a title cannot break the frontmatter."""
    return json.dumps(str(s), ensure_ascii=False)


def link_text(s: str) -> str:
    """Text safe inside [[...]]: no closing brackets, pipes, or newlines."""
    return re.sub(r"[\[\]|\r\n]+", " ", str(s)).strip()


def carry(path: pathlib.Path) -> dict[str, list[str]]:
    """Hand-authored frontmatter fields of an existing node, as raw lines (multi-line lists kept)."""
    if not path.exists():
        return {}
    m = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    if not m:
        return {}
    kept, cur = {}, None
    for line in m.group(1).split("\n"):
        key = re.match(r"([a-z_]+):(.*)$", line)
        if key:
            cur = key.group(1) if key.group(1) in PRESERVE else None
            if cur:
                kept[cur] = [line]
        elif cur and line.startswith((" ", "-", "\t")):
            kept[cur].append(line)
        else:
            cur = None
    # an empty `related: []` is the builder's own default, not a hand edit — drop it so it re-derives
    return {k: v for k, v in kept.items() if not (len(v) == 1 and v[0].strip().endswith(": []"))}


def collisions(vault: pathlib.Path, slug: str, target: pathlib.Path) -> list[pathlib.Path]:
    out = []
    for p in vault.rglob(f"{slug}.md"):
        if p == target or "_orphaned" in p.parts or ".git" in p.parts:
            continue
        out.append(p)
    return out


def render(rec: dict, keep: dict[str, list[str]], dbody: str, source: str) -> str:
    b, pages = rec["book"], rec.get("photo_pages", []) or []
    notes, kindle = rec.get("source_notes", []) or [], rec.get("kindle_highlights", []) or []
    kcolors = collections.Counter(a.get("color") for a in kindle if a.get("color"))
    knotes = sum(1 for a in kindle if a.get("note"))
    colors, marks, ann, ncat = collections.Counter(), collections.Counter(), 0, 0
    for p in pages:
        if not p.get("catalogued"):
            continue
        ncat += 1
        for k in (p.get("colors") or []):
            colors[k] += 1
        for k in (p.get("marks") or []):
            marks[k] += 1
        if p.get("ann"):
            ann += 1
    # Every node carries every key: a photo-only book has no provider id, so it gets the same
    # synthetic asin the Kindle parsers would give it, and an empty author rather than no key.
    asin = re.sub(r'[^A-Za-z0-9_-]', '', str(rec.get("asin") or "")) or _synthetic_asin(b, rec.get("author") or "")
    source = re.sub(r"[^A-Za-z0-9_.-]+", "", source) or "apply-what-you-read"
    fm = ["---", f"name: {yaml_str(b)}", "type: book", f"source: {source}", f"asin: {asin}",
          f"author: {yaml_str(rec.get('author') or '')}"]
    fm += [f"kindle_highlights: {len(kindle)}", f"typed_notes: {knotes}",
           f"kindle_colors: [{', '.join(f'{_yaml_key(k)}:{v}' for k, v in kcolors.most_common())}]",
           f"pages_captured: {len(pages)}", f"pages_catalogued: {ncat}", f"pages_annotated: {ann}",
           (f"highlight_colors: [{', '.join(f'{_yaml_key(k)}:{v}' for k, v in colors.most_common())}]" if ncat else "highlight_colors: null"),
           (f"marks: [{', '.join(f'{_yaml_key(k)}:{v}' for k, v in marks.most_common())}]" if ncat else "marks: null"),
           f"distilled: {'true' if dbody else 'false'}",
           "tags: [book, reading]"]
    fm += keep.get("related", ["related: []"])
    for k in PRESERVE:
        if k != "related" and k in keep:
            fm += keep[k]
    heading = re.sub(r"[\s\[\]|]+", " ", b).strip()   # hoisted: a backslash inside an f-string expression is a SyntaxError before 3.12
    fm += ["---", "", f"# {heading}", "", "## Source", ""]
    for n in notes:
        # A notes-app import has a real source note to link to; the folder-per-book input's
        # "note" IS the book, and a [[Book]] link there would resolve to this node itself.
        if n.get("title") and n["title"].strip().lower() != b.strip().lower():
            fm.append(f'- [[{link_text(n["title"])}]] — {n.get("n_images", 0)} pages captured')
        else:
            fm.append(f'- {n.get("n_images", 0)} photographed pages')
    fm += ["", f"**Kindle:** {len(kindle)} highlights"
              + (f" ({', '.join(f'{_yaml_key(k)} ×{v}' for k, v in kcolors.most_common())})" if kcolors else "")
              + (f" · **{knotes} typed note{'s' if knotes != 1 else ''}**" if knotes else "")
              + f" · **Photographed:** {len(pages)} pages ({ncat} catalogued)"]
    if colors:
        fm.append("**Highlight colours:** " + ", ".join(f"{_yaml_key(k)} ×{v}" for k, v in colors.most_common()))
    fm += ["", "---", ""]
    fm += [dbody.strip(), ""] if dbody else ["*Not yet distilled.* Run the distill skill against this book.", ""]
    return "\n".join(fm)


def build(corpus: pathlib.Path, vault: pathlib.Path, distill_dir: pathlib.Path | None = None,
          spool_dir: pathlib.Path | None = None, source: str = "apply-what-you-read") -> dict:
    corpus, vault = pathlib.Path(corpus), pathlib.Path(vault)
    distill_dir = pathlib.Path(distill_dir) if distill_dir else vault / "distill"
    spool_dir = pathlib.Path(spool_dir) if spool_dir else pathlib.Path(os.environ.get("RG_OUT", ROOT / "out")) / "spool"
    books = vault / "books"
    stats = {"written": 0, "kept": 0, "orphaned": 0, "collisions": 0, "spooled": 0, "stranded": 0, "skipped": 0}

    files = [f for f in sorted(corpus.glob("*.json")) if not f.name.startswith("_")]
    if not files:
        print(f"build_nodes: REFUSED — corpus empty or missing at {corpus} (refusing to orphan every node)", file=sys.stderr)
        stats["refused"] = True
        return stats

    try:
        books.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"build_nodes: vault not writable ({e}); nodes will be SPOOLED to {spool_dir}", file=sys.stderr)

    emitted, matched = set(), set()
    for cf in files:
        rec = json.loads(cf.read_text(encoding="utf-8"))
        pages, kindle = rec.get("photo_pages", []) or [], rec.get("kindle_highlights", []) or []
        if not pages and not kindle:
            stats["skipped"] += 1
            continue
        # The merged file's stem is the node's identity: the merge step already separated two works
        # that share a title into distinct stems (`foo` and `foo-b000real01`), and keying on the title
        # again would let the second silently overwrite the first — 2 written, 1 on disk, no error.
        slug = kebab(cf.stem)
        node = books / f"{slug}.md"
        if node in emitted:
            stats["collisions"] += 1
            print(f"build_nodes: COLLISION — {cf.name} maps to {node.name}, already written this run; not overwriting", file=sys.stderr)
            continue
        emitted.add(node)   # even when refused below, this node must not be swept as an orphan
        clash = collisions(vault, slug, node)
        if clash:
            stats["collisions"] += 1
            print(f"build_nodes: COLLISION — [[{slug}]] would be ambiguous; not writing {node.name}. "
                  f"Also at: {', '.join(str(c.relative_to(vault)) for c in clash)}", file=sys.stderr)
            continue
        keep = carry(node)
        dist = distill_dir / f"distill-{slug}.md"
        dtext = dist.read_text(encoding="utf-8") if dist.exists() else ""
        dbody = re.sub(r"\A---\n.*?\n---\n", "", dtext, flags=re.S) if dtext else ""
        if dtext:
            matched.add(dist.stem)
        content = render(rec, keep, dbody, source)
        try:
            if node.exists() and node.read_text(encoding="utf-8") == content:
                stats["kept"] += 1
            else:
                node.write_text(content, encoding="utf-8")
                stats["written"] += 1
        except OSError as e:
            spool_dir.joinpath("books").mkdir(parents=True, exist_ok=True)
            sp = spool_dir / "books" / node.name
            sp.write_text(content, encoding="utf-8")
            stats["spooled"] += 1
            print(f"build_nodes: SPOOLED {node.name} -> {sp} ({e})", file=sys.stderr)

    if books.is_dir():
        orphans = [f for f in books.glob("*.md") if f not in emitted]
        orphdir = books / "_orphaned"
        for f in orphans:
            orphdir.mkdir(exist_ok=True)
            stamp = dt.date.today().isoformat()
            dest, k = orphdir / f"{f.stem}.{stamp}{f.suffix}", 1
            while dest.exists():
                k += 1
                dest = orphdir / f"{f.stem}.{stamp}-{k}{f.suffix}"
            f.rename(dest)
            stats["orphaned"] += 1
            print(f"build_nodes: orphaned node -> {dest.relative_to(vault)}")
    if distill_dir.is_dir():
        stranded = sorted(f.stem for f in distill_dir.glob("distill-*.md") if f.stem not in matched)
        stats["stranded"] = len(stranded)
        for x in stranded:
            print(f"build_nodes: WARNING distillation matches no book slug and is invisible: {x}.md")
    print(f"build_nodes: {stats['written']} written, {stats['kept']} unchanged, {stats['orphaned']} orphaned, "
          f"{stats['collisions']} collisions, {stats['spooled']} spooled -> {books}")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault", default=os.environ.get("VAULT"), help="the vault root (env VAULT). Required.")
    ap.add_argument("--corpus", default=str(pathlib.Path(os.environ.get("RG_OUT", ROOT / "out")) / "merged"))
    ap.add_argument("--distill-dir", default=None, help="where distill-<slug>.md files live (default: <vault>/distill)")
    ap.add_argument("--source", default="apply-what-you-read", help="the `source:` frontmatter value")
    args = ap.parse_args(argv)
    if not args.vault:
        ap.error("--vault (or env VAULT) is required — this builder writes into your vault and will not guess where it is")
    stats = build(pathlib.Path(args.corpus), pathlib.Path(args.vault), args.distill_dir, source=args.source)
    if stats.get("refused"):
        return 2
    if stats["spooled"]:
        return 3
    if stats["collisions"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
