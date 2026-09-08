#!/usr/bin/env python3
"""capture/notes/apple_notes.py — one Apple Notes folder, into the pipeline.

If your book notes live in Apple Notes — photographed pages, typed remarks, Apple Pencil
handwriting — this reads ONE folder you name and writes the folder-per-book layout the rest of
the pipeline already consumes. Nothing else in the pipeline changes.

THE POINT: APPLE ALREADY DID THE READING. Notes stores, per attachment, the text its own
on-device OCR read from each photo (`ZOCRSUMMARY`) and the text the stroke recogniser read from
each Pencil page (`ZHANDWRITINGSUMMARY`). That is what Spotlight searches. This exporter carries
that text out as it is rather than re-recognising anything, and on a Pencil page the recogniser's
text is AUTHORITATIVE and never overwritten: it works from strokes, and on the same page it
recovers a numbered list and clean technical terms that image OCR mangles. Local Vision is a
second reading, run only where Apple's text is missing or when you ask, and both are kept.

Every line of text carries where it came from — `via: typed | apple-ocr | apple-handwriting` —
because a pipeline that mixes three readers without saying which is which cannot be audited.

SAFETY. The database is copied before it is opened, and opened read-only through a URI. Your
notes are never written to, moved, or deleted; this tool only reads. A note you later delete does
not delete anything downstream.

FOUR KINDS OF NOTE, told apart by evidence and never by guessing:

  book       the note holds photographed or handwritten pages. They become the book's pages and
             its typed body becomes the notes sidecar.
  book-note  no pages, but the title names a book that is already in your library. A typed note
             ABOUT a book is not a photographed page, and pushing it into the pages channel would
             invent a book with no pages; it becomes its own node instead, linked to the book.
  quote      a short note whose body ends in an attribution line ("— Author, Work").
  wisdom     a rule or heuristic with its source; anything else short and text-only.

The library is the evidence for `book-note`, which is why `--library` exists: on the first real
run, nineteen typed notes — book summaries, chapter notes, a note titled with an author's name —
were all landing as `wisdom`, because "does this title name a book?" cannot be answered by
looking at the title. It can be answered by looking at the shelf.

A note that fits no kind is exported as wisdom marked `kind: unsorted` and listed in the report.
Nothing is dropped silently.

Usage:
  python capture/notes/apple_notes.py --folder Praxis [--folder "Book Notes"] --dry-run
  python capture/notes/apple_notes.py --folder Praxis --pages out/pages --notes out/praxis-notes
Env: RG_NOTES_FOLDER, RG_OUT, RG_NOTES_DB
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import json
import os
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile

DEFAULT_DB = "~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
ACCOUNTS = "~/Library/Group Containers/group.com.apple.notes/Accounts"
APPLE_EPOCH = 978307200          # 2001-01-01, Core Data's zero
IMAGE_UTIS = {"public.jpeg": ".jpg", "public.png": ".png", "public.heic": ".heic",
              "public.tiff": ".tiff", "org.webmproject.webp": ".webp", "com.compuserve.gif": ".gif"}
PAPER_UTIS = {"com.apple.paper", "com.apple.paper.doc.scan", "com.apple.drawing",
              "com.apple.drawing.2", "com.apple.notes.sketch"}
SKIP_UTIS = {"com.apple.notes.table", "com.apple.notes.gallery", "com.apple.notes.inlinetextattachment"}
ATTRIBUTION_RE = re.compile(r"^\s*[—–-]\s*(?P<who>[^,\n]{2,60})(?:,\s*(?P<work>[^\n]{2,80}))?\s*$", re.M)
CONTINUATION_RE = re.compile(r"^(?P<base>.+?)[\s_-]*(?:\(\d+\)|\d+)$")
QUOTE_MAX_CHARS = 1200
MAX_BODY_BYTES = 8 * 1024 * 1024   # a note is prose; anything larger is not one
MAX_VARINT_BYTES = 10              # a 64-bit varint is 10 bytes; more is a malformed stream
MIN_MATCH_CHARS = 8      # below this a title match is a coincidence, not a match
SOLO_WORD_CHARS = 10     # a one-word title matches by containment only when this distinctive


def kebab(s: str) -> str:
    import hashlib
    out = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return out or "note-" + hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:8]


def apple_time(v) -> str | None:
    try:
        return dt.datetime.fromtimestamp(float(v) + APPLE_EPOCH).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


# ── the note body: a gzipped protobuf ────────────────────────────────────────────────────────

def _pb_fields(buf: bytes):
    """(field number, wire type, value) for one protobuf message. A tolerant walker: the format
    is Apple's and undocumented, so anything unparseable ends the walk rather than raising."""
    i = 0
    while i < len(buf):
        key = shift = 0
        n = 0
        while True:
            if i >= len(buf) or n >= MAX_VARINT_BYTES:
                return                          # malformed or hostile: stop, never spin
            b = buf[i]; i += 1; n += 1
            key |= (b & 0x7F) << shift; shift += 7
            if not b & 0x80:
                break
        fn, wt = key >> 3, key & 7
        if wt == 0:
            v = shift = 0
            n = 0
            while True:
                if i >= len(buf) or n >= MAX_VARINT_BYTES:
                    return
                b = buf[i]; i += 1; n += 1
                v |= (b & 0x7F) << shift; shift += 7
                if not b & 0x80:
                    break
            yield fn, wt, v
        elif wt == 2:
            ln = shift = 0
            n = 0
            while True:
                if i >= len(buf) or n >= MAX_VARINT_BYTES:
                    return
                b = buf[i]; i += 1; n += 1
                ln |= (b & 0x7F) << shift; shift += 7
                if not b & 0x80:
                    break
            yield fn, wt, buf[i:i + ln]; i += ln
        elif wt == 5:
            i += 4
        elif wt == 1:
            i += 8
        else:
            return


def note_text(zdata: bytes | None) -> str:
    """The typed body of a note. Apple stores it gzipped, at protobuf path 2.3.2 (verified against
    a real database). An unknown shape returns "" rather than a guess — the attachments carry the
    text that matters, and a wrong body is worse than a missing one."""
    if not zdata:
        return ""
    # A note body is a few kilobytes. Decompress with a ceiling rather than trusting the archive:
    # 522 KB of ZDATA expanded to 537 MB in review, and the walk that followed was quadratic.
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(zdata)) as fh:
            raw = fh.read(MAX_BODY_BYTES + 1)
    except (OSError, EOFError, gzip.BadGzipFile):
        return ""
    if len(raw) > MAX_BODY_BYTES:
        print(f"apple_notes: a note body expanded past {MAX_BODY_BYTES} bytes and was skipped — "
              f"a note is prose, and this one is not", file=sys.stderr)
        return ""
    for fn, wt, v in _pb_fields(raw):
        if fn != 2 or wt != 2:
            continue
        for f2, w2, v2 in _pb_fields(v):
            if f2 != 3 or w2 != 2:
                continue
            for f3, w3, v3 in _pb_fields(v2):
                if f3 == 2 and w3 == 2 and isinstance(v3, bytes):
                    return v3.decode("utf-8", "replace")
    return ""


# ── reading the database ─────────────────────────────────────────────────────────────────────

def open_readonly(db: pathlib.Path, workdir: pathlib.Path) -> sqlite3.Connection:
    """Copy first, then open read-only. Notes may be running and mid-write; and the reader must be
    incapable of touching the live file, not merely careful with it."""
    copy = workdir / "NoteStore.copy.sqlite"
    shutil.copy2(db, copy)
    for suffix in ("-wal", "-shm"):
        side = db.with_name(db.name + suffix)
        if side.exists():
            shutil.copy2(side, copy.with_name(copy.name + suffix))
    return sqlite3.connect(f"file:{copy}?mode=ro", uri=True)


def fetch_folder(con: sqlite3.Connection, folder: str) -> list[dict]:
    """Every live note in one folder, with its attachments in note order.

    Folder placement is the only evidence of book-ness. An earlier version of this idea accepted
    any note holding five or more images and mis-titled slide decks as books."""
    fid = con.execute(
        "SELECT Z_PK FROM ZICCLOUDSYNCINGOBJECT WHERE ZTITLE2=? AND IFNULL(ZMARKEDFORDELETION,0)=0",
        (folder,)).fetchone()
    if not fid:
        raise LookupError(folder)
    notes = []
    rows = con.execute("""
        SELECT n.Z_PK, n.ZIDENTIFIER, n.ZTITLE1, n.ZMODIFICATIONDATE1, nd.ZDATA
        FROM ZICCLOUDSYNCINGOBJECT n LEFT JOIN ZICNOTEDATA nd ON nd.ZNOTE = n.Z_PK
        WHERE n.ZFOLDER=? AND IFNULL(n.ZMARKEDFORDELETION,0)=0 AND n.ZTITLE1 IS NOT NULL
        ORDER BY n.ZTITLE1""", (fid[0],)).fetchall()
    for pk, ident, title, modified, zdata in rows:
        atts = []
        for a in con.execute("""
                SELECT a.Z_PK, a.ZIDENTIFIER, a.ZTYPEUTI, a.ZOCRSUMMARY, a.ZHANDWRITINGSUMMARY,
                       m.ZIDENTIFIER, m.ZFILENAME
                FROM ZICCLOUDSYNCINGOBJECT a
                LEFT JOIN ZICCLOUDSYNCINGOBJECT m ON a.ZMEDIA = m.Z_PK
                WHERE a.ZNOTE=? AND a.ZTYPEUTI IS NOT NULL AND IFNULL(a.ZMARKEDFORDELETION,0)=0
                ORDER BY a.Z_PK""", (pk,)).fetchall():
            atts.append({"pk": a[0], "id": a[1], "uti": a[2], "ocr": (a[3] or "").strip(),
                         "handwriting": (a[4] or "").strip(), "media_id": a[5], "filename": a[6]})
        notes.append({"pk": pk, "id": ident, "title": (title or "").strip(), "folder": folder,
                      "modified": apple_time(modified), "body": note_text(zdata), "attachments": atts})
    return notes


def _under(root: pathlib.Path, p: pathlib.Path) -> bool:
    """Is this really inside the root, after resolving links and `..`?

    `glob` expands a literal `..` in a pattern, so an attachment identifier of `../../..` reaches
    outside the Notes container entirely and the copy that follows pulls an arbitrary file into
    the reader's vault. A symlink inside the media store does the same thing more quietly."""
    try:
        return p.resolve().is_relative_to(root.resolve())
    except AttributeError:                      # Python 3.8
        try:
            p.resolve().relative_to(root.resolve()); return True
        except ValueError:
            return False
    except (OSError, ValueError):
        return False


SAFE_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def media_path(att: dict, accounts: pathlib.Path) -> pathlib.Path | None:
    """An attachment's file on disk.

    Images live at Accounts/<account>/Media/<media id>/<generation>/<filename> — the generation
    directory is real and undocumented, so this globs rather than assuming a depth. A Pencil page
    has no image of its own; its rendered picture is the fallback image, which is what an OCR
    engine can be pointed at."""
    if not accounts.exists():
        return None
    # An identifier from the database is data. It is interpolated into a glob and then copied from,
    # so it is checked against a shape first and the result is checked against the root after.
    ident, media = att.get("id") or "", att.get("media_id") or ""
    if att["uti"] in PAPER_UTIS:
        if not SAFE_ID.match(ident):
            return None
        for sub in ("FallbackImages", "FallbackPDFs"):
            for cand in accounts.glob(f"*/{sub}/{ident}*"):
                if cand.is_file() and not cand.is_symlink() and _under(accounts, cand):
                    return cand
        return None
    if not SAFE_ID.match(media):
        return None
    hits = [p for p in accounts.glob(f"*/Media/{media}/**/*")
            if p.is_file() and not p.is_symlink() and _under(accounts, p)]
    if not hits:
        return None
    named = [p for p in hits if att["filename"] and p.name == att["filename"]]
    return (named or hits)[0]


# ── classification ───────────────────────────────────────────────────────────────────────────

def norm_title(s: str) -> str:
    """Comparable form of a title: lowercase words only, no punctuation, no articles at the front."""
    t = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^(the|a|an) ", "", t)


def load_library(paths: list[pathlib.Path], warn=True) -> set[str]:
    """Normalised titles of the books already in the reader's library. Accepts a vault `books/`
    directory of markdown nodes or a merged-corpus directory of JSON records; both are just
    filenames plus, when present, a `name:` or `"book":` field."""
    out: set[str] = set()
    for d in paths:
        if not d.exists():
            # A path the caller NAMED is different from one they omitted. Skipping it silently
            # turned every typed book note into loose "wisdom" when --library pointed at a vault
            # directory the pipeline had not built yet — nineteen of them, in the run that found
            # this. The classification still degrades, but never quietly.
            if warn:
                print(f"apple_notes: --library {d} does not exist, so no note can be recognised as "
                      f"being ABOUT a book; typed notes will be filed as wisdom. Build the vault "
                      f"first (vault/build_nodes.py) and re-run, or drop the flag.", file=sys.stderr)
            continue
        for p in sorted(d.iterdir()):
            if p.suffix == ".md":
                out.add(norm_title(p.stem))
                head = p.read_text(encoding="utf-8", errors="replace")[:400]
                m = re.search(r'^name:\s*"?(.*?)"?\s*$', head, re.M)
                if m:
                    out.add(norm_title(m.group(1)))
            elif p.suffix == ".json" and not p.name.startswith("_"):
                out.add(norm_title(p.stem))
                try:
                    rec = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(rec, dict) and rec.get("book"):
                    out.add(norm_title(str(rec["book"])))
    out.discard("")
    return out


def in_library(title: str, library: set[str]) -> bool:
    """Does this title name a book on the shelf? Exact on the normalised form, or the note's title
    contains a library title as a whole-word run ("Meditations Book IV" → Meditations). Never a
    fuzzy score: a wrong match here files a personal note under someone else's book."""
    t = norm_title(title)
    if not t:
        return False
    if t in library:
        return True
    # Containment BOTH ways, whole-phrase, with a length guard. Both directions occur in real
    # data: "Meditations Book IV" contains the library title, and a note titled "The
    # Enchiridion" is contained by the library's "the enchiridion of epictetus". A short phrase can
    # match by accident, so a matched run must be at least MIN_MATCH_CHARS long.
    def substantial(x: str) -> bool:
        # A containment match needs a phrase, or a single word distinctive enough to be one.
        # Two words is the ordinary bar; a lone word qualifies only past SOLO_WORD_CHARS, so
        # "Meditations Book IV" finds Meditations while "Nudge the thermostat before bed" does
        # not find Nudge. Real single-word titles exist and refusing them all would silently
        # exclude a shelf's shortest names.
        w = x.split()
        return len(x) >= MIN_MATCH_CHARS and (len(w) >= 2 or len(x) >= SOLO_WORD_CHARS)
    for lib in library:
        if not substantial(lib):
            continue
        if f" {lib} " in f" {t} " or (substantial(t) and f" {t} " in f" {lib} "):
            return True
    return False


def classify(note: dict, library: set[str] | None = None) -> str:
    """book | book-note | quote | wisdom | unsorted. Evidence only — never a guess about meaning."""
    pages = [a for a in note["attachments"] if a["uti"] in IMAGE_UTIS or a["uti"] in PAPER_UTIS]
    if pages:
        return "book"
    if library and in_library(book_title(note["title"]), library):
        return "book-note"
    if note.get("mapped_book"):          # --map names the book: the reader's own answer wins
        return "book-note"
    body = note["body"].strip()
    if not body:
        return "unsorted"
    if len(body) <= QUOTE_MAX_CHARS and ATTRIBUTION_RE.search(body):
        return "quote"
    return "wisdom"


def attribution(body: str) -> tuple[str, str]:
    m = None
    for m in ATTRIBUTION_RE.finditer(body):
        pass                                  # the LAST attribution line is the note's own
    if not m:
        return "", ""
    return (m.group("who") or "").strip(), (m.group("work") or "").strip()


def book_title(title: str) -> str:
    """"Meditations 2" is the same book as "Meditations" — a continuation note, not a second
    work. The number is stripped only when a base title remains."""
    m = CONTINUATION_RE.match(title.strip())
    if m and len(m.group("base").strip()) >= 3:
        return m.group("base").strip(" _-")
    return title.strip()


# ── writing ──────────────────────────────────────────────────────────────────────────────────

def yaml_str(s) -> str:
    return json.dumps(str(s if s is not None else ""), ensure_ascii=False)


def export(notes: list[dict], pages_root: pathlib.Path, notes_root: pathlib.Path,
           accounts: pathlib.Path, dry_run: bool = False, mapping: dict | None = None,
           library: set[str] | None = None) -> dict:
    mapping = mapping or {}
    stats = {"books": 0, "pages": 0, "apple_ocr": 0, "handwriting": 0, "no_text": 0,
             "book_notes": 0, "quotes": 0, "wisdom": 0, "unsorted": 0,
             "skipped_attachments": 0, "missing_media": 0}
    report: list[str] = []
    by_book: dict[str, list[dict]] = {}
    for n in notes:
        n["mapped_book"] = mapping.get(n["title"], "")
        kind = classify(n, library)
        if kind == "book":
            by_book.setdefault(kebab(mapping.get(n["title"]) or book_title(n["title"])), []).append(n)
            continue
        stats[{"book-note": "book_notes", "quote": "quotes", "wisdom": "wisdom",
               "unsorted": "unsorted"}[kind]] += 1
        if dry_run:
            report.append(f"  {kind:8s} {n['title'][:52]}")
            continue
        who, work = attribution(n["body"]) if kind != "unsorted" else ("", "")
        notes_root.mkdir(parents=True, exist_ok=True)
        p = notes_root / f"{kebab(n['title'] or n['id'])}.md"
        hand = "\n\n".join(a["handwriting"] for a in n["attachments"] if a["handwriting"])
        fm = ["---", f"name: {yaml_str(n['title'])}", f"type: {kind if kind != 'unsorted' else 'wisdom'}",
              "source: apple-notes", f"note_id: {yaml_str(n['id'])}", f"folder: {yaml_str(n['folder'])}",
              f"modified: {n['modified'] or ''}"]
        if kind == "book-note":
            fm.append(f"book: {yaml_str(n.get('mapped_book') or book_title(n['title']))}")
        if kind == "unsorted":
            fm.append("kind: unsorted")
        if who:
            fm.append(f"who: {yaml_str(who)}")
        if work:
            fm.append(f"work: {yaml_str(work)}")
        heading = re.sub(r"[\s\[\]|]+", " ", n["title"]).strip() or "untitled"   # hoisted: a backslash
        # inside an f-string expression is a SyntaxError before 3.12, and the floor is 3.11
        fm += ["via: typed" + (" + apple-handwriting" if hand else ""), "---", "",
               f"# {heading}", "", n["body"].strip(), ""]
        if hand:
            fm += ["---", "", "## Handwriting (Apple's stroke recogniser — authoritative)", "", hand, ""]
        p.write_text("\n".join(fm), encoding="utf-8")

    for slug, group in sorted(by_book.items()):
        stats["books"] += 1
        title = mapping.get(group[0]["title"]) or book_title(group[0]["title"])
        folder = pages_root / slug
        if dry_run:
            n_img = sum(1 for n in group for a in n["attachments"]
                        if a["uti"] in IMAGE_UTIS or a["uti"] in PAPER_UTIS)
            report.append(f"  book     {title[:44]:46s} {len(group)} note(s), {n_img} page(s) -> {folder.name}/")
        else:
            folder.mkdir(parents=True, exist_ok=True)
        idx = 0
        sidecar: list[str] = []
        provenance: dict[str, dict] = {}
        for n in group:
            if n["body"].strip():
                sidecar.append(n["body"].strip())
            for a in n["attachments"]:
                if a["uti"] in SKIP_UTIS:
                    stats["skipped_attachments"] += 1
                    continue
                is_page = a["uti"] in IMAGE_UTIS or a["uti"] in PAPER_UTIS
                if not is_page:
                    stats["skipped_attachments"] += 1
                    continue
                idx += 1
                stats["pages"] += 1
                src = media_path(a, accounts)
                if src is None:
                    stats["missing_media"] += 1
                # Apple's handwriting text OUTRANKS its OCR text: strokes beat pixels, measured.
                if a["handwriting"]:
                    text, via = a["handwriting"], "apple-handwriting"
                    stats["handwriting"] += 1
                elif a["ocr"]:
                    text, via = a["ocr"], "apple-ocr"
                    stats["apple_ocr"] += 1
                else:
                    text, via = "", ""
                    stats["no_text"] += 1
                if dry_run:
                    continue
                ext = IMAGE_UTIS.get(a["uti"], src.suffix if src else ".jpg")
                # Unique across the whole tree, not just this book: capture/pages/manifest.py keys
                # images by BASENAME and refuses duplicates, so a bare p001.png in two books is a
                # refused run. Its guard caught this the first time the two were connected.
                stem = f"{slug}-p{idx:03d}"
                if src is not None:
                    shutil.copy2(src, folder / (stem + ext))
                if text:
                    # The sidecar is named after the IMAGE FILE, extension included, because that
                    # is what capture/pages reads. Writing `<stem>.ocr.txt` instead was silent
                    # data loss: every page copied, every text recognised, and the OCR stage
                    # reported "0 ok" while looking for a name nothing had written.
                    # THE SIDECAR IS THE PAGE'S TEXT AND NOTHING ELSE. Writing a provenance
                    # header into it put "via: apple-ocr / source: apple-notes / attachment: …"
                    # into the corpus as the page's own words, where the distiller and the Tutor
                    # would read it as something the book said. Provenance belongs beside the
                    # text, in a file the OCR stage does not read.
                    (folder / (stem + ext + ".ocr.txt")).write_text(text.rstrip("\n") + "\n",
                                                                    encoding="utf-8")
                    provenance[stem + ext] = {"via": via, "source": "apple-notes",
                                              "attachment": SAFE_ID.match(a["id"] or "") and a["id"] or "",
                                              "note": n["id"], "modified": n["modified"]}
        if not dry_run and provenance:
            (folder / "_provenance.json").write_text(
                json.dumps(provenance, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        if not dry_run and sidecar:
            (folder / "notes.md").write_text(
                f"---\nname: {yaml_str(title)}\nsource: apple-notes\nvia: typed\n---\n\n"
                + "\n\n---\n\n".join(sidecar) + "\n", encoding="utf-8")
    return {"stats": stats, "report": report}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    rg_out = pathlib.Path(os.environ.get("RG_OUT") or (pathlib.Path(__file__).resolve().parents[2] / "out"))
    ap.add_argument("--folder", action="append", default=[],
                    help="Notes folder to read (repeatable). Default: $RG_NOTES_FOLDER or Praxis")
    ap.add_argument("--db", default=os.environ.get("RG_NOTES_DB", DEFAULT_DB))
    ap.add_argument("--accounts", default=ACCOUNTS)
    ap.add_argument("--pages", default=str(rg_out / "pages"))
    ap.add_argument("--notes", default=str(rg_out / "praxis-notes"))
    ap.add_argument("--map", default="", help="TSV of `note title<TAB>book title` overrides")
    ap.add_argument("--library", action="append", default=[],
                    help="a vault books/ dir or a merged-corpus dir; a typed note whose title names "
                         "a book on that shelf becomes a book-note rather than loose wisdom (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="list what would be written; write nothing")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    folders = a.folder or [os.environ.get("RG_NOTES_FOLDER", "Praxis")]
    db = pathlib.Path(a.db).expanduser()
    if not db.exists():
        import platform
        if platform.system() == "Darwin":
            print(f"apple_notes: cannot see the Notes database at {db}.\n"
                  f"  On macOS this is almost always PERMISSIONS, not a missing file: reading it\n"
                  f"  requires Full Disk Access for the program running this. Grant it in\n"
                  f"  System Settings > Privacy & Security > Full Disk Access (add your terminal,\n"
                  f"  or the app running the agent), then run this again.\n"
                  f"  If the path really is wrong, pass --db.", file=sys.stderr)
        else:
            print(f"apple_notes: no Notes database at {db} — this reader is macOS only", file=sys.stderr)
        return 2
    mapping = {}
    if a.map:
        for line in pathlib.Path(a.map).expanduser().read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "\t" in line:
                k, v = line.split("\t", 1)
                mapping[k.strip()] = v.strip()

    with tempfile.TemporaryDirectory(prefix="rg-notes-") as tmp:
        con = open_readonly(db, pathlib.Path(tmp))
        notes, missing = [], []
        for f in folders:
            try:
                notes += fetch_folder(con, f)
            except LookupError:
                missing.append(f)
        if missing:
            print(f"apple_notes: REFUSED — no folder named {', '.join(repr(m) for m in missing)} in Notes. "
                  f"A misspelled folder and an empty one are the same result here; that must be an error.",
                  file=sys.stderr)
            return 3
        if not notes:
            print(f"apple_notes: REFUSED — {', '.join(folders)} holds no notes. An empty export is not a "
                  f"clean run.", file=sys.stderr)
            return 3
        library = load_library([pathlib.Path(p).expanduser() for p in a.library])
        out = export(notes, pathlib.Path(a.pages).expanduser(), pathlib.Path(a.notes).expanduser(),
                     pathlib.Path(a.accounts).expanduser(), a.dry_run, mapping, library)

    s = out["stats"]
    if a.json:
        print(json.dumps({"folders": folders, "notes": len(notes), **s}, indent=1))
        return 0
    print(f"apple_notes: folders={','.join(folders)} notes={len(notes)} books={s['books']} pages={s['pages']} "
          f"book-notes={s['book_notes']} quotes={s['quotes']} wisdom={s['wisdom']} unsorted={s['unsorted']}")
    if not library and (s["wisdom"] or s["unsorted"]):
        print(f"  NOTE: no --library given, so no typed note could be recognised as being ABOUT a book; "
              f"they are all filed as wisdom. Pass --library <vault>/books to sort them.")
    print(f"  page text: apple-handwriting={s['handwriting']} apple-ocr={s['apple_ocr']} none={s['no_text']}"
          f"   (a page with no text needs a Vision pass: capture/pages/ocr.py)")
    if s["missing_media"]:
        print(f"  WARNING: {s['missing_media']} attachment(s) had no file on disk — iCloud may not have "
              f"downloaded them; open the note once and re-run")
    if s["unsorted"]:
        print(f"  {s['unsorted']} note(s) fit no kind and were exported as wisdom marked `unsorted` — "
              f"nothing was dropped")
    for line in out["report"]:
        print(line)
    if a.dry_run:
        print("  (dry run — nothing was written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
