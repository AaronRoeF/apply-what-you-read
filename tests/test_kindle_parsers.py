"""The three Kindle on-ramps must produce the fixture's golden parse. Each format loses
something, and the tests say exactly what:
  * My Clippings.txt carries no colour            -> compared with colour nulled
  * Readwise CSV carries no page numbers          -> compared with page nulled
  * the app's HTML export keeps both              -> compared exactly
Plus the edge cases the fixture plants: superseded shorts, exact duplicates, page-less records,
note attachment, BOM/CRLF, the empty-parse error, and header aliases.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from capture.kindle import clippings, notebook_html, plausibility, readwise_csv
from capture.kindle.schema import EmptyParseError, merge_books, to_kindle_json

ROOT = pathlib.Path(__file__).resolve().parents[1]
FX = ROOT / "fixtures" / "meditations"


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads((FX / "expected" / "kindle-highlights.json").read_text(encoding="utf-8"))


def _strip(doc: dict, *, drop: tuple[str, ...] = ()) -> dict:
    """Comparable core: books + annotations, minus volatile top-level keys and dropped fields."""
    books = []
    for b in doc["books"]:
        anns = [{k: (None if k in drop else v) for k, v in a.items()} for a in b["annotations"]]
        books.append({k: v for k, v in b.items() if k != "annotations"} | {"annotations": anns})
    return {"books": books, "total_annotations": doc["total_annotations"]}


# --- My Clippings.txt ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def clip_books():
    return clippings.parse_clippings_file(FX / "clippings" / "My Clippings.txt")


def test_clippings_matches_golden_except_colour(clip_books, golden):
    doc = to_kindle_json(clip_books, source="clippings", crawled_at="x")
    assert _strip(doc, drop=("color",)) == _strip(golden, drop=("color",))


def test_clippings_drops_superseded_and_duplicates(clip_books):
    texts = [a.text for a in clip_books[0].annotations]
    assert len(texts) == 35 and len(set(texts)) == 35
    assert "This world is mere change" not in texts                       # superseded short
    assert "Every man's happiness depends from himself" not in texts     # superseded short
    assert sum(t.startswith("Let nothing be done rashly") for t in texts) == 1   # duplicate kept once


def test_clippings_pageless_record_has_page_none(clip_books):
    a = next(a for a in clip_books[0].annotations if a.text.startswith("For not observing the state"))
    assert a.page is None and a.location.isdigit()


def test_clippings_notes_attach_to_containing_highlight(clip_books):
    noted = {a.text: a.note for a in clip_books[0].annotations if a.note}
    assert len(noted) == 5
    morning = next(v for k, v in noted.items() if k.startswith("go about every action as thy last action"))
    assert morning == "Morning rule: the first task as if it were the last."
    assert all(a.kind == "highlight" for a in clip_books[0].annotations), "no orphan notes in the fixture"


def test_clippings_bom_crlf_and_both_metadata_forms():
    raw = (FX / "clippings" / "My Clippings.txt").read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf" and b"\r\n" in raw
    text = raw.decode("utf-8-sig")
    assert " at location " in text and " | Location " in text
    assert clippings.parse_clippings(text)[0].title == "Meditations"


def test_clippings_empty_parse_of_nonempty_is_an_error():
    junk = "Some Title (Someone)\n- Your Highlight somewhere unparseable\n\ntext\n==========\n"
    with pytest.raises(EmptyParseError):
        clippings.parse_clippings(junk)
    assert clippings.parse_clippings("") == []


def test_clippings_diagnose_prints_one_line_per_record(capsys):
    clippings.parse_clippings_file(FX / "clippings" / "My Clippings.txt", diagnose=True)
    out = capsys.readouterr().out
    assert out.count("record ") == 47 and "superseded=3" in out and "duplicates=2" in out and "bookmarks=2" in out


# --- Export Notes HTML ---------------------------------------------------------------------

def test_html_export_matches_golden_exactly(golden):
    book = notebook_html.parse_notebook_html_file(FX / "export-html" / "meditations.html")
    doc = to_kindle_json([book], source="notebook_html", crawled_at="x")
    assert _strip(doc) == _strip(golden)


def test_html_note_pairs_attach_and_colours_normalise():
    book = notebook_html.parse_notebook_html_file(FX / "export-html" / "meditations.html")
    assert {a.color for a in book.annotations} == {"Yellow", "Pink", "Blue", "Orange"}
    assert sum(1 for a in book.annotations if a.note) == 5


def test_html_without_the_expected_divs_is_an_error():
    with pytest.raises(EmptyParseError):
        notebook_html.parse_notebook_html("<html><body><p>not a notebook export</p></body></html>")


# --- Readwise CSV --------------------------------------------------------------------------

def test_readwise_matches_golden_except_page(golden):
    books = readwise_csv.parse_readwise_csv_file(FX / "readwise" / "highlights.csv")
    doc = to_kindle_json(books, source="readwise_csv", crawled_at="x")
    assert _strip(doc, drop=("page",)) == _strip(golden, drop=("page",))


def test_readwise_header_aliases_and_missing_header_is_loud():
    text = (FX / "readwise" / "highlights.csv").read_text(encoding="utf-8")
    aliased = text.replace("Highlight,Book Title,Book Author", "Highlight text,Title,Author", 1)
    assert len(readwise_csv.parse_readwise_csv(aliased)[0].annotations) == 35
    broken = text.replace("Highlight,Book Title,", "Quote,Book Title,", 1)
    with pytest.raises(ValueError, match="missing required column"):
        readwise_csv.parse_readwise_csv(broken)


# --- cross-source merge + the merge_corpus contract -----------------------------------------

def test_same_highlight_from_two_sources_dedupes_on_merge(clip_books):
    rw = readwise_csv.parse_readwise_csv_file(FX / "readwise" / "highlights.csv")
    merged = merge_books(clip_books, rw)
    assert len(merged) == 1 and len(merged[0].annotations) == 35


def test_merge_matches_on_title_when_only_one_source_has_a_real_asin(clip_books):
    """Readwise supplies the real Amazon id; the device file never does. Keying on asin would
    land the same book twice — the defect a docs pass found before it reached a reader."""
    text = (FX / "readwise" / "highlights.csv").read_text(encoding="utf-8")
    with_asin = text.replace(",Marcus Aurelius,,", ",Marcus Aurelius,B00FIXTURE,")
    assert with_asin != text
    rw = readwise_csv.parse_readwise_csv(with_asin)
    assert rw[0].asin == "B00FIXTURE"
    merged = merge_books(clip_books, rw)
    assert len(merged) == 1 and len(merged[0].annotations) == 35
    assert merged[0].asin == "B00FIXTURE", "the real id wins over the synthetic one"


def test_plausibility_flags_a_page_cap_band_and_prints_sorted_counts(capsys):
    doc = {"books": [{"title": t, "n": n} for t, n in
                     [("a", 97), ("b", 95), ("c", 92), ("d", 460), ("e", 12), ("f", 0)]]}
    rep = plausibility.check(doc)
    out = capsys.readouterr().out
    assert "sorted counts = [0, 12, 92, 95, 97, 460]" in out
    assert "PAGE_CAP_SUSPECTED" in rep.flags and "ZERO_VS_NULL" in rep.flags
    rep2 = plausibility.check(doc, previous={"books": [{"title": "a", "n": 97}, {"title": "d", "n": 376}]})
    assert "RECRAWL_DIFF" in rep2.flags


def test_merge_corpus_runs_unchanged_on_parser_output(tmp_path, clip_books):
    import os
    import subprocess
    import sys
    out = tmp_path / "out"
    out.mkdir()
    (out / "bookcorpus").mkdir()
    from capture.kindle.schema import write_kindle_json
    write_kindle_json(out / "kindle-highlights.json", to_kindle_json(clip_books, source="clippings"))
    r = subprocess.run([sys.executable, str(ROOT / "corpus" / "merge_corpus.py")],
                       env={**os.environ, "RG_OUT": str(out)}, capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    merged = json.loads((out / "merged" / "meditations.json").read_text(encoding="utf-8"))
    assert merged["book"] == "Meditations" and len(merged["kindle_highlights"]) == 35
