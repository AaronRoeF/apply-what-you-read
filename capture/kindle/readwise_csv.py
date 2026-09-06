"""capture/kindle/readwise_csv.py — parse a Readwise CSV export.

Header-driven: columns are found by name (with aliases), never by position, and a missing
required column is a loud error that lists the headers actually present. Readwise keeps colour
and the typed note; it carries no page number, and the Amazon id is empty for books that were
not bought on Kindle — which is why the record schema synthesises one.

Columns seen in real exports: Highlight, Book Title, Book Author, Amazon Book ID, Note, Color,
Tags, Location Type, Location, Highlighted at, Document tags. Send a real export if yours
differs; the alias table below is where a new spelling goes.
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict

from .schema import Annotation, Book, EmptyParseError, annotation_id, loc_int, norm_color, synthetic_asin

ALIASES = {
    "highlight": ["Highlight", "Highlight text", "Text"],
    "title": ["Book Title", "Title"],
    "author": ["Book Author", "Author"],
    "asin": ["Amazon Book ID", "ASIN"],
    "note": ["Note", "Notes"],
    "color": ["Color", "Colour"],
    "location": ["Location", "Loc"],
    "location_type": ["Location Type"],
    "highlighted_at": ["Highlighted at", "Highlighted At", "Date"],
}
REQUIRED = ("highlight", "title")


def _resolve(headers: list[str]) -> dict[str, str]:
    lower = {h.strip().lower(): h for h in headers}
    found = {}
    for key, names in ALIASES.items():
        for n in names:
            if n.lower() in lower:
                found[key] = lower[n.lower()]
                break
    missing = [k for k in REQUIRED if k not in found]
    if missing:
        raise ValueError(f"Readwise CSV is missing required column(s) {missing}; headers present: {headers}. "
                         f"Add the spelling to ALIASES in capture/kindle/readwise_csv.py.")
    return found


def parse_readwise_csv(text: str) -> list[Book]:
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
    if not rows:
        if text.strip().count("\n") >= 1:
            raise EmptyParseError("the CSV has a header and no data rows — nothing to import")
        return []
    col = _resolve(list(rows[0].keys()))
    g = lambda r, k: (r.get(col[k]) or "").strip() if k in col else ""
    by_book: dict[tuple[str, str, str], list[Annotation]] = defaultdict(list)
    for r in rows:
        text_ = g(r, "highlight")
        if not text_:
            continue
        title, author, asin = g(r, "title"), g(r, "author"), g(r, "asin")
        loc = str(loc_int(g(r, "location")) or "")
        by_book[(asin, title, author)].append(Annotation(
            id=annotation_id("kh", title, loc, text_), text=text_, note=g(r, "note"),
            color=norm_color(g(r, "color") or None), page=None, location=loc, location_end=loc,
            added_on=g(r, "highlighted_at") or None, kind="highlight"))
    books = [Book(asin or synthetic_asin(title, author), title, author, anns)
             for (asin, title, author), anns in by_book.items()]
    if not books:
        raise EmptyParseError("rows were read but every Highlight cell was empty")
    return books


def parse_readwise_csv_file(path) -> list[Book]:
    from pathlib import Path
    return parse_readwise_csv(Path(path).read_text(encoding="utf-8", errors="replace"))
