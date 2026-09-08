"""Praxis: the proposer proposes, the skeptic refuses, and neither does the other's job."""
from __future__ import annotations

import json
import os
import pathlib
import re
import stat
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "agents" / "praxis" / "praxis-one.sh"


def _two_stage_stub(tmp_path, candidates, adjudicated, first_rc=0, second_rc=0):
    """A stub `claude` that plays the qualifier on its first call and the skeptic on its second,
    so the two-pass shape itself is under test."""
    marker = tmp_path / "call-count"
    stub = tmp_path / "claude"
    stub.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys
marker = pathlib.Path({str(marker)!r})
n = int(marker.read_text()) if marker.exists() else 0
marker.write_text(str(n + 1))
out = pathlib.Path({str(tmp_path / "out" / "praxis")!r}); out.mkdir(parents=True, exist_ok=True)
vault = pathlib.Path({str(tmp_path / "vault" / "praxis")!r}); vault.mkdir(parents=True, exist_ok=True)
if n == 0:
    cands = {candidates!r}
    if cands is not None:
        (out / "candidates.jsonl").write_text("\\n".join(json.dumps(c) for c in cands) + "\\n")
    sys.exit({first_rc})
else:
    adj = {adjudicated!r}
    if adj is not None:
        (vault / "praxis.jsonl").write_text("\\n".join(json.dumps(a) for a in adj) + "\\n")
    sys.exit({second_rc})
""", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub


def _run(tmp_path, stub):
    env = {**os.environ, "VAULT": str(tmp_path / "vault"), "RG_OUT": str(tmp_path / "out"),
           "CLAUDE_BIN": str(stub), "PRAXIS_TIMEOUT_SECS": "30", "READER_SURFACES": str(tmp_path / "w")}
    return subprocess.run(["bash", str(RUN)], capture_output=True, text=True, env=env)


REC = {"id": "px:1", "claim": "Take the ten minutes before the first meeting.",
       "citation": "Meditations loc 269",
       "argument": "The retreat people seek elsewhere is available at any moment.",
       "application": {"kind": "current", "evidence": ["journal/2026-03-11.md:8"], "what": "did it twice"}}


def test_both_passes_run_and_the_counts_are_reported(tmp_path):
    applied = {**REC, "adjudication": {"verdict": "applied"}}
    rejected = {**REC, "id": "px:2", "adjudication": {"verdict": "rejected"}}
    r = _run(tmp_path, _two_stage_stub(tmp_path, [REC, {**REC, "id": "px:2"}], [applied, rejected]))
    assert r.returncode == 0, r.stderr
    assert "2 candidate(s) proposed" in r.stdout
    assert "applied=1" in r.stdout and "rejected=1" in r.stdout


def test_a_qualifier_that_writes_nothing_is_a_failure_not_a_clean_run(tmp_path):
    """An empty proposal and a successful run look identical from outside; they must not."""
    r = _run(tmp_path, _two_stage_stub(tmp_path, None, None))
    assert r.returncode == 1 and "wrote no candidates" in r.stderr


def test_nothing_surviving_adjudication_is_reported_as_a_result_not_an_error(tmp_path):
    none_applied = {**REC, "adjudication": {"verdict": "rejected"}}
    r = _run(tmp_path, _two_stage_stub(tmp_path, [REC], [none_applied]))
    assert r.returncode == 0
    assert "Nothing survived adjudication" in r.stdout and "not an error" in r.stdout


def test_a_failing_pass_stops_the_run(tmp_path):
    r = _run(tmp_path, _two_stage_stub(tmp_path, [REC], None, second_rc=3))
    assert r.returncode == 1 and "adjudicator exited 3" in r.stderr


def test_the_proposer_cannot_write_to_the_vault(tmp_path):
    """The tool surfaces differ by design: the agent that proposes records must not be able to
    mark its own homework, even by accident."""
    src = RUN.read_text(encoding="utf-8")
    qualify = re.search(r'run_agent qualify\.md "([^"]+)"', src).group(1)
    adjudicate = re.search(r'run_agent adjudicate\.md "([^"]+)"', src).group(1)
    assert "$VAULT" not in qualify, qualify
    assert "$RG_OUT/praxis" in qualify
    assert "$VAULT/praxis" in adjudicate


def test_the_contract_and_the_prompts_keep_their_load_bearing_rules():
    schema = re.sub(r"\s+", " ", (ROOT / "agents" / "praxis" / "schema.md").read_text(encoding="utf-8"))
    assert "No citation, no record" in schema
    assert "Empty only for `hypothetical`" in schema
    assert "The proposer never adjudicates" in schema
    # Prose wraps; the rules are about words, not line breaks.
    q = re.sub(r"\s+", " ", (ROOT / "agents" / "praxis" / "qualify.md").read_text(encoding="utf-8"))
    assert "Quote both sides or discard" in q
    assert "Never infer use from similarity" in q
    assert "A candidate is a question, not a finding" in q, "the matcher's candidates are not findings"
    a = re.sub(r"\s+", " ", (ROOT / "agents" / "praxis" / "adjudicate.md").read_text(encoding="utf-8"))
    assert "twenty-seven" in a.lower(), "the 27-1 result is the reason refusal is the default"
    assert "`unverified`, not `applied`" in a
