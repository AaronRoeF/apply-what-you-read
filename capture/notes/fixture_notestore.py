#!/usr/bin/env python3
"""capture/notes/fixture_notestore.py — a synthetic Apple Notes database, in Apple's shape.

The exporter reads a database that exists only on one person's Mac, holding one person's notes.
Testing against it would mean testing against private data on one platform, which is the same as
not testing. So this builds a small database with the columns and file layout the exporter uses,
containing invented notes and the fixture's public-domain page images.

It reproduces exactly the parts the exporter touches — a single table for folders, notes and
attachments; the gzipped protobuf body at path 2.3.2; Apple's OCR and handwriting summary columns;
the Media/<id>/<generation>/<file> and FallbackImages/<id> layout — and nothing else. Everything
downstream of `fetch_folder` is therefore testable on Linux, in CI, with no Mac and no notes.

  python capture/notes/fixture_notestore.py --out /tmp/notes-fixture
"""
from __future__ import annotations

import argparse
import gzip
import pathlib
import shutil
import sqlite3
import sys

APPLE_EPOCH = 978307200
FIXTURE = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "meditations"

SCHEMA = """
CREATE TABLE ZICCLOUDSYNCINGOBJECT (
  Z_PK INTEGER PRIMARY KEY, ZIDENTIFIER TEXT, ZTITLE1 TEXT, ZTITLE2 TEXT,
  ZFOLDER INTEGER, ZNOTE INTEGER, ZMEDIA INTEGER, ZPARENTATTACHMENT INTEGER,
  ZTYPEUTI TEXT, ZOCRSUMMARY TEXT, ZHANDWRITINGSUMMARY TEXT, ZFILENAME TEXT,
  ZMODIFICATIONDATE1 REAL, ZMARKEDFORDELETION INTEGER DEFAULT 0);
CREATE TABLE ZICNOTEDATA (Z_PK INTEGER PRIMARY KEY, ZNOTE INTEGER, ZDATA BLOB);
"""


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _field(num: int, payload: bytes) -> bytes:
    return _varint((num << 3) | 2) + _varint(len(payload)) + payload


def note_blob(text: str) -> bytes:
    """The body, where Apple puts it: gzip(Document{2:{3:{2: text}}}) — path verified against a
    real database before this fixture was written."""
    return gzip.compress(_field(2, _field(3, _field(2, text.encode("utf-8")))))


def build(out: pathlib.Path) -> pathlib.Path:
    out.mkdir(parents=True, exist_ok=True)
    db = out / "NoteStore.sqlite"
    if db.exists():
        db.unlink()
    acct = out / "Accounts" / "ACCOUNT-0001"
    media, fallback = acct / "Media", acct / "FallbackImages"
    media.mkdir(parents=True, exist_ok=True)
    fallback.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    pk = [100]

    def add(**kw):
        pk[0] += 1
        cols = ",".join(kw); qs = ",".join("?" * len(kw))
        con.execute(f"INSERT INTO ZICCLOUDSYNCINGOBJECT (Z_PK,{cols}) VALUES (?,{qs})", (pk[0], *kw.values()))
        return pk[0]

    praxis = add(ZTITLE2="Praxis", ZIDENTIFIER="folder-praxis")
    other = add(ZTITLE2="Groceries", ZIDENTIFIER="folder-other")
    mod = 780000000.0

    def note(title, folder, body="", ident=None):
        nid = add(ZTITLE1=title, ZFOLDER=folder, ZIDENTIFIER=ident or f"note-{pk[0]+1}", ZMODIFICATIONDATE1=mod)
        con.execute("INSERT INTO ZICNOTEDATA (ZNOTE, ZDATA) VALUES (?, ?)", (nid, note_blob(body)))
        return nid

    def image(note_id, src: pathlib.Path, uti="public.png", ocr="", hand=""):
        mid = add(ZIDENTIFIER=f"media-{pk[0]+1}", ZFILENAME=src.name)
        aid = add(ZNOTE=note_id, ZMEDIA=mid, ZTYPEUTI=uti, ZOCRSUMMARY=ocr, ZHANDWRITINGSUMMARY=hand,
                  ZIDENTIFIER=f"att-{pk[0]+1}")
        ident = con.execute("SELECT ZIDENTIFIER FROM ZICCLOUDSYNCINGOBJECT WHERE Z_PK=?", (mid,)).fetchone()[0]
        d = media / ident / "1_generation"          # the undocumented generation directory
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, d / src.name)
        return aid

    def paper(note_id, src: pathlib.Path, hand=""):
        aid = add(ZNOTE=note_id, ZTYPEUTI="com.apple.paper", ZHANDWRITINGSUMMARY=hand,
                  ZIDENTIFIER=f"paper-{pk[0]+1}")
        ident = con.execute("SELECT ZIDENTIFIER FROM ZICCLOUDSYNCINGOBJECT WHERE Z_PK=?", (aid,)).fetchone()[0]
        shutil.copy2(src, fallback / f"{ident}.jpg")
        return aid

    pages = sorted((FIXTURE / "pages").rglob("*.png"))
    if not pages:
        print("fixture_notestore: the Meditations fixture has no page images — run gen_fixture.py first",
              file=sys.stderr)
        raise SystemExit(2)

    # 1 a book note: two photos with Apple's OCR, plus a typed remark
    b1 = note("Meditations", praxis, "Read on the train. The retiring passage is the one that stuck.")
    image(b1, pages[0], ocr="It is in thy power to retire into thyself and to be at rest")
    image(b1, pages[1 % len(pages)], ocr="Be like the promontory against which the waves continually break")
    add(ZNOTE=b1, ZTYPEUTI="com.apple.notes.table", ZIDENTIFIER="table-in-a-book")  # skipped, counted
    # 2 a continuation note for the SAME book, with a Pencil page whose recogniser text must win
    b2 = note("Meditations 2", praxis)
    paper(b2, pages[2 % len(pages)], hand="my own hand: the retiring is a door, not a holiday")
    # 3 a photo with NO Apple text at all — the Vision fallback case
    b3 = note("The Enchiridion", praxis)
    image(b3, pages[3 % len(pages)], ocr="")
    # 4 a quote, with an attribution line
    note("On making a start", praxis,
         "Begin at once to live, and count each separate day as a separate life.\n\n— Seneca, Letters")
    # 5 collected wisdom: a rule with a source, no attribution dash
    note("Two-list rule", praxis,
         "Write the twenty-five things you want. Circle the top five. The other twenty are the ones to avoid "
         "at all costs, because they are attractive enough to steal time from the five.\n\nHeard on a podcast.")
    # 6 an empty note: fits no kind, must be exported as unsorted rather than dropped
    note("Untitled thought", praxis, "")
    # 7 a note OUTSIDE the folder — must never appear in an export
    note("Milk and eggs", other, "do not export me")
    # 8 a table attachment — skipped with a count, never a page
    t = note("Reading log", praxis, "a table lives here")
    add(ZNOTE=t, ZTYPEUTI="com.apple.notes.table", ZIDENTIFIER="table-1")
    # 9 a deleted note — tombstoned, never exported
    d = add(ZTITLE1="Deleted book", ZFOLDER=praxis, ZIDENTIFIER="note-deleted", ZMARKEDFORDELETION=1)
    con.execute("INSERT INTO ZICNOTEDATA (ZNOTE, ZDATA) VALUES (?, ?)", (d, note_blob("gone")))

    con.commit(); con.close()
    return db


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="/tmp/notes-fixture")
    a = ap.parse_args(argv)
    db = build(pathlib.Path(a.out).expanduser())
    print(f"fixture_notestore: wrote {db} (+ Accounts/ACCOUNT-0001/{{Media,FallbackImages}})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
