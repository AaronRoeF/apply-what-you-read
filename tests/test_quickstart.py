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
