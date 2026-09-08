"""One Apple Notes folder, into the pipeline — tested without a Mac and without anyone's notes.

`capture/notes/fixture_notestore.py` builds a database in Apple's shape, so every rule below runs
on Linux in CI. The two that matter most: a note outside the named folder must never appear, and
Apple's handwriting text must outrank everything else on a Pencil page.
"""
from __future__ import annotations

import gzip
import pathlib
import sqlite3
import subprocess
import sys

import pytest

from capture.notes import apple_notes as AN
from capture.notes import fixture_notestore as FX

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    out = tmp_path_factory.mktemp("notes")
    return FX.build(out), out / "Accounts"


@pytest.fixture()
def exported(store, tmp_path):
    db, accounts = store
    with __import__("tempfile").TemporaryDirectory() as tmp:
        con = AN.open_readonly(db, pathlib.Path(tmp))
        notes = AN.fetch_folder(con, "Praxis")
        res = AN.export(notes, tmp_path / "pages", tmp_path / "praxis", accounts)
    return notes, res, tmp_path


# ── reading ──────────────────────────────────────────────────────────────────────────────────

def test_only_the_named_folder_is_read_and_deleted_notes_are_skipped(exported):
    notes, _, _ = exported
    titles = {n["title"] for n in notes}
    assert "Milk and eggs" not in titles, "a note outside the folder must never be exported"
    assert "Deleted book" not in titles, "a tombstoned note is not a note"
    assert {"Meditations", "Meditations 2", "On making a start"} <= titles


def test_a_missing_folder_is_refused_rather_than_returning_nothing(store):
    db, _ = store
    with __import__("tempfile").TemporaryDirectory() as tmp:
        con = AN.open_readonly(db, pathlib.Path(tmp))
        with pytest.raises(LookupError):
            AN.fetch_folder(con, "No Such Folder")


def test_the_typed_body_is_decoded_from_apple_s_gzipped_protobuf(exported):
    notes, _, _ = exported
    med = next(n for n in notes if n["title"] == "Meditations")
    assert "Read on the train" in med["body"]


def test_the_live_database_is_never_opened_for_writing(store, tmp_path):
    db, _ = store
    before = db.stat().st_mtime_ns
    with __import__("tempfile").TemporaryDirectory() as tmp:
        con = AN.open_readonly(db, pathlib.Path(tmp))
        AN.fetch_folder(con, "Praxis")
        with pytest.raises(sqlite3.OperationalError):
            con.execute("UPDATE ZICCLOUDSYNCINGOBJECT SET ZTITLE1='pwned' WHERE Z_PK=1")
    assert db.stat().st_mtime_ns == before


# ── the three kinds ──────────────────────────────────────────────────────────────────────────

def test_a_note_with_pages_is_a_book_and_a_quote_is_not(exported):
    notes, _, _ = exported
    kinds = {n["title"]: AN.classify(n) for n in notes}
    assert kinds["Meditations"] == "book" and kinds["Meditations 2"] == "book"
    assert kinds["On making a start"] == "quote"
    assert kinds["Two-list rule"] == "wisdom"
    assert kinds["Untitled thought"] == "unsorted"


def test_a_continuation_note_joins_its_book_instead_of_making_a_second_one(exported):
    _, _, out = exported
    books = sorted(p.name for p in (out / "pages").iterdir() if p.is_dir())
    assert "meditations" in books and "meditations-2" not in books, books
    assert AN.book_title("Meditations 2") == "Meditations"
    assert AN.book_title("2001") == "2001", "a title that is only a number is not a continuation"


def test_nothing_fits_no_kind_silently(exported):
    _, res, out = exported
    assert res["stats"]["unsorted"] == 1
    p = out / "praxis" / "untitled-thought.md"
    assert p.exists() and "kind: unsorted" in p.read_text(encoding="utf-8")


def test_a_quote_keeps_its_attribution(exported):
    _, _, out = exported
    text = (out / "praxis" / "on-making-a-start.md").read_text(encoding="utf-8")
    assert 'who: "Seneca"' in text and 'work: "Letters"' in text and "type: quote" in text


# ── the authority rule ───────────────────────────────────────────────────────────────────────

def test_apple_s_handwriting_text_outranks_everything_and_says_so(exported):
    """Strokes beat pixels: the recogniser reads a numbered list and clean technical terms that
    image OCR mangles on the same page. It is never overwritten, and the sidecar records it."""
    import json as J
    _, res, out = exported
    book = out / "pages" / "meditations"
    texts = {p.name: p.read_text(encoding="utf-8") for p in sorted(book.glob("*.ocr.txt"))}
    assert texts, "the recognised text must be written beside each page"
    # The sidecar carries the text; the provenance lives beside it, because the OCR stage reads
    # the sidecar verbatim and anything else in it becomes the page's own words in the corpus.
    prov = J.loads((book / "_provenance.json").read_text(encoding="utf-8"))
    hand = [k for k, v in prov.items() if v["via"] == "apple-handwriting"]
    assert len(hand) == 1, prov
    assert "the retiring is a door" in texts[hand[0] + ".ocr.txt"]
    assert sum(1 for v in prov.values() if v["via"] == "apple-ocr") == 2, prov
    assert res["stats"]["handwriting"] == 1 and res["stats"]["apple_ocr"] == 2


def test_a_page_with_no_apple_text_is_counted_not_invented(exported):
    _, res, out = exported
    assert res["stats"]["no_text"] == 1
    enchiridion = out / "pages" / "the-enchiridion"
    assert list(enchiridion.glob("*.png")), "the image still lands, ready for a Vision pass"
    assert not list(enchiridion.glob("*.ocr.txt")), "no sidecar is written when there is no text"


def test_the_page_image_lands_beside_its_sidecar(exported):
    _, _, out = exported
    med = out / "pages" / "meditations"
    stems = {p.name.split(".")[0] for p in med.iterdir() if p.suffix in (".png", ".jpg")}
    assert stems, "images must be copied out of the Notes media store"
    for s in sorted(stems)[:1]:
        assert (med / f"{s}.png").exists() or (med / f"{s}.jpg").exists()


def test_a_table_is_skipped_with_a_count_never_treated_as_a_page(exported):
    _, res, _ = exported
    assert res["stats"]["skipped_attachments"] >= 1


def test_the_typed_body_becomes_the_sidecar_the_pipeline_already_reads(exported):
    _, _, out = exported
    notes_md = out / "pages" / "meditations" / "notes.md"
    assert notes_md.exists() and "Read on the train" in notes_md.read_text(encoding="utf-8")


# ── end to end ───────────────────────────────────────────────────────────────────────────────

def test_the_cli_dry_run_writes_nothing_and_names_every_note(store, tmp_path):
    db, accounts = store
    r = subprocess.run([sys.executable, str(ROOT / "capture" / "notes" / "apple_notes.py"),
                        "--db", str(db), "--accounts", str(accounts), "--folder", "Praxis",
                        "--pages", str(tmp_path / "pages"), "--notes", str(tmp_path / "praxis"), "--dry-run"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert "dry run — nothing was written" in r.stdout
    assert not (tmp_path / "pages").exists() and not (tmp_path / "praxis").exists()
    assert "Meditations" in r.stdout and "apple-handwriting=" in r.stdout


def test_the_cli_refuses_a_folder_that_does_not_exist(store, tmp_path):
    db, accounts = store
    r = subprocess.run([sys.executable, str(ROOT / "capture" / "notes" / "apple_notes.py"),
                        "--db", str(db), "--accounts", str(accounts), "--folder", "Nope",
                        "--pages", str(tmp_path / "p"), "--notes", str(tmp_path / "n")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 3 and "REFUSED" in r.stderr


def test_a_second_export_is_identical(store, tmp_path):
    db, accounts = store
    cmd = [sys.executable, str(ROOT / "capture" / "notes" / "apple_notes.py"), "--db", str(db),
           "--accounts", str(accounts), "--folder", "Praxis", "--pages", str(tmp_path / "pages"),
           "--notes", str(tmp_path / "praxis"), "--json"]
    a = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    assert a.returncode == 0 and a.stdout == b.stdout, (a.stderr, b.stderr)


def test_the_export_feeds_the_existing_page_pipeline(store, tmp_path):
    """The whole design: Apple Notes is an on-ramp, not a second pipeline. What the exporter
    writes must be exactly what capture/pages/manifest.py already reads."""
    db, accounts = store
    subprocess.run([sys.executable, str(ROOT / "capture" / "notes" / "apple_notes.py"), "--db", str(db),
                    "--accounts", str(accounts), "--folder", "Praxis", "--pages", str(tmp_path / "pages"),
                    "--notes", str(tmp_path / "praxis")], capture_output=True, text=True, cwd=ROOT, check=True)
    r = subprocess.run([sys.executable, str(ROOT / "capture" / "pages" / "manifest.py"),
                        "--pages", str(tmp_path / "pages"), "--out", str(tmp_path / "manifest.json")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    import json
    man = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    books = {n.get("title") for n in man.get("notes", [])}
    assert any("editation" in (b or "") for b in books), books


# ── the library is the evidence for "this note is about a book" ──────────────────────────────

def test_a_typed_note_about_a_book_is_not_loose_wisdom(store, tmp_path):
    """On the first real run, typed notes — book summaries, chapter notes, a note titled with an
    author's name — all landed as `wisdom`, because "does this title name a book?" cannot be
    answered from the title. It can be answered from the shelf."""
    db, accounts = store
    shelf = tmp_path / "books"; shelf.mkdir()
    (shelf / "the-enchiridion.md").write_text('---\nname: "The Enchiridion"\n---\n', encoding="utf-8")
    lib = AN.load_library([shelf])
    note = {"title": "The Enchiridion — chapter notes", "body": "chapter notes", "attachments": []}
    assert AN.classify(note, lib) == "book-note"
    assert AN.classify(note, set()) == "wisdom", "with no library there is no evidence, and it stays wisdom"


def test_the_library_match_is_exact_or_whole_phrase_never_fuzzy(tmp_path):
    """A wrong match files a personal note under someone else's book."""
    shelf = tmp_path / "books"; shelf.mkdir()
    for slug, name in [("meditations", "Meditations"), ("nudge", "Nudge")]:
        (shelf / f"{slug}.md").write_text(f'---\nname: "{name}"\n---\n', encoding="utf-8")
    lib = AN.load_library([shelf])
    assert AN.in_library("Meditations", lib) and AN.in_library("Meditations Book IV", lib)
    assert AN.in_library("The Meditations", lib), "a leading article must not defeat the match"
    assert not AN.in_library("Nudge the thermostat before bed", lib), "a short title must not match loosely"
    assert not AN.in_library("Meditating quietly", lib)


def test_a_book_note_records_which_book_it_belongs_to(store, tmp_path):
    db, accounts = store
    shelf = tmp_path / "books"; shelf.mkdir()
    (shelf / "two-list-rule.md").write_text('---\nname: "Two-list rule"\n---\n', encoding="utf-8")
    with __import__("tempfile").TemporaryDirectory() as tmp:
        con = AN.open_readonly(db, pathlib.Path(tmp))
        notes = AN.fetch_folder(con, "Praxis")
        res = AN.export(notes, tmp_path / "pages", tmp_path / "praxis", accounts,
                        library=AN.load_library([shelf]))
    assert res["stats"]["book_notes"] == 1
    text = (tmp_path / "praxis" / "two-list-rule.md").read_text(encoding="utf-8")
    assert "type: book-note" in text and 'book: "Two-list rule"' in text


def test_a_library_title_that_contains_the_note_title_matches_too(tmp_path):
    """Both directions occur: a note title containing the library's, and a note title contained BY it."""
    shelf = tmp_path / "books"; shelf.mkdir()
    (shelf / "the-enchiridion-of-epictetus.md").write_text('---\nname: "The Enchiridion of Epictetus"\n---\n', encoding="utf-8")
    lib = AN.load_library([shelf])
    assert AN.in_library("The Enchiridion", lib)
    assert AN.in_library("Enchiridion", lib), "a distinctive single word is a title, not a coincidence"
    assert not AN.in_library("Stoic", lib), "a short common word is a coincidence, not a match"


def test_the_reader_s_own_mapping_beats_every_heuristic(store, tmp_path):
    db, accounts = store
    with __import__("tempfile").TemporaryDirectory() as tmp:
        con = AN.open_readonly(db, pathlib.Path(tmp))
        notes = AN.fetch_folder(con, "Praxis")
        res = AN.export(notes, tmp_path / "pages", tmp_path / "praxis", accounts,
                        mapping={"Two-list rule": "Essentialism"})
    assert res["stats"]["book_notes"] == 1
    text = (tmp_path / "praxis" / "two-list-rule.md").read_text(encoding="utf-8")
    assert 'book: "Essentialism"' in text and "type: book-note" in text


# ── the watcher: only what moved, and nothing is ever deleted ────────────────────────────────

def _watch(db, accounts, tmp_path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "capture" / "notes" / "watch.py"),
                           "--db", str(db), "--accounts", str(accounts), "--folder", "Praxis",
                           "--pages", str(tmp_path / "pages"), "--notes", str(tmp_path / "praxis"),
                           "--state", str(tmp_path / "state.json"), "--json", *extra],
                          capture_output=True, text=True, cwd=ROOT)


def test_the_first_run_exports_everything_and_the_second_exports_nothing(store, tmp_path):
    db, accounts = store
    first = _watch(db, accounts, tmp_path)
    assert first.returncode == 0, first.stderr
    import json as J
    assert J.loads(first.stdout)["changed"] > 0
    second = _watch(db, accounts, tmp_path)
    assert J.loads(second.stdout)["changed"] == 0, "an unchanged folder must be free"


def test_an_unchanged_note_is_not_rewritten(store, tmp_path):
    db, accounts = store
    _watch(db, accounts, tmp_path)
    p = tmp_path / "praxis" / "on-making-a-start.md"
    before = p.stat().st_mtime_ns
    _watch(db, accounts, tmp_path)
    assert p.stat().st_mtime_ns == before, "write-only-on-change, so mtimes stay meaningful"


def test_a_note_deleted_in_apple_notes_deletes_nothing_here(store, tmp_path):
    """Deletion in one place must never cascade into a store the reader treats as an archive."""
    db, accounts = store
    _watch(db, accounts, tmp_path)
    quote = tmp_path / "praxis" / "on-making-a-start.md"
    assert quote.exists()
    trimmed = tmp_path / "trimmed.sqlite"
    shutil_copy = __import__("shutil").copy2
    shutil_copy(db, trimmed)
    con = sqlite3.connect(trimmed)
    con.execute("UPDATE ZICCLOUDSYNCINGOBJECT SET ZMARKEDFORDELETION=1 WHERE ZTITLE1='On making a start'")
    con.commit(); con.close()
    r = _watch(trimmed, accounts, tmp_path)
    import json as J
    assert r.returncode == 0 and J.loads(r.stdout)["gone"] == 1, r.stdout
    assert quote.exists(), "the exported note stays"
    state = J.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert any(v.get("gone") for v in state["notes"].values()), "and the disappearance is recorded"


def test_an_edited_note_is_the_only_one_re_exported(store, tmp_path):
    db, accounts = store
    _watch(db, accounts, tmp_path)
    edited = tmp_path / "edited.sqlite"
    __import__("shutil").copy2(db, edited)
    con = sqlite3.connect(edited)
    nid = con.execute("SELECT Z_PK FROM ZICCLOUDSYNCINGOBJECT WHERE ZTITLE1='Two-list rule'").fetchone()[0]
    con.execute("UPDATE ZICNOTEDATA SET ZDATA=? WHERE ZNOTE=?", (FX.note_blob("a new body entirely"), nid))
    con.commit(); con.close()
    r = _watch(edited, accounts, tmp_path)
    import json as J
    assert J.loads(r.stdout)["changed"] == 1, r.stdout
    assert "a new body entirely" in (tmp_path / "praxis" / "two-list-rule.md").read_text(encoding="utf-8")


# ── hostile database and media store ─────────────────────────────────────────────────────────

def test_apples_recognised_text_actually_reaches_the_ocr_stage(store, tmp_path):
    """Review found the exporter writing `<stem>.ocr.txt` while capture/pages reads
    `<image-file>.ocr.txt`. Every page copied, every text recognised, and the OCR stage reported
    '0 ok' — the on-ramp's whole point, silently lost, with nothing failing."""
    db, accounts = store
    subprocess.run([sys.executable, str(ROOT / "capture" / "notes" / "apple_notes.py"), "--db", str(db),
                    "--accounts", str(accounts), "--folder", "Praxis", "--pages", str(tmp_path / "pages"),
                    "--notes", str(tmp_path / "praxis")], capture_output=True, text=True, cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "capture" / "pages" / "manifest.py"), "--pages",
                    str(tmp_path / "pages"), "--out", str(tmp_path / "manifest.json")],
                   capture_output=True, text=True, cwd=ROOT, check=True)
    r = subprocess.run([sys.executable, str(ROOT / "capture" / "pages" / "ocr.py"), "--dir",
                        str(tmp_path / "pages"), "--out", str(tmp_path / "ocr.jsonl"), "--engine", "stub"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    import json as J
    rows = [J.loads(l) for l in (tmp_path / "ocr.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if r.get("ok")]
    assert ok, f"Apple's own text must survive into the corpus: {r.stdout}"
    joined = "\n".join(x["text"] for x in ok)
    assert "retire into thyself" in joined and "the retiring is a door" in joined
    # And ONLY the text. A provenance header written into the sidecar becomes the page's own
    # words in the corpus, where the distiller and the Tutor read it as something the book said.
    for x in ok:
        assert not x["text"].startswith("via:"), x["text"][:80]
        for key in ("via:", "source: apple-notes", "attachment:"):
            assert key not in x["text"], f"provenance leaked into the page text: {x['text'][:120]!r}"
    prov = J.loads((tmp_path / "pages" / "meditations" / "_provenance.json").read_text(encoding="utf-8"))
    assert prov and any(v["via"] == "apple-handwriting" for v in prov.values()), prov
    assert all(set(v) >= {"via", "source", "note"} for v in prov.values())


def test_a_hostile_attachment_identifier_cannot_escape_the_media_store(store, tmp_path):
    """`glob` expands a literal `..`, so an identifier of `../../..` reaches outside the container
    and the copy that follows pulls an arbitrary file into the reader's vault."""
    db, accounts = store
    secret = tmp_path / "secret.txt"
    secret.write_text("not yours\n", encoding="utf-8")
    att = {"uti": "public.png", "id": "x", "media_id": f"../../../../{tmp_path.name}", "filename": "secret.txt"}
    assert AN.media_path(att, accounts) is None
    att2 = {"uti": "com.apple.paper", "id": "../../../../etc/hosts", "media_id": "", "filename": ""}
    assert AN.media_path(att2, accounts) is None


def test_a_symlink_in_the_media_store_is_not_followed(store, tmp_path):
    db, accounts = store
    target = tmp_path / "outside.png"
    target.write_bytes(b"\x89PNG\r\n\x1a\n")
    acct = next(accounts.iterdir())
    d = acct / "Media" / "SYMLINK-TEST" / "1_gen"
    d.mkdir(parents=True, exist_ok=True)
    (d / "shot.png").symlink_to(target)
    att = {"uti": "public.png", "id": "a", "media_id": "SYMLINK-TEST", "filename": "shot.png"}
    assert AN.media_path(att, accounts) is None


def test_a_compressed_note_body_that_expands_absurdly_is_skipped(capsys):
    """522 KB of stored body expanded to 537 MB in review, with no ceiling."""
    import gzip
    bomb = gzip.compress(b"\x00" * (AN.MAX_BODY_BYTES + 1024))
    assert AN.note_text(bomb) == ""
    assert "expanded past" in capsys.readouterr().err


def test_a_malformed_protobuf_stream_terminates(capsys):
    """An uncapped varint walk over a run of continuation bytes is quadratic."""
    import gzip, time
    t0 = time.monotonic()
    assert AN.note_text(gzip.compress(b"\xff" * 200_000)) == ""
    assert time.monotonic() - t0 < 2.0
