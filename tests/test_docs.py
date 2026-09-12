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
    # Two labels now. "Proven, landing" was retired when the last agent it described shipped; a
    # label defined and never used is a promise the table does not keep.
    assert "**Shipped**" in readme and "**Designed**" in readme
    body = readme.split("## Status", 1)[-1].split("\n## ", 1)[0]
    assert "Proven, landing" not in body, "a status label must be used by the table that defines it"
    for doc in DOCS:
        if doc.name == "README.md":
            continue
        text = doc.read_text(encoding="utf-8")
        assert "**Proven, landing** —" not in text, f"{doc.name} restates the label definitions"


def test_every_example_citation_resolves_in_the_shipped_fixture():
    """The docs promise "a citation you can check in ten seconds". An example citation pointing at
    a location the fixture does not contain breaks that promise in the most-read text in the
    project — and it shipped once: loc 496, in a fixture whose range is 100–362."""
    import csv
    fixture = ROOT / "fixtures" / "meditations" / "readwise" / "highlights.csv"
    rows = list(csv.DictReader(fixture.open(encoding="utf-8")))
    locs = {r["Location"].strip() for r in rows if r.get("Location", "").strip().isdigit()}
    assert locs, "the fixture must carry locations to check against"
    bad = []
    for p in sorted(ROOT.rglob("*.md")) + sorted(ROOT.rglob("*.py")) + sorted(ROOT.rglob("*.sh")):
        if any(x in p.parts for x in (".venv", "out", "fixtures", "__pycache__")):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in re.finditer(r"Meditations[, ]+loc(?:ation)? (\d+)", line):
                if m.group(1) not in locs:
                    bad.append(f"{p.relative_to(ROOT)}:{i} cites loc {m.group(1)}")
    assert not bad, "example citations must resolve in the fixture: " + "; ".join(bad)


def test_the_agent_brief_exists_under_both_names_and_stays_in_step():
    """Someone pointing an agent at this repo is a supported path, so the repo has to answer when
    one arrives. Claude Code reads CLAUDE.md; other harnesses read AGENTS.md. Two names, one brief,
    and a test so they cannot drift."""
    a = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    c = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert a.strip(), "AGENTS.md must not be empty"
    # Equivalence OR a pointer. Claude Code loads CLAUDE.md automatically, so a copy would put the
    # brief into context twice in the very invocation the README suggests; a pointer must actually
    # point, which is what this checks.
    assert a in c or "AGENTS.md" in c, "CLAUDE.md must carry the brief or point at it by name"
    if a not in c:
        assert len(c) < 1200, "a pointer that long is a second brief drifting out of step"
    for required in ("Ask these five things", "do not re-litigate", "KNOWN-GAPS",
                     "quickstart.sh", "READER_SURFACES", "Do not start building"):
        assert required in a, f"the agent brief must cover: {required}"


def test_the_agent_brief_points_only_at_files_that_exist():
    """A brief that names a missing file sends an agent looking for it, which is worse than saying
    nothing."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    missing = []
    for m in re.finditer(r"`([a-zA-Z0-9_./-]+\.(?:md|py|sh))`", text):
        rel = m.group(1)
        if rel.startswith(("http", "-")) or "*" in rel:
            continue
        if not (ROOT / rel).exists():
            missing.append(rel)
    assert not missing, f"the agent brief names files that do not exist: {sorted(set(missing))}"


def test_every_command_in_the_agent_brief_is_real():
    """The brief's whole value is that an agent can follow it without reading the source. A command
    that does not exist, or a flag a script does not take, spends exactly the session the brief is
    meant to save."""
    import shlex
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    block = re.search(r"```bash\n(.*?)```", text, re.S)
    assert block, "the brief must carry a runnable sequence, not just file names"
    problems = []
    for raw in block.group(1).splitlines():
        line = raw.strip().lstrip("#").strip()
        if not line or line.startswith(("export ", "source ", "rm ", "or:", "add ", "later:")):
            continue
        try:
            parts = shlex.split(line)
        except ValueError:
            continue
        if parts[0] not in ("python", "bash"):
            continue
        # the script or module the line runs
        if parts[1] == "-m":
            mod = parts[2].replace(".", "/")
            if not (ROOT / mod).exists() and not (ROOT / (mod + ".py")).exists():
                problems.append(f"no module {parts[2]}")
            target, flags = None, parts[3:]
        else:
            target, flags = parts[1], parts[2:]
            if not (ROOT / target).exists():
                problems.append(f"no such file: {target}")
                continue
        if target and target.endswith(".py"):
            src = (ROOT / target).read_text(encoding="utf-8")
            for f in [x for x in flags if x.startswith("--")]:
                if f'"{f}"' not in src and f"'{f}'" not in src:
                    problems.append(f"{target} does not take {f}")
    assert not problems, "the agent brief names commands that do not work: " + "; ".join(problems)


def test_the_agent_brief_does_not_contradict_the_known_gaps():
    """Two documents disagreed about whether a space in a vault path breaks the agents. A
    measurement settled it — a comma does, a space does not — and both files must say so."""
    brief = re.sub(r"\s+", " ", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))
    gaps = re.sub(r"\s+", " ", (ROOT / "docs" / "reference" / "KNOWN-GAPS.md").read_text(encoding="utf-8"))
    assert "comma" in brief and "comma" in gaps
    assert "spaces or parentheses produces broken" not in gaps, "the stale claim is back"
    assert "Spaces and parentheses are fine" in brief


def test_the_agent_brief_is_reachable_from_the_repository_root():
    """The README tells a reader to point their agent here and say "read AGENTS.md". If the brief
    is written but never shipped, that sentence sends the agent looking for a file that is not
    there — which happened: the manifest rows were added with the wrong source path and the export
    dropped both names silently."""
    for name in ("AGENTS.md", "CLAUDE.md"):
        assert (ROOT / name).is_file(), f"{name} must sit at the repository root"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "AGENTS.md" in readme, "the README must name the brief it tells the reader to invoke"


def _corpus_totals():
    """Read the corpus totals out of the table itself, so the check below is derived from the
    document it polices rather than from a list kept in this file by hand."""
    table = (ROOT / "docs" / "reference" / "CORPUS.md").read_text(encoding="utf-8")
    label_unit = {"books in the merged corpus": "books", "e-reader highlights": "highlights",
                  "photographed pages": "pages", "**marks** (highlights + pages)": "marks"}
    totals = {}
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] in label_unit:
            totals[label_unit[cells[0]]] = cells[1].strip("*").strip()
    assert len(totals) == len(label_unit), f"the corpus table lost a row: got {sorted(totals)}"
    return totals


_SCOPE = re.compile(r"(?:the|one|this)\s+(?:reference\s+|real\s+|merged\s+)?corpus", re.I)
_UNIT = re.compile(r"\b([\d,]{2,7})\s+(?:e-reader\s+|photographed\s+|merged\s+)?"
                   r"(books|book files|highlights|marks|pages)\b", re.I)
_ASSERTS = re.compile(r"corpus\s+(?:contains|holds|has|is|of)\b", re.I)


def test_no_clause_about_the_corpus_states_a_total_the_table_denies():
    """The derived half of the promise. A security reviewer probed the hand-written denylist below
    with five invented totals and it caught one; four shipped silently, which is exactly the drift
    the corpus page exists to stop. So this half reads the totals out of the table and checks every
    clause that talks about the corpus against them.

    Scoped to the clause, not the sentence or the file, because "the most-marked book has 595
    marks" is a different quantity from "the corpus holds 5,225 marks" and only the second is a
    total. That scoping is also the limit: a total stated in a clause that never says "corpus"
    is not caught here, and docs/reference/CORPUS.md says so rather than implying otherwise."""
    totals = _corpus_totals()
    bad = []
    for path in sorted(ROOT.rglob("*.md")):
        if any(x in path.parts for x in (".venv", "out", "fixtures", "__pycache__")):
            continue
        if path.name == "CORPUS.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in _SCOPE.finditer(text):
            end = len(text)
            for term in (".", ";", "\n\n"):
                i = text.find(term, m.end())
                if i != -1:
                    end = min(end, i)
            start = max(text.rfind("\n\n", 0, m.start()), text.rfind(". ", 0, m.start()), 0)
            clause = text[start:end]
            found = list(_UNIT.finditer(clause))
            # A number is a corpus TOTAL only when it is stated as one: either inside a descriptor
            # list ("88 books, 5,225 marks, 800 photographed pages") or after "the corpus
            # contains/holds/has". Everything else in a clause that happens to mention the corpus
            # is a sub-count — "44 books holding 214 highlights" is what a bad filter discarded,
            # and "one book went from 97 to 376 highlights" is one book. Policing those would make
            # this test fail on true sentences, which is how a check gets deleted.
            asserted = _ASSERTS.search(clause)
            for i, u in enumerate(found):
                listed = False
                for other in (found[i - 1] if i else None, found[i + 1] if i + 1 < len(found) else None):
                    if other is None:
                        continue
                    lo, hi = sorted([(u.start(), u.end()), (other.start(), other.end())])
                    if re.fullmatch(r"[\s,]*(?:and)?[\s,]*", clause[lo[1]:hi[0]] or ""):
                        listed = True
                if not (listed or (asserted and u.start() > asserted.end())):
                    continue
                value, unit = u.group(1), u.group(2).lower()
                if unit in totals and value != totals[unit]:
                    line = text[:start + u.start()].count("\n") + 1
                    bad.append(f"{path.relative_to(ROOT)}:{line} '{u.group(0)}' — the table says "
                               f"{totals[unit]} {unit}")
    assert not bad, "clauses about the corpus contradict docs/reference/CORPUS.md: " + \
                    "; ".join(sorted(set(bad)))


def test_no_document_contradicts_the_corpus_table():
    """Six independent reviewers found the same defect: the corpus figures drifted across the docs
    — 88 books in nine places and 89 in four, and a "worst book" number the project's own appendix
    said was impossible. CONTRIBUTING asks that every number cite its artifact; this makes that
    mechanical for the handful of figures that describe the corpus as a whole.

    Deliberately narrow. It does not police every number in the docs — "four books over 300 marks"
    and "107 highlights" in one book are different quantities, not contradictions. It polices the
    corpus totals, where drift is silent and a reader cannot tell which figure to believe."""
    table = (ROOT / "docs" / "reference" / "CORPUS.md").read_text(encoding="utf-8")
    for expected in ("| 88 |", "| 4,425 |", "| 800 |", "| 5,225 |", "| 460 |", "| 595 |",
                     "| 5,211 |", "| 21 |"):
        assert expected in table, f"the corpus table lost {expected}"
    # The first version of this page shipped two defects of exactly the kind it exists to stop:
    # it omitted the pages figure from this list while nine documents carried a stale one, and it
    # explained the 89th file in out/merged/ as a dropped book when it is _manifest.json.
    assert "_manifest.json" in table, "the 88-vs-89 row must name the manifest file"
    # values that WOULD contradict the table if any document stated them as a corpus total
    contradictions = {
        r"\b89 books\b": "the corpus holds 88 books; 89 is the file count before the membership rule",
        r"\b490 (?:highlights|marks)\b": "no book has 490; the maxima are 460 highlights and 595 marks",
        r"\b5,211 highlights\b": "5,211 counts marks in both channels, not e-reader highlights",
        r"\b88 highlights\b": "88 is a book count",
        r"\b798\b": "the photographed-pages channel measures 800; 798 is withdrawn",
    }
    bad = []
    for p in sorted(ROOT.rglob("*.md")):
        if any(x in p.parts for x in (".venv", "out", "fixtures", "__pycache__")) or p.name == "CORPUS.md":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pattern, why in contradictions.items():
            for m in re.finditer(pattern, text):
                line = text[:m.start()].count("\n") + 1
                bad.append(f"{p.relative_to(ROOT)}:{line} '{m.group(0)}' — {why}")
    assert not bad, "documents contradict docs/reference/CORPUS.md: " + "; ".join(sorted(set(bad)))
