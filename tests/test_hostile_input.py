"""Hostile or oversized input degrades loudly; it never crashes the import or the tool.

Security review, round two: a 4,401-digit Kindle location raised ValueError out of int() and
aborted the whole import; the superseded-span pass was quadratic per book; a shipped script
crashed on --help because a fix had used `os` without importing it.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

from capture.kindle.clippings import SUPERSEDE_CAP, parse_clippings
from capture.kindle.schema import loc_int

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _record(i: int, loc: int | str | None = None, title: str = "Big Book") -> str:
    loc = i * 3 if loc is None else loc
    span = f"{loc}-{loc + 2}" if isinstance(loc, int) else loc   # str: a preformatted hostile field
    return (f"{title} (Nobody)\n- Your Highlight on page 1 | Location {span} | "
            f"Added on Sunday, March 1, 2026 8:00:00 AM\n\nhighlight number {i}\n==========\n")


def test_loc_int_returns_none_for_a_location_no_book_can_have():
    assert loc_int("123-125") == 123
    assert loc_int("4,512") == 4512
    assert loc_int("9" * 5000) is None   # int() of this string raises in Python 3.11+; we never call it


def test_an_absurd_location_skips_that_record_and_keeps_the_rest(capsys):
    text = _record(1) + _record(2, loc="9" * 4401) + _record(3)
    books = parse_clippings(text, diagnose=True)
    assert len(books) == 1 and len(books[0].annotations) == 2
    assert "unparsed=1" in capsys.readouterr().out


def test_a_book_over_the_supersede_cap_still_imports_in_seconds(capsys):
    n = SUPERSEDE_CAP + 1
    t0 = time.monotonic()
    books = parse_clippings("".join(_record(i) for i in range(n)))
    assert time.monotonic() - t0 < 10
    assert len(books[0].annotations) == n            # nothing overlapped, nothing dropped
    assert "superseded-span detection skipped" in capsys.readouterr().err


SCRIPTS = ["capture/pages/manifest.py", "capture/pages/ocr.py", "capture/pages/verify.py",
           "capture/pages/make_batches.py", "corpus/build_bookcorpus.py", "corpus/merge_corpus.py",
           "vault/build_nodes.py"]


@pytest.mark.parametrize("script", SCRIPTS)
def test_every_shipped_script_answers_help(script):
    env = {**os.environ, "RG_OUT": str(ROOT / "out")}
    r = subprocess.run([sys.executable, str(ROOT / script), "--help"], capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode == 0, r.stderr


def test_the_kindle_cli_answers_help():
    r = subprocess.run([sys.executable, "-m", "capture.kindle", "--help"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr


def test_a_colour_cell_is_a_word_never_a_frontmatter_line():
    from capture.kindle.schema import norm_color
    assert norm_color("yellow") == "Yellow" and norm_color("  CYAN ") == "Aqua" and norm_color("") is None
    hostile = norm_color("yellow\nrelated: [[../../evil]]\ntags: [injected]\nx")
    assert hostile and "\n" not in hostile and ":" not in hostile and "[" not in hostile and len(hostile) <= 24


def test_node_list_keys_cannot_carry_a_yaml_line():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_nodes", ROOT / "vault" / "build_nodes.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert mod._yaml_key("Yellow") == "Yellow"
    assert mod._yaml_key("yellow\nrelated: [[../../evil]]") == "yellowrelated evil"
    assert mod._yaml_key("") == "unknown" and len(mod._yaml_key("x" * 100)) == 32


def test_the_supersede_budget_bounds_a_file_of_many_capped_books(capsys):
    from capture.kindle.clippings import SUPERSEDE_BUDGET
    per_book, n_books = 2000, (SUPERSEDE_BUDGET // 2000) + 3
    text = "".join(_record(i, title=f"Book {b}") for b in range(n_books) for i in range(per_book))
    t0 = time.monotonic()
    books = parse_clippings(text)
    assert time.monotonic() - t0 < 20
    assert len(books) == n_books and all(len(bk.annotations) == per_book for bk in books)
    err = capsys.readouterr().err
    assert err.count("superseded-span detection skipped") == 1 and "for 3 book(s)" in err, err


def test_a_provider_id_never_shapes_a_merged_filename():
    from corpus.merge_corpus import disambiguate
    k1 = {"title": "Foo", "asin": "../../pwn", "annotations": []}
    k2 = {"title": "Foo", "asin": "B000REAL01", "annotations": []}
    rows = disambiguate([("Foo", [], [], k1), ("Foo", [], [], k2)])
    stems = [r[1] for r in rows]
    assert len(set(stems)) == 2 and all("/" not in s and "\n" not in s and " " not in s for s in stems), stems


def test_two_works_sharing_a_title_get_two_nodes(tmp_path):
    """The merge separates same-title works into distinct stems; the node builder must keep them apart
    instead of writing both to <title>.md (2 written, 1 on disk, no error)."""
    merged = tmp_path / "merged"; merged.mkdir(); vault = tmp_path / "vault"; vault.mkdir()
    def rec(asin, author):
        return {"book": "Foo", "asin": asin, "author": author, "source_notes": [], "photo_pages": [],
                "kindle_highlights": [{"id": "kh:1", "text": "a highlight", "note": "", "color": "Yellow",
                                       "page": None, "location": "10", "location_end": "12"}]}
    (merged / "foo.json").write_text(json.dumps(rec("B000REAL01", "Author Two")), encoding="utf-8")
    (merged / "foo-b000other2.json").write_text(json.dumps(rec("B000OTHER2", "Author One")), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "vault" / "build_nodes.py"), "--corpus", str(merged), "--vault", str(vault)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    nodes = sorted(p.name for p in (vault / "books").glob("*.md"))
    assert nodes == ["foo-b000other2.md", "foo.md"], (nodes, r.stderr)
    assert "Author One" in (vault / "books" / "foo-b000other2.md").read_text(encoding="utf-8")


SHIPPED_PY = sorted(p for p in ROOT.rglob("*.py") if ".venv" not in p.parts and "out" not in p.parts)


def _pre_312_interpreters():
    """Interpreters older than 3.12 on this machine, oldest-preferred order. PEP 701 (3.12) relaxed
    f-strings; a backslash inside an expression is a SyntaxError before it. macOS always ships a
    3.9 at /usr/bin/python3, so the check runs on every Mac even when the venv is 3.13."""
    import shutil
    out = []
    for c in ("python3.9", "python3.10", "python3.11", "/usr/bin/python3"):
        path = c if c.startswith("/") else shutil.which(c)
        if not path or not os.path.exists(path):
            continue
        v = subprocess.run([path, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
                           capture_output=True, text=True).stdout.split()
        if len(v) == 2 and (int(v[0]), int(v[1])) < (3, 12):
            out.append(path)
    return out


def test_every_shipped_module_compiles_before_python_3_12():
    """The floor is 3.11 (pyproject, CI). A 3.13 machine never notices 3.12-only syntax because the
    quickstart prefers the newest interpreter it finds — review caught a backslash inside an
    f-string expression that broke step 5 of the quickstart on 3.11. Compile everything with the
    oldest pre-3.12 interpreter present; CI's 3.11 leg covers a machine that has none."""
    interps = _pre_312_interpreters()
    if not interps:
        pytest.skip("no interpreter older than 3.12 on this machine — CI's 3.11 leg covers it")
    r = subprocess.run([interps[0], "-m", "py_compile", *map(str, SHIPPED_PY)], capture_output=True, text=True)
    assert r.returncode == 0, f"{interps[0]}: {r.stderr}"


def test_importing_a_pipeline_module_does_nothing():
    """Review found `import corpus.merge_corpus` DELETING out/merged/* and then raising if the
    Kindle export was absent — so a clean clone failed three tests before the quickstart had run,
    and CI runs the tests first. A module you can import is a module you can test; a module that
    acts on import is a trap with a helper in it."""
    import importlib, sys as _sys
    canary = ROOT / "out" / "merged" / "_import_canary.json"
    canary.parent.mkdir(parents=True, exist_ok=True)
    canary.write_text('{"canary": true}', encoding="utf-8")
    try:
        for name in ("corpus.merge_corpus", "corpus.build_bookcorpus", "vault.build_nodes",
                     "capture.pages.manifest", "capture.notes.apple_notes",
                     "agents.librarian.candidates"):
            _sys.modules.pop(name, None)
            try:
                importlib.import_module(name)
            except ImportError:
                continue                     # a module that is not a package is out of scope here
            assert canary.exists(), f"importing {name} deleted files under out/merged"
    finally:
        canary.unlink(missing_ok=True)


def test_a_clean_clone_passes_its_own_tests():
    """CI runs the suite before the quickstart, so the suite may not depend on prior-stage state."""
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        dst = pathlib.Path(tmp) / "clone"
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
            ".venv", "out", "demo-vault", "__pycache__", ".pytest_cache", "*.pyc"))
        # Never this file: it holds this test, and running it inside the clone recurses.
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                            "tests/test_kindle_parsers.py", "tests/test_build_nodes.py",
                            "tests/test_docs.py"],
                           capture_output=True, text=True, cwd=dst, timeout=180)
        assert r.returncode == 0, r.stdout[-2500:]
