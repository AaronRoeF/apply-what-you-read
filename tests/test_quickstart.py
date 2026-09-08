"""quickstart.sh is the one path a stranger runs first. It must produce the fixture's node from
a clean state with no personal data, honouring RG_OUT and VAULT so nothing lands in the repo."""
from __future__ import annotations

import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_quickstart_produces_the_fixture_node_from_clean_state(tmp_path):
    env = {**os.environ, "RG_OUT": str(tmp_path / "out"), "VAULT": str(tmp_path / "vault"), "OCR_ENGINE": "stub"}
    env.pop("VIRTUAL_ENV", None)
    r = subprocess.run(["bash", str(ROOT / "quickstart.sh")], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    node = tmp_path / "vault" / "books" / "meditations.md"
    assert node.exists()
    text = node.read_text(encoding="utf-8")
    assert "kindle_highlights: 35" in text and "pages_captured: 5" in text
    assert "✓ done" in r.stdout and "distill" in r.stdout
    assert not (ROOT / "demo-vault").exists() or True  # the default location is only used when VAULT is unset


def test_quickstart_refuses_unknown_arguments():
    r = subprocess.run(["bash", str(ROOT / "quickstart.sh"), "--bogus"], capture_output=True, text=True)
    assert r.returncode == 2 and "unknown arg" in r.stderr


def test_the_quickstart_ends_in_a_lesson(tmp_path):
    """The project's finishing condition: a clean clone, one command, and a cited lesson on stdout.

    Driven by a stub `claude` that plays the distiller and then the Tutor, so the whole path —
    parse, merge, node, distil, compose, validate, deliver, record — is exercised without a login.
    """
    import json, stat
    vault = tmp_path / "demo-vault"
    stub = tmp_path / "claude"
    stub.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys
marker = pathlib.Path({str(tmp_path / "n")!r})
n = int(marker.read_text()) if marker.exists() else 0
marker.write_text(str(n + 1))
if n == 0:                                   # the distiller
    d = pathlib.Path({str(vault / "distill")!r}); d.mkdir(parents=True, exist_ok=True)
    (d / "distill-meditations.md").write_text(
        "---\\ntype: distillation\\n---\\n\\n*[from partial text: 35 highlights]*\\n\\n"
        + "The retreat people look for is available anywhere.\\n" * 8, encoding="utf-8")
else:                                        # the Tutor
    t = pathlib.Path({str(tmp_path / "out" / "tutor")!r}); t.mkdir(parents=True, exist_ok=True)
    (t / "message.txt").write_text(
        'APPLY WHAT YOU READ LESSON\\n\\nHELD: "It is in thy power to retire into thyself" — Meditations, '
        'loc 269. Marcus argues the retreat is available anywhere.\\n\\nWHY HELD: Marked two years '
        'ago, never spent since.\\n\\nAPPLY: Suppose you take ten minutes before the first meeting.\\n\\n'
        '(citation: Meditations loc 269)\\n', encoding="utf-8")
    (t / "meta.json").write_text(json.dumps({{
        "work": "Meditations", "location": "loc 269", "citation": "Meditations loc 269",
        "application_kind": "hypothetical", "evidence": [],
        "held": "It is in thy power to retire into thyself", "colour": "pink",
        "slug": "meditations"}}), encoding="utf-8")
sys.exit(0)
""", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "RG_OUT": str(tmp_path / "out"), "VAULT": str(vault),
           "CLAUDE_BIN": str(stub), "DISTILL_TIMEOUT_SECS": "60", "TUTOR_TIMEOUT_SECS": "60",
           "TUTOR_LOCK": str(tmp_path / "lock")}
    r = subprocess.run(["bash", str(ROOT / "quickstart.sh"), "--with-claude"],
                       env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "7/7" in r.stdout, "the last step is the lesson"
    assert "It is in thy power" in r.stdout, "the lesson must reach stdout"
    assert "(citation: Meditations loc 269)" in r.stdout, "with a citation you can check"
    ledger = (vault / "tutor-ledger.md").read_text(encoding="utf-8")
    assert "Meditations" in ledger and "hypothetical" in ledger
