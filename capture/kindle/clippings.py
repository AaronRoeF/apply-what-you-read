"""capture/kindle/clippings.py — parse the device file `My Clippings.txt`.

The file every Kindle writes as you read: one record per highlight, note or bookmark, separated
by a line of ten `=`. It is the most universal on-ramp (no account, no app) and the lossiest:
it carries NO colour, its records accumulate (re-selecting a longer span leaves the shorter one
behind), and exact duplicates appear whenever the device re-syncs. This parser:

  * strips the UTF-8 BOM and accepts CRLF or LF
  * reads both metadata forms — `on page N | Location A-B` and the older `at location A-B`
  * attaches a typed Note to the highlight whose location range contains it
  * drops bookmarks, exact duplicates, and SUPERSEDED highlights (an earlier record whose text
    is contained in a later, overlapping one — the reader re-selected a longer span)
  * raises EmptyParseError when a non-empty file yields zero records (the null result and the
    correct result are the same value; that must be an error, never a clean exit)

Record grammar (what real files look like; `--diagnose` prints one line per record):

    <Title> (<Author>)
    - Your Highlight on page 12 | Location 123-125 | Added on Monday, March 4, 2026 8:15:32 AM
    <blank line>
    <the selected text>
    ==========
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from collections import defaultdict

from .schema import Annotation, Book, EmptyParseError, annotation_id, loc_int, synthetic_asin

SEP = "=========="
SUPERSEDE_CAP = 5000          # per book: 5,000 spans is ~3 s of quadratic work
SUPERSEDE_BUDGET = 10000      # per file: after this many spans have had the pass, later books skip it
META_RE = re.compile(
    r"^- Your (?P<kind>Highlight|Note|Bookmark|Clipping)"
    r"(?: on [Pp]age (?P<page>[^\s|]+))?"
    r"(?:\s*\|\s*| at | on )?[Ll]ocation (?P<loc>\d[\d,]*)(?:-(?P<loc_end>\d[\d,]*))?"
    r"(?:\s*\|\s*Added on (?P<added>\S.*?))?$"
)
# Lines are .strip()ed before matching, so no trailing \s* — a lazy group followed by \s*$ is
# quadratic on long runs of spaces (measured: 2.7 s at 32k spaces).
TITLE_RE = re.compile(r"^(?P<title>.*?)(?: \((?P<author>[^()]*)\))?$")
STAMP_FORMATS = ("%A, %B %d, %Y %I:%M:%S %p", "%A, %d %B %Y %H:%M:%S", "%A, %B %d, %Y %H:%M:%S")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def parse_stamp(s: str | None) -> str | None:
    if not s:
        return None
    for fmt in STAMP_FORMATS:
        try:
            return dt.datetime.strptime(s.strip(), fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def split_records(text: str) -> list[str]:
    text = text.lstrip("﻿").replace("\r\n", "\n")
    return [r.strip("\n") for r in text.split(SEP) if r.strip()]


def parse_record(rec: str) -> dict | None:
    lines = rec.split("\n")
    if len(lines) < 2:
        return None
    m = META_RE.match(lines[1].strip())
    if not m:
        return None
    t = TITLE_RE.match(lines[0].strip())
    body_lines = lines[2:]
    if body_lines and body_lines[0].strip() == "":
        body_lines = body_lines[1:]
    loc = loc_int(m.group("loc"))
    if loc is None:
        return None   # a location no book can have (13+ digits): skip the record, count it unparsed
    return {
        "kind": m.group("kind"),
        "title": (t.group("title") if t else lines[0]).strip(),
        "author": ((t.group("author") or "") if t else "").strip(),
        "page": m.group("page"),
        "loc": loc,
        "loc_end": loc_int(m.group("loc_end")) or loc,
        "added": parse_stamp(m.group("added")),
        "body": "\n".join(body_lines).strip(),
    }


def parse_clippings(text: str, *, diagnose: bool = False) -> list[Book]:
    recs = split_records(text)
    if not recs:
        return []
    parsed, bad = [], []
    for i, r in enumerate(recs):
        p = parse_record(r)
        if p is None:
            bad.append((i, r))
            if diagnose:
                print(f"  record {i:4d}: UNPARSED  {r.splitlines()[1][:80] if len(r.splitlines()) > 1 else r[:80]!r}")
            continue
        p["order"] = i
        parsed.append(p)
        if diagnose:
            print(f"  record {i:4d}: {p['kind']:9s} page={p['page'] or '-':>4} loc={p['loc']}-{p['loc_end']} {p['title'][:40]!r}")
    if not parsed:
        raise EmptyParseError(f"{len(recs)} record(s), 0 parsed — the file is not empty but nothing matched the "
                              f"record grammar; first block: {recs[0][:160]!r}")

    by_book: dict[tuple[str, str], dict] = defaultdict(lambda: {"hl": [], "notes": [], "bookmarks": 0})
    for p in parsed:
        slot = by_book[(p["title"], p["author"])]
        if p["kind"] in ("Highlight", "Clipping"):
            slot["hl"].append(p)
        elif p["kind"] == "Note":
            slot["notes"].append(p)
        else:
            slot["bookmarks"] += 1

    books: list[Book] = []
    budget = SUPERSEDE_BUDGET
    skipped: list[str] = []   # books whose superseded-span pass was skipped — reported once, below
    stats = {"duplicates": 0, "superseded": 0, "notes_attached": 0, "notes_orphan": 0, "bookmarks": 0, "unparsed": len(bad)}
    for (title, author), slot in by_book.items():
        hls = sorted(slot["hl"], key=lambda p: (p["loc"] or 0, p["added"] or "", p["order"]))
        # 1. exact duplicates: same start location + same text -> keep the first
        seen, uniq = set(), []
        for p in hls:
            key = (p["loc"], _norm(p["body"]))
            if key in seen:
                stats["duplicates"] += 1
                continue
            seen.add(key)
            uniq.append(p)
        # 2. superseded: an earlier, overlapping record whose text is contained in a later one.
        # The pass is quadratic per book; a real book never nears the cap, a crafted file can.
        keep = []
        run_pass = len(uniq) <= SUPERSEDE_CAP and len(uniq) <= budget
        if run_pass:
            budget -= len(uniq)
        else:
            skipped.append(f"{title!r} ({len(uniq)})")
        for a in uniq:
            superseded = False
            for b in (uniq if run_pass else ()):
                if a is b:
                    continue
                overlap = b["loc"] <= a["loc_end"] and b["loc_end"] >= a["loc"]
                later = (b["added"] or "", b["order"]) > (a["added"] or "", a["order"])
                if overlap and later and len(b["body"]) > len(a["body"]) and _norm(a["body"]) in _norm(b["body"]):
                    superseded = True
                    break
            if superseded:
                stats["superseded"] += 1
            else:
                keep.append(a)
        keep.sort(key=lambda p: (p["added"] or "", p["order"]))
        anns = [Annotation(
            id=annotation_id("kh", title, str(p["loc"]), p["body"]), text=p["body"], note="",
            color=None, page=p["page"], location=str(p["loc"]), location_end=str(p["loc_end"]),
            added_on=p["added"], kind="highlight") for p in keep]
        # 3. notes attach to the highlight whose range contains them (nearest start on ties)
        for n in slot["notes"]:
            cands = [a for a in anns if loc_int(a.location) <= (n["loc"] or 0) <= loc_int(a.location_end)]
            if cands:
                # A note is anchored at the END of its highlight; adjacent spans can share a location
                # bucket, so prefer the candidate whose end is the note's location, then the tightest.
                target = min(cands, key=lambda a: (loc_int(a.location_end) != (n["loc"] or 0), -loc_int(a.location)))
                target.note = (target.note + "; " + n["body"]) if target.note else n["body"]
                stats["notes_attached"] += 1
            else:
                anns.append(Annotation(id=annotation_id("kn", title, str(n["loc"]), n["body"]), text="",
                                       note=n["body"], page=n["page"], location=str(n["loc"]),
                                       added_on=n["added"], kind="note"))
                stats["notes_orphan"] += 1
        stats["bookmarks"] += slot["bookmarks"]
        books.append(Book(synthetic_asin(title, author), title, author, anns))
    if skipped:
        shown = ", ".join(skipped[:5]) + (f", … {len(skipped) - 5} more" if len(skipped) > 5 else "")
        print(f"clippings: superseded-span detection skipped for {len(skipped)} book(s) — per-book cap "
              f"{SUPERSEDE_CAP}, per-file budget {SUPERSEDE_BUDGET}; duplicates were still dropped: {shown}", file=sys.stderr)
    if diagnose:
        print("  " + " ".join(f"{k}={v}" for k, v in stats.items()))
    return books


def parse_clippings_file(path, *, diagnose: bool = False) -> list[Book]:
    from pathlib import Path
    return parse_clippings(Path(path).read_text(encoding="utf-8", errors="replace"), diagnose=diagnose)
