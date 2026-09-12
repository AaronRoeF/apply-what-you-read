"""The distill surfaces: the skill file's contract, the swarm prompt's hygiene, the headless
runner's one hard check (a clean exit without output is a failure), and the workflow's meta."""
from __future__ import annotations

import json
import os
import pathlib
import re
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FX = ROOT / "fixtures" / "meditations"
# Shapes only, never values: an absolute personal path or an email address has no place in a
# prompt or a skill. (Value-level scanning is the release gate's job, with its own pattern file.)
PERSONAL = re.compile(r"/Users/|/home/[a-z]|iCloud~|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")


def _frontmatter(path: pathlib.Path) -> dict:
    m = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path.name} has no frontmatter"
    keys = {}
    cur = None
    for line in m.group(1).split("\n"):
        k = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if k:
            cur = k.group(1)
            keys[cur] = k.group(2)
        elif cur:
            keys[cur] += " " + line.strip()
    return keys


def test_skill_frontmatter_has_name_and_a_triggering_description():
    fm = _frontmatter(ROOT / "skills" / "distill" / "distill.md")
    assert fm["name"] == "distill"
    assert "distill [book]" in fm["description"] and "fidelity" in fm["description"].lower()


def test_skill_and_prompt_carry_no_personal_tokens_and_keep_the_load_bearing_rules():
    for f in (ROOT / "skills" / "distill" / "distill.md", ROOT / "agents" / "distill" / "DISTILL_PROMPT.md",
              ROOT / "agents" / "distill" / "README.md"):
        text = f.read_text(encoding="utf-8")
        assert not PERSONAL.search(text), f"{f.name}: {PERSONAL.search(text).group(0)!r}"
        assert "Thomas Dev Brown" in text
    skill = (ROOT / "skills" / "distill" / "distill.md").read_text(encoding="utf-8")
    assert "[from the full text]" in skill and "drop test" in skill and "$VAULT/distill/distill-" in skill
    prompt = (ROOT / "agents" / "distill" / "DISTILL_PROMPT.md").read_text(encoding="utf-8")
    for rule in ("RARITY IS NOT SIGNIFICANCE", "CORROBORATION IS THE SIGNAL", "NEVER INFER A GAP FROM MISSING DATA"):
        assert rule in prompt
    assert re.search(r"782\s+files", prompt) and "$READER_SURFACES" in prompt and "READER.md" in prompt


def _stub_claude(tmp_path: pathlib.Path, body: str | None) -> pathlib.Path:
    """A fake `claude` that writes (or does not write) the distillation the prompt asks for."""
    stub = tmp_path / "claude"
    if body is None:
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    else:
        stub.write_text("#!/bin/sh\n"
                        "out=$(printf '%s' \"$2\" | grep -o '/[^ ]*/distill/distill-[a-z0-9-]*\\.md' | head -1)\n"
                        "[ -n \"$out\" ] || { echo 'stub: no output path in prompt' >&2; exit 3; }\n"
                        "mkdir -p \"$(dirname \"$out\")\"\n"
                        f"cat > \"$out\" <<'EOF'\n{body}\nEOF\n"
                        "exit 0\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub


@pytest.fixture()
def merged(tmp_path) -> pathlib.Path:
    out = tmp_path / "out" / "merged"
    out.mkdir(parents=True)
    (out / "meditations.json").write_text(json.dumps({"book": "Meditations", "kindle_highlights": [], "photo_pages": []}), encoding="utf-8")
    (out / "meditations.md").write_text("# Meditations\n", encoding="utf-8")
    return tmp_path / "out"


def _run(tmp_path, out, stub, slug="meditations"):
    env = {**os.environ, "VAULT": str(tmp_path / "vault"), "RG_OUT": str(out), "CLAUDE_BIN": str(stub),
           "READER_CONTEXT": str(FX / "reader-context.md"), "DISTILL_TIMEOUT_SECS": "30"}
    return subprocess.run(["bash", str(ROOT / "agents" / "distill" / "distill-one.sh"), slug],
                          env=env, capture_output=True, text=True)


def test_distill_one_writes_the_prefixed_file_and_substitutes_the_prompt(tmp_path, merged):
    body = "---\nname: \"Meditations\"\ntype: distillation\nsource: apply-what-you-read\n---\n*[from partial text]*\n\n" + "x" * 300
    r = _run(tmp_path, merged, _stub_claude(tmp_path, body))
    assert r.returncode == 0, r.stdout + r.stderr
    out = tmp_path / "vault" / "distill" / "distill-meditations.md"
    assert out.exists() and "type: distillation" in out.read_text(encoding="utf-8")


def test_distill_one_treats_a_clean_exit_without_output_as_failure(tmp_path, merged):
    r = _run(tmp_path, merged, _stub_claude(tmp_path, None))
    assert r.returncode == 1 and "missing or trivial" in r.stderr


def test_distill_one_refuses_without_a_merged_record(tmp_path, merged):
    r = _run(tmp_path, merged, _stub_claude(tmp_path, "x" * 300), slug="no-such-book")
    assert r.returncode == 2 and "merge_corpus" in r.stderr


def test_workflow_meta_is_a_pure_literal_and_the_dispatch_check_is_first():
    js = (ROOT / "agents" / "distill" / "distill-library.workflow.js").read_text(encoding="utf-8")
    m = re.search(r"export const meta = \{(.*?)\n\}", js, re.S)
    assert m and "${" not in m.group(1) and "(" not in m.group(1).replace("(the", "")
    assert "shasum -a 256" in js and "MANIFEST MISMATCH" in js
    assert js.index("DISPATCH CHECK") < js.index("Then distill the book")


def test_distill_one_success_prints_no_job_control_noise(tmp_path, merged):
    """Killing the timeout watchdog must not make bash print 'Terminated: 15' — a stranger reads
    that as a failure right before the success line."""
    r = _run(tmp_path, merged, _stub_claude(tmp_path, "x" * 300))
    assert r.returncode == 0, r.stderr
    assert "Terminated" not in r.stderr + r.stdout, r.stderr


def test_the_runner_grants_the_verb_that_creates_a_file():
    """The agent must be able to create its output file, and the grant that lets it must be a rule
    the CLI actually honours. An earlier version of this test asserted a scoped `Write(//dir/**)`
    rule, which does not exist: the CLI prints "is not matched by file permission checks — only
    Edit(path) rules are" and ignores it. An Edit path rule covers every file-editing tool. What
    had actually blocked creation was a global Write in --disallowedTools, because deny beats
    allow. A security reviewer proved all of this against the live CLI; every stub here writes with
    a shell redirect and never asks permission, so the argv is the only place it is checkable."""
    src = (ROOT / "agents" / "distill" / "distill-one.sh").read_text(encoding="utf-8")
    tools = re.search(r'^TOOLS="([^"]+)"', src, re.M).group(1)
    assert "Edit(//$VAULT/distill/**)" in tools, tools
    assert "Write(" not in tools, f"a path-scoped Write rule is inert and the CLI warns on it: {tools}"
    denied = re.search(r'--disallowedTools "([^"]+)"', src).group(1)
    assert "Write" not in denied.split(","), f"Write is denied globally while being required: {denied}"
    for scope in ("Read(//$ROOT/**)", "Read(//$VAULT/**)"):
        assert scope in tools
    assert tools.count("Edit(") == 1, "editing stays scoped to one directory"
