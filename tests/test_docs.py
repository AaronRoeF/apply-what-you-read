"""Documentation drift is the failure class this repository's own history warns about most:
a doc that names a retired script, a stale count, or a private path stays wrong silently.
These tests make the docs answerable to the tree."""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = sorted((ROOT / "docs").rglob("*.md")) + [ROOT / "README.md"]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# Repository-hygiene files the README links to; they sit beside the docs tree, not inside it.
HYGIENE = {"CONTRIBUTING.md", "LICENSE", "CODE_OF_CONDUCT.md", "CHANGELOG.md"}
SCRIPT_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|sh|js))`")
# Paths the docs may name before they exist: the README's status table labels them Proven,
# landing (v0.2) or Designed (v0.3). Remove each prefix from this set in the release that lands it.
PLANNED_PREFIXES = ("agents/praxis/", "agents/tutor/", "agents/librarian/", "capture/kindle/notebook_crawl.py")
PLANNED_BARE = {"extract.py", "candidates.py", "write.py", "adjudicate.py", "tutor.py", "build_praxis.py", "notebook_crawl.py"}
# The publish gate under the name CI runs it by.
GATE_COPY = {"tests/publish-checks.sh"}
# Shapes and stale claims only — never a list of private values (that is the release gate's job,
# with a pattern file that does not ship).
FORBIDDEN = [
    (r"\bAaron\b(?! Fulkerson)", "author's first name outside the byline"),
    (r"/Users/|/home/[a-z]|iCloud~", "absolute personal path"),
    (r"build_books\.py|BOOK_CATALOG_PROMPT", "retired name"),
    (r"28 refuted|twenty-eight were refuted|[Zz]ero survived|28/28", "stale graph result (it is 27–1)"),
    (r"[Zz]ero lines of agent code|[Nn]either (agent )?is built|designed but unbuilt", "stale agent status"),
    (r"(?<!stack )\btraces?\b", "the reserved word (use citation / receipt)"),
]


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(doc: pathlib.Path):
    text = doc.read_text(encoding="utf-8")
    bad = []
    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")) or target in HYGIENE:
            continue
        path = (doc.parent / target.split("#")[0]).resolve()
        if not path.exists():
            bad.append(target)
    assert not bad, f"{doc.relative_to(ROOT)}: unresolved links {bad}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_referenced_scripts_exist(doc: pathlib.Path):
    text = doc.read_text(encoding="utf-8")
    missing = []
    for name in set(SCRIPT_RE.findall(text)):
        if name.startswith(("http", "$", "<")) or name.startswith(PLANNED_PREFIXES):
            continue
        if name in PLANNED_BARE or name in GATE_COPY:
            continue
        if "/" in name:
            ok = (ROOT / name).exists() or (doc.parent / name).exists()
        else:
            ok = any(p.name == name for p in ROOT.rglob(name) if ".venv" not in p.parts)
        if not ok:
            missing.append(name)
    assert not missing, f"{doc.relative_to(ROOT)}: scripts named but absent {sorted(missing)}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_private_stale_or_reserved_words(doc: pathlib.Path):
    text = doc.read_text(encoding="utf-8")
    hits = []
    for pat, why in FORBIDDEN:
        for m in re.finditer(pat, text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"line {line}: {m.group(0)!r} ({why})")
    assert not hits, f"{doc.relative_to(ROOT)}:\n  " + "\n  ".join(hits[:12])


def test_docs_index_lists_every_doc():
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    for doc in DOCS:
        rel = doc.relative_to(ROOT / "docs") if doc.is_relative_to(ROOT / "docs") else None
        if rel is None or rel.name == "README.md":
            continue
        assert str(rel) in index, f"docs/README.md does not list {rel}"


def test_readme_defines_the_status_labels_once():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "**Shipped**" in readme and "**Proven, landing**" in readme and "**Designed**" in readme
    for doc in DOCS:
        if doc.name == "README.md":
            continue
        text = doc.read_text(encoding="utf-8")
        assert "**Proven, landing** —" not in text, f"{doc.name} restates the label definitions"
