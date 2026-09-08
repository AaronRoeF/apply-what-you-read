"""The corroboration matcher: which marked ideas left a receipt, and which never did.

Every test here is a rule that a looser matcher broke. The floor and the self-exclusion tests
matter most: without them the tool returns confident evidence for everything, which reads exactly
like success.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import subprocess
import sys

import pytest

from agents.librarian import candidates as C

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "meditations"


def _marks(*texts, slug="book", book="A Book"):
    return [{"book": book, "slug": slug, "id": f"kh:{i}", "text": t, "color": None,
             "location": str(i), "kind": "highlight"} for i, t in enumerate(texts)]


# ── phrase construction ──────────────────────────────────────────────────────────────────────

def test_a_candidate_is_never_one_or_two_words():
    marks = _marks("It is in thy power to retire into thyself and to be at rest")
    stop = C.corpus_stoplist(marks)
    ph = C.candidate_phrases(marks[0]["text"], stop, C.phrase_rarity(marks))
    assert ph, "a 14-token highlight must yield candidates"
    assert all(len(p.split()) in (C.NGRAM_SHORT, C.NGRAM) for p in ph), ph


def test_a_short_highlight_may_use_three_words_and_a_long_one_uses_four():
    stop = set(C.FUNCTION_WORDS)
    df = collections.Counter()
    short = C.candidate_phrases("retire into thyself daily", stop, df)
    long_ = C.candidate_phrases("it is in thy power to retire into thyself and be at rest", stop, df)
    assert short and all(len(p.split()) == C.NGRAM_SHORT for p in short), short
    assert long_ and all(len(p.split()) == C.NGRAM for p in long_), long_


def test_a_phrase_of_pure_function_words_is_never_a_candidate():
    stop = set(C.FUNCTION_WORDS)
    assert C.candidate_phrases("of the same as it is to be", stop, collections.Counter()) == []


def test_the_stoplist_absorbs_a_token_common_across_the_reader_s_own_books():
    """A hand-written stoplist cannot know that THIS library says 'leader' in every book."""
    marks = []
    for i in range(10):
        marks += _marks(f"the leader must decide item {i} clearly", slug=f"b{i}", book=f"Book {i}")
    marks += _marks("a rare phrase about porcupine husbandry entirely", slug="b9x", book="Book 9x")
    stop = C.corpus_stoplist(marks)
    assert "leader" in stop and "porcupine" not in stop
    ph = C.candidate_phrases("the leader must decide item 3 clearly", stop, C.phrase_rarity(marks))
    assert all("leader must" not in p or len([t for t in p.split() if t not in stop]) >= 2 for p in ph)


def test_phrases_do_not_overlap_and_are_capped():
    marks = _marks(" ".join(f"distinct{i}" for i in range(40)))
    ph = C.candidate_phrases(marks[0]["text"], set(C.FUNCTION_WORDS), collections.Counter(), per_highlight=3)
    assert len(ph) == 3
    starts = [marks[0]["text"].split().index(p.split()[0]) for p in ph]
    assert all(abs(a - b) >= C.NGRAM for i, a in enumerate(starts) for b in starts[i + 1:])


# ── adjudication ─────────────────────────────────────────────────────────────────────────────

def test_a_phrase_over_the_noise_floor_is_noise_not_evidence(tmp_path):
    """The ancestor of this check matched a phrase in 782 files and called all 782 evidence."""
    marks = _marks("retire into thyself and be at rest")
    hits = {p: [(f"/f{i}.md", 1, "line") for i in range(60)] for p in ["retire into thyself and"]}
    rows = C.adjudicate(marks, {0: ["retire into thyself and"]}, hits, n_files=100)
    assert rows[0]["status"] == "noise" and rows[0]["noise"][0]["files"] == 60
    assert rows[0]["noise_floor"] == max(C.NOISE_MIN, 2)


def test_a_phrase_under_the_floor_is_a_receipt_with_file_and_line():
    marks = _marks("retire into thyself and be at rest")
    hits = {"retire into thyself and": [("/j/2026-03-04.md", 8, "Tried the retiring today.")]}
    rows = C.adjudicate(marks, {0: ["retire into thyself and"]}, hits, n_files=100)
    r = rows[0]
    assert r["status"] == "candidate"
    assert r["receipts"][0]["file"].endswith("2026-03-04.md") and r["receipts"][0]["line"] == 8
    assert "Tried the retiring" in r["receipts"][0]["quote"]


def test_no_hit_anywhere_is_unapplied():
    marks = _marks("a passage never used")
    rows = C.adjudicate(marks, {0: ["a passage never used"]}, {}, n_files=100)
    assert rows[0]["status"] == "unapplied" and rows[0]["receipts"] == []


# ── searching the reader's surfaces ──────────────────────────────────────────────────────────

def test_the_search_excludes_everything_derived_from_the_corpus(tmp_path):
    """A book node quotes its own highlights. Searching it would corroborate the whole library
    against itself — the failure that makes a matcher look perfect and mean nothing."""
    surf = tmp_path / "vault"
    (surf / "books").mkdir(parents=True)
    (surf / "journal").mkdir()
    (surf / "books" / "meditations.md").write_text("retire into thyself and be at rest\n", encoding="utf-8")
    (surf / "distill-meditations.md").write_text("retire into thyself and be at rest\n", encoding="utf-8")
    (surf / "journal" / "day.md").write_text("I tried to retire into thyself and it worked\n", encoding="utf-8")
    files = C.surface_files([surf], exclude=[tmp_path / "out"])
    names = {f.name for f in files}
    assert names == {"day.md"}, names


def test_frontmatter_is_not_searched_and_line_numbers_point_at_the_body(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntitle: retire into thyself and\n---\n\nfirst body line\n"
                 "he wrote retire into thyself and rest\n", encoding="utf-8")
    hits = C.search({"retire into thyself and"}, [f], {4})
    assert len(hits["retire into thyself and"]) == 1
    _, line, quote = hits["retire into thyself and"][0]
    assert quote.startswith("he wrote retire") and line == 3


def test_a_phrase_split_across_two_lines_still_matches(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("he said retire into\nthyself and be at rest\n", encoding="utf-8")
    hits = C.search({"retire into thyself and"}, [f], {4})
    assert hits, "normalisation must survive a line break"


# ── end to end on the fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def merged(tmp_path_factory):
    out = tmp_path_factory.mktemp("rg")
    env = {**os.environ, "RG_OUT": str(out)}
    for cmd in ([sys.executable, "-m", "capture.kindle", "clippings",
                 str(FIXTURE / "clippings" / "My Clippings.txt"), "--out", str(out / "kindle-highlights.json")],
                [sys.executable, str(ROOT / "corpus" / "merge_corpus.py")]):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
        assert r.returncode == 0, r.stderr
    return out


def test_the_fixture_journal_corroborates_a_marked_passage(merged, tmp_path):
    """The synthetic reader journal paraphrases one Meditations passage and mentions a decoy."""
    out = tmp_path / "candidates.jsonl"
    r = subprocess.run([sys.executable, str(ROOT / "agents" / "librarian" / "candidates.py"),
                        "--corpus", str(merged / "merged"), "--surfaces", str(FIXTURE / "reader-journal"),
                        "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    assert rows, "the fixture corpus must produce marks"
    assert r.stdout.splitlines()[0].startswith("candidates: marks=")
    assert "sorted marks-per-book" in r.stdout
    corroborated = [x for x in rows if x["status"] == "candidate"]
    assert corroborated, "the journal paraphrases a highlight; at least one mark must have a receipt"
    rec = corroborated[0]["receipts"][0]
    assert rec["file"].endswith(".md") and rec["line"] > 0 and rec["quote"]
    assert any(x["status"] == "unapplied" for x in rows), "not every mark can have been used"


def test_an_empty_corpus_is_refused_not_reported_as_zero(tmp_path):
    (tmp_path / "merged").mkdir()
    r = subprocess.run([sys.executable, str(ROOT / "agents" / "librarian" / "candidates.py"),
                        "--corpus", str(tmp_path / "merged"), "--surfaces", str(FIXTURE / "reader-journal"),
                        "--out", str(tmp_path / "c.jsonl")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 3 and "REFUSED" in r.stderr


def test_no_surfaces_says_so_instead_of_reporting_everything_unapplied(merged, tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "agents" / "librarian" / "candidates.py"),
                        "--corpus", str(merged / "merged"), "--surfaces", "",
                        "--out", str(tmp_path / "c.jsonl")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0
    assert "BY CONSTRUCTION" in r.stdout, r.stdout


def test_the_run_is_deterministic(merged, tmp_path):
    outs = []
    for i in range(2):
        o = tmp_path / f"c{i}.jsonl"
        subprocess.run([sys.executable, str(ROOT / "agents" / "librarian" / "candidates.py"),
                        "--corpus", str(merged / "merged"), "--surfaces", str(FIXTURE / "reader-journal"),
                        "--out", str(o)], capture_output=True, text=True, cwd=ROOT, check=True)
        outs.append(o.read_text(encoding="utf-8"))
    assert outs[0] == outs[1]


def test_a_small_library_still_produces_candidates():
    """A document-frequency stoplist needs documents: on one book every token appears in 100% of
    the books, so the naive rule stops the whole vocabulary and the tool returns nothing —
    which looks exactly like a clean run with nothing to report."""
    one = _marks("It is in thy power to retire into thyself and to be at rest")
    stop = C.corpus_stoplist(one)
    assert "retire" not in stop and "thyself" not in stop
    assert C.candidate_phrases(one[0]["text"], stop, C.phrase_rarity(one))
    many = []
    for i in range(C.STOP_MIN_BOOKS + 1):
        many += _marks(f"the leader must decide item {i} clearly", slug=f"b{i}", book=f"Book {i}")
    assert "leader" in C.corpus_stoplist(many)


def test_a_file_that_quotes_the_corpus_is_a_mirror_not_a_receipt():
    """Measured on the reference corpus: one review file holding the scanned pages supplied 60 of
    the first 102 receipts, and each was the book quoting itself. Path rules cannot catch it —
    the file had an ordinary name in an ordinary project directory."""
    hits = {f"phrase {i}": [("/proj/calibration-review.md", i, "> quoted page text")] for i in range(20)}
    hits["a real one"] = [("/proj/journal.md", 4, "I tried a real one today")]
    mirror = C.mirrors(hits)
    assert mirror == {"/proj/calibration-review.md"}
    marks = _marks("phrase 0 body", "a real one body")
    rows = C.adjudicate(marks, {0: ["phrase 0"], 1: ["a real one"]}, hits, n_files=100, mirror_files=mirror)
    assert rows[0]["status"] == "unapplied", "a mirrored hit is not evidence"
    assert rows[1]["status"] == "candidate" and rows[1]["receipts"][0]["file"].endswith("journal.md")


def test_a_file_with_a_few_hits_is_never_called_a_mirror():
    hits = {f"phrase {i}": [("/proj/journal.md", i, "line")] for i in range(C.MIRROR_PHRASES)}
    assert C.mirrors(hits) == set()


def test_a_phrase_of_the_language_is_not_a_phrase_of_the_book():
    """The first honest run on the reference library returned 'a leap of faith', 'does the heavy
    lifting' and 'vp of engineering' as receipts — every match real, every one meaningless. A
    phrase that could have come from anywhere is evidence of nothing."""
    marks = []
    for i in range(20):                                   # 'leap of faith' is everywhere here
        marks += _marks(f"it takes a leap of faith to decide item {i}", slug=f"b{i}", book=f"Book {i}")
    marks += _marks("the porcupine husbandry manual says otherwise entirely", slug="rare", book="Rare Book")
    stop, df = C.corpus_stoplist(marks), C.phrase_rarity(marks)
    n = len({m["slug"] for m in marks})
    common = C.candidate_phrases("it takes a leap of faith to decide item 3", stop, df, n_books=n)
    assert all("leap of faith" not in p for p in common), common
    rare = C.candidate_phrases("the porcupine husbandry manual says otherwise entirely", stop, df, n_books=n)
    assert rare, "a phrase distinctive to one book must survive"


def test_distinctiveness_is_not_applied_to_a_library_too_small_to_measure_it():
    one = _marks("It is in thy power to retire into thyself and to be at rest")
    assert C.candidate_phrases(one[0]["text"], C.corpus_stoplist(one), C.phrase_rarity(one), n_books=1)
