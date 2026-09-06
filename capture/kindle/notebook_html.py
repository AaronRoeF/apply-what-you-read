"""capture/kindle/notebook_html.py — parse the Kindle app's "Export Notes" HTML.

One book per file. Keeps colour and (when the edition has them) page numbers — the two things
`My Clippings.txt` loses. Structure, as the app writes it (all `div`s, colour in a `span`):

    <div class="bookTitle">Title</div>
    <div class="authors">Author</div>
    <div class="sectionHeading">Chapter</div>
    <div class="noteHeading">Highlight (<span class="highlight_yellow">yellow</span>) - Page 12 · Location 123</div>
    <div class="noteText">the selected text</div>
    <div class="noteHeading">Note - Page 12 · Location 123</div>
    <div class="noteText">the typed note</div>

A `Note` heading immediately following a highlight attaches to it. Standard library only.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from .schema import Annotation, Book, EmptyParseError, annotation_id, loc_int, norm_color, synthetic_asin

CAPTURE = {"bookTitle", "authors", "citation", "sectionHeading", "noteHeading", "noteText"}
HEADING_RE = re.compile(
    r"^(?P<kind>Highlight|Note)(?:\s*\((?P<color>[^)]*)\))?\s*-\s*"
    r"(?:Page (?P<page>[^\s·•]+)\s*[·•-]\s*)?Location (?P<loc>\d[\d,]*)"
)


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self._cls: str | None = None
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if self._cls is not None:
            if tag == "div":
                self._depth += 1
            return
        if tag == "div":
            cls = dict(attrs).get("class", "")
            if cls in CAPTURE:
                self._cls, self._depth, self._buf = cls, 0, []

    def handle_endtag(self, tag):
        if self._cls is None or tag != "div":
            return
        if self._depth:
            self._depth -= 1
            return
        self.items.append((self._cls, re.sub(r"\s+", " ", "".join(self._buf)).strip()))
        self._cls = None

    def handle_data(self, data):
        if self._cls is not None:
            self._buf.append(data)


def parse_notebook_html(html: str) -> Book:
    c = _Collector()
    c.feed(html)
    title = next((t for k, t in c.items if k == "bookTitle"), "")
    author = next((t for k, t in c.items if k == "authors"), "")
    anns: list[Annotation] = []
    pending: dict | None = None
    for kind, text in c.items:
        if kind == "noteHeading":
            m = HEADING_RE.match(text)
            pending = m.groupdict() if m else None
        elif kind == "noteText" and pending is not None:
            h = pending
            pending = None
            if h["kind"] == "Highlight":
                loc = str(loc_int(h["loc"]) or "")   # None (13+ digits) -> "", never the string "None"
                anns.append(Annotation(id=annotation_id("kh", title, loc, text), text=text, note="",
                                       color=norm_color(h["color"]), page=h["page"], location=loc,
                                       location_end=loc, kind="highlight"))
            elif anns and anns[-1].kind == "highlight":
                anns[-1].note = (anns[-1].note + "; " + text) if anns[-1].note else text
            else:
                loc = str(loc_int(h["loc"]) or "")   # None (13+ digits) -> "", never the string "None"
                anns.append(Annotation(id=annotation_id("kn", title, loc, text), text="", note=text,
                                       page=h["page"], location=loc, kind="note"))
    if html.strip() and not (title or anns):
        raise EmptyParseError("the HTML is not empty but no bookTitle / noteHeading / noteText divs were found — "
                              "is this really an Export Notes file? (selectors: bookTitle, noteHeading, noteText)")
    return Book(synthetic_asin(title, author), title, author, anns)


def parse_notebook_html_file(path) -> Book:
    from pathlib import Path
    return parse_notebook_html(Path(path).read_text(encoding="utf-8", errors="replace"))
