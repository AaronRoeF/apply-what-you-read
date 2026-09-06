"""capture/kindle/schema.py — the ONE record shape every Kindle on-ramp emits.

Three parsers (My Clippings.txt, the app's "Export Notes" HTML, a Readwise CSV) and the
reference crawler all normalise to the same two records, and one writer turns them into
`kindle-highlights.json` — the file `corpus/merge_corpus.py` reads. Keys and types below are
the merge step's contract, measured from a real crawl artifact; do not rename them.

Per book:        asin (str, never null — synthesised when the source has none), title,
                 author, n (== len(annotations)), pageRange ([min, max] of integer locations),
                 annotations (list)
Per annotation:  id (provider-stable or synthesised; the dedupe key across re-runs),
                 color (Title-case provider name, or null), page (str or null — many
                 sources carry no page), location (str, always present), text, note ("" when
                 absent — never null)

Two rules this module enforces so no parser has to remember them:
  * `note` is an empty string when absent. Downstream tests `if a.get("note")`.
  * `page` is None when absent. A schema that made page mandatory would drop the ~60% of
    annotations that carry only a location (docs/02-KINDLE.md).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, field

# Colour vocabulary as the crawl emitted it (Title case). Parsers call norm_color().
COLORS = ("Yellow", "Pink", "Aqua", "Orange", "Blue")
_COLOR_ALIASES = {"cyan": "Aqua", "teal": "Aqua", "red": "Pink", "rose": "Pink"}


def norm_color(raw: str | None) -> str | None:
    """'yellow' -> 'Yellow'; unknown names pass through Title-cased; empty -> None."""
    if raw is None:
        return None
    # A colour is a word. A provider cell can hold anything (a Readwise export carried newlines and
    # a planted YAML key in review), so keep letters and spaces only, one line, bounded.
    s = re.sub(r"\s+", " ", re.sub(r"[^a-z ]+", " ", str(raw).lower())).strip()[:24].strip()
    if not s:
        return None
    s = _COLOR_ALIASES.get(s, s)
    return s.title()


def kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def synthetic_asin(title: str, author: str) -> str:
    """A stable stand-in when the source carries no Amazon id. Prefixed 'x' so it can never
    collide with a real ASIN (which start with B or a digit)."""
    h = hashlib.sha1(f"{_norm_key(title)}|{_norm_key(author)}".encode("utf-8")).hexdigest()
    return "x" + h[:9]


def annotation_id(source: str, title: str, location: str, text: str) -> str:
    """Stable id for sources that have none. Same span at the same place -> same id, so
    re-parsing dedupes instead of duplicating."""
    h = hashlib.sha1(f"{_norm_key(title)}|{location}|{_norm_key(text)}".encode("utf-8")).hexdigest()
    return f"{source}:{h[:16]}"


def loc_int(location: str | None) -> int | None:
    """'123-125' -> 123; '  4,512' -> 4512; None/'' -> None."""
    if not location:
        return None
    m = re.match(r"\s*([\d,]+)", str(location))
    if not m:
        return None
    digits = m.group(1).replace(",", "")
    if len(digits) > 12:   # no book has a 13-digit location; int() of a huge string is a crash, not a value
        return None
    return int(digits)


@dataclass
class Annotation:
    id: str
    text: str
    note: str = ""
    color: str | None = None
    page: str | None = None
    location: str = ""
    location_end: str | None = None   # end of a range when the source gives one (not emitted)
    added_on: str | None = None       # ISO 8601 when known (not emitted; used for ordering)
    kind: str = "highlight"           # "highlight" | "note" (a typed note with no highlight)

    def to_record(self) -> dict:
        return {
            "id": self.id,
            "color": self.color,
            "page": self.page if self.page not in ("", None) else None,
            "location": str(self.location or ""),
            "text": self.text,
            "note": self.note or "",
        }


@dataclass
class Book:
    asin: str
    title: str
    author: str
    annotations: list[Annotation] = field(default_factory=list)

    def page_range(self) -> list[int]:
        locs = [v for v in (loc_int(a.location) for a in self.annotations) if v is not None]
        return [min(locs), max(locs)] if locs else [0, 0]

    def to_record(self) -> dict:
        return {
            "asin": self.asin or synthetic_asin(self.title, self.author),
            "title": self.title,
            "author": self.author,
            "n": len(self.annotations),
            "pageRange": self.page_range(),
            "annotations": [a.to_record() for a in self.annotations],
        }


CRAWL_TS_FORMAT = "%m/%d/%Y %H:%M:%S"   # what the crawl wrote; kept for shape parity


def to_kindle_json(books: list[Book], source: str, errors: list | None = None,
                   crawled_at: str | None = None) -> dict:
    """The full kindle-highlights.json document. `source` names the on-ramp
    (clippings | notebook_html | readwise_csv | crawl | fixture) — an extra key merge_corpus
    ignores, so a reader can tell which path produced the file."""
    recs = [b.to_record() for b in books]
    return {
        "crawled_at": crawled_at or _dt.datetime.now().strftime(CRAWL_TS_FORMAT),
        "source": source,
        "account_books": len(recs),
        "books_with_highlights": sum(1 for r in recs if r["n"] > 0),
        "total_annotations": sum(r["n"] for r in recs),
        "errors": list(errors or []),
        "books": recs,
    }


def write_kindle_json(path: str | pathlib.Path, doc: dict) -> pathlib.Path:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p


def load_kindle_json(path: str | pathlib.Path) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def merge_books(*groups: list[Book]) -> list[Book]:
    """Merge several parses (e.g. clippings + Readwise), deduping annotations by id.

    Books are matched by normalised title + author, NOT by asin: a Readwise export carries the
    real Amazon id while the device file and the app export never do (they get a synthetic
    one), so keying on asin would land the same book twice. When any source supplies a real
    id, the merged book keeps it. First occurrence wins; order is preserved."""
    out: dict[str, Book] = {}
    for group in groups:
        for b in group:
            key = f"{_norm_key(b.title)}|{_norm_key(b.author)}"
            if key not in out:
                out[key] = Book(b.asin or synthetic_asin(b.title, b.author), b.title, b.author, [])
            elif b.asin and not b.asin.startswith("x") and out[key].asin.startswith("x"):
                out[key].asin = b.asin          # a real id beats a synthetic one
            seen = {a.id for a in out[key].annotations}
            for a in b.annotations:
                if a.id not in seen:
                    out[key].annotations.append(a)
                    seen.add(a.id)
    return list(out.values())


class EmptyParseError(RuntimeError):
    """Raised when an input is non-empty but yielded zero records. The null result and the
    correct result are the same value for this class of program, so an empty parse of real
    input must be an ERROR, never a clean exit (docs/02-KINDLE.md)."""
