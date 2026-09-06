"""vault/build_nodes.py — the node contract and every rule the builder enforces, on the fixture.
The merged corpus is built once per module by running corpus/merge_corpus.py on the parsed
fixture; each test gets its own vault."""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

from capture.kindle import clippings
from capture.kindle.schema import to_kindle_json, write_kindle_json
from vault import build_nodes

ROOT = pathlib.Path(__file__).resolve().parents[1]
FX = ROOT / "fixtures" / "meditations"


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> pathlib.Path:
    out = tmp_path_factory.mktemp("out")
    (out / "bookcorpus").mkdir()
    books = clippings.parse_clippings_file(FX / "clippings" / "My Clippings.txt")
    write_kindle_json(out / "kindle-highlights.json", to_kindle_json(books, source="clippings"))
    r = subprocess.run([sys.executable, str(ROOT / "corpus" / "merge_corpus.py")],
                       env={**os.environ, "RG_OUT": str(out)}, capture_output=True, text=True, cwd=str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    return out / "merged"


def _fm(path: pathlib.Path) -> dict:
    m = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, "node has no frontmatter"
    return dict(line.split(":", 1) for line in m.group(1).split("\n") if ":" in line)


def test_node_frontmatter_matches_the_contract(corpus, tmp_path):
    stats = build_nodes.build(corpus, tmp_path)
    node = tmp_path / "books" / "meditations.md"
    assert stats["written"] == 1 and node.exists()
    fm = {k: v.strip() for k, v in _fm(node).items()}
    assert fm["name"] == '"Meditations"' and fm["type"] == "book" and fm["source"] == "apply-what-you-read"
    assert fm["asin"].startswith("x") and fm["kindle_highlights"] == "35" and fm["typed_notes"] == "5"
    assert fm["pages_captured"] == "0" and fm["highlight_colors"] == "null" and fm["marks"] == "null"
    assert fm["distilled"] == "false" and fm["related"] == "[]"
    body = node.read_text(encoding="utf-8")
    assert "# Meditations" in body and "**Kindle:** 35 highlights" in body and "*Not yet distilled.*" in body


def test_hand_authored_fields_survive_a_rebuild(corpus, tmp_path):
    build_nodes.build(corpus, tmp_path)
    node = tmp_path / "books" / "meditations.md"
    text = node.read_text(encoding="utf-8")
    text = text.replace("related: []", "related:\n  - \"[[some-other-book]]\"\nstatus: keep\noutcome: applied\napplied_in: journal", 1)
    node.write_text(text, encoding="utf-8")
    stats = build_nodes.build(corpus, tmp_path)
    assert stats["written"] == 1
    fm = _fm(node)
    assert "related" in fm and "status" in fm and "outcome" in fm and "applied_in" in fm
    assert '  - "[[some-other-book]]"' in node.read_text(encoding="utf-8")


def test_unchanged_rebuild_keeps_mtime(corpus, tmp_path):
    build_nodes.build(corpus, tmp_path)
    node = tmp_path / "books" / "meditations.md"
    before = node.stat().st_mtime_ns
    time.sleep(0.02)
    stats = build_nodes.build(corpus, tmp_path)
    assert stats["kept"] == 1 and stats["written"] == 0
    assert node.stat().st_mtime_ns == before


def test_orphan_is_moved_dated_never_deleted(corpus, tmp_path):
    build_nodes.build(corpus, tmp_path)
    stale = tmp_path / "books" / "a-book-that-left.md"
    stale.write_text("---\nname: gone\ntype: book\n---\n# gone\n", encoding="utf-8")
    stats = build_nodes.build(corpus, tmp_path)
    assert stats["orphaned"] == 1 and not stale.exists()
    moved = list((tmp_path / "books" / "_orphaned").glob("a-book-that-left.*.md"))
    assert len(moved) == 1 and moved[0].read_text(encoding="utf-8").startswith("---\nname: gone")


def test_empty_corpus_is_refused_and_nothing_is_orphaned(corpus, tmp_path):
    build_nodes.build(corpus, tmp_path)
    empty = tmp_path / "empty-corpus"
    empty.mkdir()
    stats = build_nodes.build(empty, tmp_path)
    assert stats.get("refused") is True and stats["orphaned"] == 0
    assert (tmp_path / "books" / "meditations.md").exists()
    assert build_nodes.main(["--vault", str(tmp_path), "--corpus", str(empty)]) == 2


def test_basename_collision_is_refused_loudly(corpus, tmp_path, capsys):
    other = tmp_path / "notes" / "meditations.md"
    other.parent.mkdir(parents=True)
    other.write_text("# my own note called meditations\n", encoding="utf-8")
    stats = build_nodes.build(corpus, tmp_path)
    assert stats["collisions"] == 1 and stats["written"] == 0
    assert not (tmp_path / "books" / "meditations.md").exists()
    assert "COLLISION" in capsys.readouterr().err
    assert build_nodes.main(["--vault", str(tmp_path), "--corpus", str(corpus)]) == 1


def test_distillation_is_joined_with_its_frontmatter_stripped(corpus, tmp_path):
    d = tmp_path / "distill"
    d.mkdir()
    dist = d / "distill-meditations.md"
    dist.write_text("---\nname: Meditations\ntype: distillation\nfidelity: full-text\n---\n"
                    "*[from the full text]*\n\n**The 20% — what carries the book**\n1. Retire into yourself.\n",
                    encoding="utf-8")
    before = dist.read_bytes()
    stats = build_nodes.build(corpus, tmp_path)
    node = (tmp_path / "books" / "meditations.md").read_text(encoding="utf-8")
    assert "distilled: true" in node and "Retire into yourself." in node
    assert "fidelity: full-text" not in node, "the distillation's frontmatter must not be inlined"
    assert dist.read_bytes() == before, "the builder never writes into a distillation"
    assert stats["stranded"] == 0
    (d / "distill-a-slug-with-no-book.md").write_text("---\nname: x\n---\nbody\n", encoding="utf-8")
    assert build_nodes.build(corpus, tmp_path)["stranded"] == 1


def test_unwritable_vault_spools_the_node(corpus, tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root ignores mode bits")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "books").mkdir()
    (vault / "books").chmod(0o500)
    try:
        stats = build_nodes.build(corpus, vault, spool_dir=tmp_path / "spool")
        assert stats["spooled"] == 1 and (tmp_path / "spool" / "books" / "meditations.md").exists()
        assert build_nodes.main(["--vault", str(vault), "--corpus", str(corpus)]) == 3
    finally:
        (vault / "books").chmod(0o700)


def test_vault_is_required_on_the_cli(corpus):
    env = {k: v for k, v in os.environ.items() if k != "VAULT"}
    r = subprocess.run([sys.executable, str(ROOT / "vault" / "build_nodes.py"), "--corpus", str(corpus)],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 2 and "--vault" in r.stderr
