#!/usr/bin/env python3
"""fixtures/meditations/gen_fixture.py — the deterministic generator for the sample corpus.

Reads `excerpts.txt` (public-domain text; see SOURCE.md) and writes every input the pipeline
consumes, for one imaginary reader:

  clippings/My Clippings.txt          the device file (BOM + CRLF; 40 highlight records incl.
                                      3 superseded shorter versions, 2 exact duplicates and 7
                                      page-less "at location" records; 5 typed notes; 2 bookmarks)
  export-html/meditations.html        the app's "Export Notes" HTML (35 highlights, 5 notes)
  readwise/highlights.csv             a Readwise CSV export (35 rows, no Amazon id)
  pages/meditations/page-0N.png       five "photographed" pages rendered from the text
                                      (page-03 carries a highlighter band and a pen bracket)
  pages/meditations/page-0N.png.ocr.txt   what OCR would return — drives the stub OCR engine
  pages/meditations/notes.md          the sidecar: title / author / two typed notes
  reader-journal/*.md                 three dated notes (one quotes a highlight, one names the
                                      practice, one only mentions the book — the decoy)
  reader-context.md                   the $READER_CONTEXT example
  expected/kindle-highlights.json     the golden parse: what every Kindle on-ramp must produce

NOTHING HERE IS RANDOM. Spans are cut from excerpts.txt by anchor phrases; locations derive from
character offsets; timestamps step from one fixed base. Re-running produces identical bytes,
and `--check` proves it (text byte-for-byte, PNGs pixel-for-pixel — PNG encoders differ across
Pillow versions, pixels do not).

    python fixtures/meditations/gen_fixture.py            # (re)generate in place
    python fixtures/meditations/gen_fixture.py --check    # regenerate to a temp dir and diff
    python fixtures/meditations/gen_fixture.py --no-pages # skip the PNGs (no Pillow needed)

Pillow >= 10.1 is needed for the page images (`pip install pillow`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import csv
import html
import io
import json
import pathlib
import re
import sys
import tempfile
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from capture.kindle.schema import (Annotation, Book, annotation_id, synthetic_asin,  # noqa: E402
                                   to_kindle_json)

TITLE, AUTHOR = "Meditations", "Marcus Aurelius"
ASIN = synthetic_asin(TITLE, AUTHOR)
SRC_LINE = "Project Gutenberg eBook #2680 — https://www.gutenberg.org/ebooks/2680 — public domain (US); synthetic annotations by gen_fixture.py"
BASE_TS = dt.datetime(2026, 3, 1, 8, 0, 0)
STEP = dt.timedelta(hours=7)

# (start phrase, end phrase or None, colour, page known?, typed note or None)
SPANS = [
    ("Remember how long thou hast already put off these things", "thou hast neglected it.", "Yellow", True, None),
    ("It is high time for thee to understand the true nature both of the world", "thou thyself didst flow", "Yellow", True, None),
    ("there is but a certain limit of time appointed unto thee", "never after return.", "Pink", True, "Deadline for the soul, not the calendar."),
    ("Let it be thy earnest and incessant care as a Roman and a man", "freedom and justice", "Yellow", True, None),
    ("go about every action as thy last action", "and self-love", "Pink", True, "Morning rule: the first task as if it were the last."),
    ("Every man's happiness depends from himself", "conceits of other men.", "Yellow", False, None),
    ("Why should any of these things that happen externally, so much distract thee?", "wandering to and fro.", "Yellow", True, None),
    ("they are idle in their actions, who toil and labour in this life", "motions, and desires.", "Yellow", True, None),
    ("For not observing the state of another man's soul", "known to be unhappy.", "Yellow", False, None),
    ("Tell whosoever they be that intend not", "must of necessity be unhappy.", "Yellow", True, None),
    ("A man must not only consider how daily his life wasteth and decreaseth", "so able and sufficient", "Yellow", True, None),
    ("Thou must hasten therefore", "doth daily waste and decay", "Pink", True, None),
    ("whatsoever it is that naturally doth happen to things natural", "pleasing and delightful", "Blue", True, None),
    ("as a great loaf when it is baked", "stir the appetite.", "Yellow", True, None),
    ("So figs are accounted fairest and ripest then", "in their proper beauty.", "Yellow", False, None),
    ("if a man shall with a profound mind and apprehension, consider all things in the world", "matter of pleasure and delight.", "Yellow", True, None),
    ("So will he be able to perceive the proper ripeness and beauty of old age", "he will soon find out and discern.", "Yellow", True, None),
    ("not credible unto every one, but unto them only who are truly and familiarly acquainted", "and all natural things.", "Yellow", False, None),
    ("That inward mistress part of man if it be in its own true natural temper", "at first it intended.", "Yellow", True, None),
    ("it doth prosecute it with exception and reservation", "it makes its proper object.", "Yellow", True, None),
    ("Even as the fire when it prevails upon those things that are in his way", "made greater and greater.", "Yellow", True, None),
    ("Let nothing be done rashly, and at random", "perfect rules of art.", "Orange", True, None),
    ("They seek for themselves private retiring places", "long much after such places.", "Yellow", True, None),
    ("At what time soever thou wilt, it is in thy power to retire into thyself", "free from all businesses.", "Pink", True, "The retiring: ten minutes, door shut, before the inbox."),
    ("A man cannot any whither retire better than to his own soul", "perfect ease and tranquillity.", "Yellow", True, None),
    ("By tranquillity I understand a decent orderly disposition and carriage", "confusion and tumultuousness.", "Yellow", True, None),
    ("Let these precepts be brief and fundamental", "purge thy soul throughly", "Yellow", False, None),
    ("all reasonable creatures are made one for another", "against their wills that they offend?", "Yellow", True, None),
    ("how many already, who once likewise prosecuted their enmities", "reduced unto ashes?", "Yellow", True, "Every grudge I hold has this expiry date."),
    ("It is time for thee to make an end.", None, "Yellow", True, None),
    ("how quickly all things that are, are forgotten", "human judgments and opinions", "Yellow", True, None),
    ("For the whole earth is but as one point", "that will commend thee?", "Yellow", False, None),
    ("keep thyself from distraction, and intend not anything vehemently", "as a mortal creature.", "Yellow", True, None),
    ("the things or objects themselves reach not unto the soul", "all the trouble doth proceed.", "Pink", True, "Opinion is the only place the trouble lives."),
    ("This world is mere change, and this life, opinion.", None, "Pink", True, None),
]
# Earlier, shorter versions of three highlights (the reader re-selected a longer span later).
# A parser must keep the later superset and drop these. Index -> shorter start/end phrase.
SUPERSEDED = {5: ("Every man's happiness depends from himself", None),
              23: ("it is in thy power to retire into thyself", None),
              34: ("This world is mere change", None)}
DUPLICATES = [21, 29]            # re-appear verbatim at the end of the file
BOOKMARKS_AFTER = [0, 22]        # a bookmark record follows these highlights

PAGES = [  # (label, start phrase, end phrase) — rendered as "photographed" pages
    ("BOOK II", "I. Remember how long", "observe these things."),
    ("BOOK II", "III. Do, soul, do", "must of necessity be unhappy."),
    ("BOOK III", "I. A man must not only consider", "doth daily waste and decay"),
    ("BOOK IV", "I. That inward mistress part of man", "perfect rules of art."),
    ("BOOK IV", "III. They seek for themselves private retiring", "It is time for thee to make an end."),
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def load_text() -> str:
    raw = (HERE / "excerpts.txt").read_text(encoding="utf-8")
    first, _, body = raw.partition("\n")
    if not (first.startswith("# SOURCE:") and "#2680" in first):
        sys.exit("excerpts.txt must open with the '# SOURCE: ... #2680' line")
    return norm(body)


def cut(text: str, start: str, end: str | None) -> tuple[str, int, int]:
    s = text.find(start)
    if s < 0:
        sys.exit(f"anchor not found in excerpts: {start!r}")
    if end is None:
        e = s + len(start)
    else:
        e = text.find(end, s)
        if e < 0:
            sys.exit(f"end anchor not found after {start!r}: {end!r}")
        e += len(end)
    return text[s:e], s, e


def loc_of(offset: int) -> int:
    return 100 + offset // 40


def page_of(loc: int) -> str:
    return str(1 + (loc - 100) // 30)


def book_of(text: str, offset: int) -> str:
    marks = [(text.find(f"BOOK {b}"), f"BOOK {b}") for b in ("II", "III", "IV")]
    return max((m for m in marks if m[0] <= offset), key=lambda m: m[0])[1]


def kindle_stamp(t: dt.datetime) -> str:
    h = t.hour % 12 or 12
    return f"{t:%A, %B} {t.day}, {t.year} {h}:{t:%M:%S} {'AM' if t.hour < 12 else 'PM'}"


# ------------------------------------------------------------------------------------------
def build_annotations(text: str):
    """The 35 canonical annotations (what every parser must produce) + raw clipping records."""
    anns, raw = [], []
    for i, (start, end, color, paged, note) in enumerate(SPANS):
        span, s, e = cut(text, start, end)
        loc, loc_end = loc_of(s), loc_of(e)
        page = page_of(loc) if paged else None
        t = BASE_TS + i * STEP
        if i in SUPERSEDED:
            short, sh_s, sh_e = cut(text, *SUPERSEDED[i])
            raw.append(("Highlight", page, loc_of(sh_s), loc_of(sh_e), t - dt.timedelta(hours=1), short))
        raw.append(("Highlight", page, loc, loc_end, t, span))
        if i in BOOKMARKS_AFTER:
            raw.append(("Bookmark", page, loc, None, t + dt.timedelta(minutes=30), ""))
        if note:
            raw.append(("Note", page, loc_end, None, t + dt.timedelta(minutes=2), note))
        anns.append(Annotation(
            id=annotation_id("kh", TITLE, str(loc), span), text=span, note=note or "",
            color=color, page=page, location=str(loc), location_end=str(loc_end),
            added_on=t.isoformat(timespec="seconds"), kind="highlight"))
    for j, i in enumerate(DUPLICATES):
        a = anns[i]
        raw.append(("Highlight", a.page, int(a.location), int(a.location_end),
                    BASE_TS + (len(SPANS) + j) * STEP, a.text))
    return anns, raw


def write_clippings(raw, out: pathlib.Path):
    parts = []
    for kind, page, loc, loc_end, t, body in raw:
        rng = f"{loc}-{loc_end}" if loc_end and loc_end != loc else f"{loc}"
        if page is None:
            meta = f"- Your {kind} at location {rng} | Added on {kindle_stamp(t)}"
        else:
            meta = f"- Your {kind} on page {page} | Location {rng} | Added on {kindle_stamp(t)}"
        parts.append(f"{TITLE} ({AUTHOR})\r\n{meta}\r\n\r\n{body}\r\n==========\r\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(("﻿" + "".join(parts)).encode("utf-8"))


def write_export_html(anns, text: str, out: pathlib.Path):
    rows = [f'<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>',
            f'<title>{TITLE} - Notebook</title></head><body>',
            f'<!-- SOURCE: {html.escape(SRC_LINE)} -->',
            '<div class="bodyContainer">',
            '<div class="notebookFor">Notebook Export</div>',
            f'<div class="bookTitle">{TITLE}</div>',
            f'<div class="authors">{AUTHOR}</div>',
            f'<div class="citation">{AUTHOR}. <i>{TITLE}</i>. Project Gutenberg, 2001.</div>',
            '<hr/>']
    current = None
    for a in anns:
        b = book_of(text, text.find(a.text))
        if b != current:
            rows.append(f'<div class="sectionHeading">{b}</div>')
            current = b
        where = f"Page {a.page} · Location {a.location}" if a.page else f"Location {a.location}"
        c = (a.color or "yellow").lower()
        rows.append(f'<div class="noteHeading">Highlight (<span class="highlight_{c}">{c}</span>) - {where}</div>')
        rows.append(f'<div class="noteText">{html.escape(a.text)}</div>')
        if a.note:
            rows.append(f'<div class="noteHeading">Note - {where}</div>')
            rows.append(f'<div class="noteText">{html.escape(a.note)}</div>')
    rows += ['</div></body></html>', '']
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows), encoding="utf-8")


def write_readwise_csv(anns, out: pathlib.Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Highlight", "Book Title", "Book Author", "Amazon Book ID", "Note", "Color",
                "Tags", "Location Type", "Location", "Highlighted at", "Document tags"])
    for a in anns:
        w.writerow([a.text, TITLE, AUTHOR, "", a.note, (a.color or "").lower(), "", "location",
                    a.location, a.added_on + "Z", ""])
    out.write_text(buf.getvalue(), encoding="utf-8")


def page_texts(text: str):
    for label, start, end in PAGES:
        body, _, _ = cut(text, start, end)
        yield label, body


def write_pages(text: str, pages_dir: pathlib.Path, with_png: bool):
    pages_dir.mkdir(parents=True, exist_ok=True)
    for n, (label, body) in enumerate(page_texts(text), start=1):
        lines = textwrap.wrap(body, width=64)
        (pages_dir / f"page-{n:02d}.png.ocr.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if with_png:
            render_page(label, lines, pages_dir / f"page-{n:02d}.png", marked=(n == 3))
    (pages_dir / "notes.md").write_text(
        "---\n"
        f"title: {TITLE}\n"
        f"author: {AUTHOR}\n"
        f"asin: {ASIN}\n"
        f"source: \"{SRC_LINE}\"\n"
        "---\n\n"
        "Two notes typed on the phone while reading the paper copy.\n\n"
        "- Book II, on the first page: read this before opening anything with a red badge on it.\n"
        "- Book IV, the retiring passage: the villages and the sea-shore are the notifications.\n",
        encoding="utf-8")


def render_page(label: str, lines: list[str], out: pathlib.Path, marked: bool):
    from PIL import Image, ImageDraw, ImageFont
    W, H, M, LH = 1240, 1754, 96, 40
    img = Image.new("RGB", (W, H), (252, 250, 244))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=26)
    small = ImageFont.load_default(size=20)
    draw.text((M, 48), f"MEDITATIONS  ·  {label}", fill=(60, 60, 60), font=small)
    y0 = 120
    if marked:  # a highlighter band over two lines, drawn under the ink
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(band).rectangle([M - 6, y0 + 5 * LH - 6, W - M + 6, y0 + 7 * LH + 2], fill=(255, 235, 59, 120))
        img = Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")
        draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((M, y0 + i * LH), line, fill=(20, 20, 20), font=font)
    if marked:  # a pen bracket in the margin beside lines 10–12
        x, top, bot = M - 34, y0 + 10 * LH - 4, y0 + 13 * LH - 10
        ink = (28, 44, 120)
        draw.line([(x, top), (x, bot)], fill=ink, width=4)
        draw.line([(x, top), (x + 14, top + 2)], fill=ink, width=4)
        draw.line([(x, bot), (x + 14, bot - 3)], fill=ink, width=4)
    draw.text((W // 2 - 10, H - 70), str(out.stem[-2:]).lstrip("0"), fill=(90, 90, 90), font=small)
    img.save(out, format="PNG")


def write_journal_and_context(root: pathlib.Path):
    j = root / "reader-journal"
    j.mkdir(parents=True, exist_ok=True)
    fm = f'---\ntype: journal\nsource: "reader journal (synthetic); quotes cite {SRC_LINE}"\n---\n\n'
    (j / "2026-03-04.md").write_text(fm + (
        "# 2026-03-04\n\n"
        "Tried the thing from Book IV before the inbox: ten minutes, door shut. \"It is in thy power "
        "to retire into thyself, and to be at rest, and free from all businesses.\" It held until "
        "the second call. The negotiation prep went better for it — I wrote the position before "
        "reading theirs.\n"), encoding="utf-8")
    (j / "2026-03-11.md").write_text(fm + (
        "# 2026-03-11\n\n"
        "Did the retiring again before the 9:00 call, and again at lunch. Naming it helps: the "
        "retiring. Also caught myself keeping score on a colleague and remembered the line about "
        "enmities and ashes; let it go by the afternoon.\n"), encoding="utf-8")
    (j / "2026-04-02.md").write_text(fm + (
        "# 2026-04-02\n\n"
        "Reading list for the quarter: Meditations (still in Book IV), two books on hiring, one on "
        "negotiation. No notes yet on the last three.\n"), encoding="utf-8")
    (root / "reader-context.md").write_text(
        "---\n"
        f"source: \"synthetic reader context for the fixture; book text from {SRC_LINE}\"\n"
        "---\n\n"
        "# Reader context (the $READER_CONTEXT example)\n\n"
        "A reader who manages a small team and reads to use, not to finish. This week: a difficult "
        "negotiation on Tuesday, a hiring decision due Friday, and an inbox that opens the day "
        "unless something else does first.\n", encoding="utf-8")


def generate(root: pathlib.Path, with_png: bool):
    text = load_text()
    anns, raw = build_annotations(text)
    write_clippings(raw, root / "clippings" / "My Clippings.txt")
    write_export_html(anns, text, root / "export-html" / "meditations.html")
    write_readwise_csv(anns, root / "readwise" / "highlights.csv")
    write_pages(text, root / "pages" / "meditations", with_png)
    write_journal_and_context(root)
    doc = to_kindle_json([Book(ASIN, TITLE, AUTHOR, anns)], source="fixture",
                         crawled_at=BASE_TS.strftime("%m/%d/%Y %H:%M:%S"))
    exp = root / "expected"
    exp.mkdir(parents=True, exist_ok=True)
    (exp / "kindle-highlights.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_hl = sum(1 for r in raw if r[0] == "Highlight")
    return len(anns), n_hl, len(raw)


def check(with_png: bool) -> int:
    global HERE  # generate() reads excerpts via HERE; point it at a temp copy during the check
    real = HERE
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        (tmp / "excerpts.txt").write_bytes((real / "excerpts.txt").read_bytes())
        try:
            HERE = tmp
            generate(tmp, with_png)
        finally:
            HERE = real
        drift = []
        for p in sorted(tmp.rglob("*")):
            if p.is_dir() or p.name == "excerpts.txt":
                continue
            q = real / p.relative_to(tmp)
            if not q.exists():
                drift.append(f"MISSING  {q.relative_to(real)}")
            elif p.suffix == ".png":
                from PIL import Image
                if Image.open(p).tobytes() != Image.open(q).tobytes():
                    drift.append(f"PIXELS   {q.relative_to(real)}")
            elif p.read_bytes() != q.read_bytes():
                drift.append(f"DIFFERS  {q.relative_to(real)}")
        for line in drift:
            print(line)
        print(f"gen_fixture --check: {'DRIFT' if drift else 'identical'} ({len(drift)} file(s))")
        return 1 if drift else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="regenerate to a temp dir and diff against the committed files")
    ap.add_argument("--no-pages", action="store_true", help="skip the PNG page images (no Pillow needed)")
    args = ap.parse_args(argv)
    if args.check:
        return check(with_png=not args.no_pages)
    n_anns, n_hl, n_raw = generate(HERE, with_png=not args.no_pages)
    print(f"gen_fixture: {n_anns} canonical annotations · {n_hl} highlight records · {n_raw} clipping records · asin {ASIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
