"""The photographed-pages channel on the fixture: manifest → OCR seam (stub engine on every
platform, Apple Vision on macOS) → bookcorpus → merge with the Kindle channel → node."""
from __future__ import annotations

import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys

import pytest

from capture.kindle import clippings
from capture.kindle.schema import to_kindle_json, write_kindle_json
from capture.pages import manifest as manifest_mod
from capture.pages import ocr as ocr_mod
from vault import build_nodes

ROOT = pathlib.Path(__file__).resolve().parents[1]
FX = ROOT / "fixtures" / "meditations"
PAGES = FX / "pages"


def _run(script: str, out: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / script), *args], env={**os.environ, "RG_OUT": str(out)},
                          capture_output=True, text=True, cwd=str(out))


@pytest.fixture(scope="module")
def out(tmp_path_factory) -> pathlib.Path:
    """manifest + stub OCR + bookcorpus + kindle + merge, once per module."""
    out = tmp_path_factory.mktemp("out")
    man = manifest_mod.build(PAGES)
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    assert ocr_mod.main(["--dir", str(PAGES), "--out", str(out / "ocr.jsonl"), "--engine", "stub"]) == 0
    r = _run("corpus/build_bookcorpus.py", out)
    assert r.returncode == 0, r.stdout + r.stderr
    books = clippings.parse_clippings_file(FX / "clippings" / "My Clippings.txt")
    write_kindle_json(out / "kindle-highlights.json", to_kindle_json(books, source="clippings"))
    r = _run("corpus/merge_corpus.py", out)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def test_manifest_one_note_per_book_folder_with_sidecar_title():
    man = manifest_mod.build(PAGES)
    assert man["root"] == str(PAGES.resolve()) and man["stats"]["notes"] == 1
    n = man["notes"][0]
    assert n["book"] == "Meditations" and n["author"] == "Marcus Aurelius" and n["asin"].startswith("x")
    assert n["n_images"] == 5 and all(i["raster"] for i in n["images"])
    assert n["path"].endswith("notes.md")


def test_manifest_refuses_duplicate_basenames(tmp_path):
    for book in ("one", "two"):
        d = tmp_path / book
        d.mkdir()
        shutil.copy(PAGES / "meditations" / "page-01.png", d / "page-01.png")
    with pytest.raises(SystemExit, match="duplicate image basename"):
        manifest_mod.build(tmp_path)


def test_stub_ocr_records_carry_the_contract_and_dimensions(out):
    recs = [json.loads(l) for l in (out / "ocr.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(recs) == 5 and all(r["ok"] for r in recs)
    for r in recs:
        assert set(ocr_mod.FIELDS) <= set(r), r.keys()
        assert r["engine"] == "stub" and r["width"] == 1240 and r["height"] == 1754 and r["chars"] > 500


def test_stub_missing_sidecar_is_not_an_empty_success(tmp_path):
    shutil.copy(PAGES / "meditations" / "page-01.png", tmp_path / "lonely.png")
    rec = ocr_mod.recognize(tmp_path / "lonely.png", "stub")
    assert rec["ok"] is False and "no sidecar" in rec["error"]


def test_verify_density_is_measurable_now_that_records_carry_size(out):
    sys.path.insert(0, str(ROOT / "capture" / "pages"))
    import verify
    rec = json.loads((out / "ocr.jsonl").read_text(encoding="utf-8").splitlines()[0])
    s = verify.score(rec, set(), None)
    assert s["density"] is not None and s["density"] > 100


def test_bookcorpus_membership_is_declared_and_null_is_not_empty(out):
    bc = json.loads((out / "bookcorpus" / "meditations.json").read_text(encoding="utf-8"))
    assert bc["book"] == "Meditations" and len(bc["pages"]) == 5
    p = bc["pages"][0]
    assert p["catalogued"] is False and p["colors"] is None and p["marks"] is None and p["ann"] is None
    assert "declared" in _run("corpus/build_bookcorpus.py", out).stdout


def test_merge_joins_both_channels(out):
    merged = json.loads((out / "merged" / "meditations.json").read_text(encoding="utf-8"))
    assert len(merged["kindle_highlights"]) == 35 and len(merged["photo_pages"]) == 5
    md = (out / "merged" / "meditations.md").read_text(encoding="utf-8")
    assert "never infer a gap" in md.lower() or "absence" in md.lower(), "the two-channel warning must be in every merged file"


def test_node_counts_both_channels(out, tmp_path):
    stats = build_nodes.build(out / "merged", tmp_path)
    assert stats["written"] == 1
    fm = (tmp_path / "books" / "meditations.md").read_text(encoding="utf-8")
    assert "pages_captured: 5" in fm and "kindle_highlights: 35" in fm and "highlight_colors: null" in fm


@pytest.mark.macos
def test_apple_vision_recovers_the_rendered_spans():
    if platform.system() != "Darwin":
        pytest.skip("Apple Vision is macOS only")
    pytest.importorskip("Vision")
    rec = ocr_mod.recognize(PAGES / "meditations" / "page-03.png", "vision")
    assert rec["ok"], rec.get("error")
    got = re.sub(r"\s+", " ", rec["text"]).lower()
    want = [l.strip() for l in (PAGES / "meditations" / "page-03.png.ocr.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    hits = sum(1 for l in want if re.sub(r"\s+", " ", l).lower() in got)
    assert hits / len(want) >= 0.8, f"Vision recovered only {hits}/{len(want)} lines"
    assert rec["mean_conf"] > 0.5 and rec["width"] == 1240
