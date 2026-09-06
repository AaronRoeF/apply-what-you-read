"""The fixture is the only book text in the repository, and it may only be public-domain text
whose provenance is stated on the file. These tests are the enforcement:

  * every markdown / HTML fixture file carries the source marker (eBook #2680)
  * every highlight span in every generated input is a verbatim (whitespace-normalised)
    substring of excerpts.txt — nothing typed from memory of the book
  * regeneration is byte-identical (text) and pixel-identical (PNG), so a hand edit to a
    generated file cannot survive
"""
from __future__ import annotations

import csv
import html
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FX = ROOT / "fixtures" / "meditations"
MARK = "#2680"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@pytest.fixture(scope="module")
def excerpts() -> str:
    raw = (FX / "excerpts.txt").read_text(encoding="utf-8")
    first, _, body = raw.partition("\n")
    assert first.startswith("# SOURCE:"), "excerpts.txt must open with the SOURCE line"
    assert MARK in first and "gutenberg.org/ebooks/2680" in first
    return norm(body)


def test_markdown_and_html_carry_the_source_marker():
    files = sorted(FX.rglob("*.md")) + sorted(FX.rglob("*.html"))
    assert len(files) >= 6, "expected SOURCE.md, notes.md, three journal notes, reader-context, the HTML export"
    for f in files:
        assert MARK in f.read_text(encoding="utf-8"), f"{f.relative_to(FX)} lacks the {MARK} source marker"


def test_expected_json_spans_are_verbatim_excerpts(excerpts):
    doc = json.loads((FX / "expected" / "kindle-highlights.json").read_text(encoding="utf-8"))
    assert doc["source"] == "fixture"
    book = doc["books"][0]
    assert book["n"] == len(book["annotations"]) == 35
    assert book["asin"].startswith("x"), "the fixture has no real Amazon id; asin must be synthetic"
    for a in book["annotations"]:
        assert norm(a["text"]) in excerpts, a["id"]
        assert a["note"] is not None and a["location"], a["id"]


def _clipping_records(path: pathlib.Path):
    raw = path.read_bytes().decode("utf-8-sig")
    assert path.read_bytes()[:3] == b"\xef\xbb\xbf", "My Clippings.txt starts with a UTF-8 BOM on a real device"
    assert "\r\n" in raw, "device files are CRLF"
    for rec in raw.split("=========="):
        rec = rec.replace("\r\n", "\n").strip("\n")
        if not rec.strip():
            continue
        lines = rec.split("\n")
        yield lines[0], lines[1], "\n".join(lines[3:])


def test_clippings_highlight_bodies_are_verbatim_excerpts(excerpts):
    recs = list(_clipping_records(FX / "clippings" / "My Clippings.txt"))
    kinds = [meta.split()[2] for _, meta, _ in recs]
    assert kinds.count("Highlight") == 40 and kinds.count("Note") == 5 and kinds.count("Bookmark") == 2
    pageless = [meta for _, meta, _ in recs if " at location " in meta]
    assert len(pageless) == 7, "page-less records are written in the older 'at location' form (6 spans + 1 superseded short)"
    assert all("on page" not in m for m in pageless)
    for title, meta, body in recs:
        assert title == "Meditations (Marcus Aurelius)"
        if "Highlight" in meta:
            assert norm(body) in excerpts, meta


def test_html_export_highlights_are_verbatim_excerpts(excerpts):
    doc = (FX / "export-html" / "meditations.html").read_text(encoding="utf-8")
    pairs = re.findall(r'<div class="noteHeading">(.*?)</div>\s*<div class="noteText">(.*?)</div>', doc, re.S)
    highlights = [html.unescape(t) for h, t in pairs if h.startswith("Highlight")]
    notes = [t for h, t in pairs if h.startswith("Note")]
    assert len(highlights) == 35 and len(notes) == 5
    for t in highlights:
        assert norm(t) in excerpts
    assert doc.count('<div class="sectionHeading">') == 3


def test_readwise_rows_are_verbatim_excerpts(excerpts):
    with (FX / "readwise" / "highlights.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 35
    assert "Highlight" in rows[0] and "Book Title" in rows[0] and "Location" in rows[0]
    for r in rows:
        assert norm(r["Highlight"]) in excerpts
        assert r["Amazon Book ID"] == "", "the fixture must exercise the synthetic-asin path"


def test_ocr_sidecars_are_verbatim_excerpts(excerpts):
    sidecars = sorted((FX / "pages" / "meditations").glob("page-*.png.ocr.txt"))
    assert len(sidecars) == 5
    for s in sidecars:
        assert norm(s.read_text(encoding="utf-8")) in excerpts, s.name


def test_regeneration_is_identical():
    pytest.importorskip("PIL")
    r = subprocess.run([sys.executable, str(FX / "gen_fixture.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
