"""capture/pages/ocr_stub.py — the "I already have the text" engine.

For each image `X.png` it reads `X.png.ocr.txt` beside it and reports that as the recognised
text with confidence 1.0. Used by the fixture, by CI on Linux (no Apple Vision there), and by
anyone whose pages were transcribed some other way. A missing sidecar is `ok: false` with an
error, not an empty success — an empty result and a correct result must never look the same.
"""
from __future__ import annotations

import pathlib


def recognize(path: pathlib.Path) -> dict:
    side = pathlib.Path(str(path) + ".ocr.txt")
    if not side.exists():
        return {"path": str(path), "ok": False, "error": f"no sidecar {side.name}"}
    text = side.read_text(encoding="utf-8", errors="replace").rstrip("\n")
    lines = [l for l in text.split("\n") if l.strip()]
    return {"path": str(path), "ok": True, "n_obs": len(lines), "mean_conf": 1.0, "min_conf": 1.0,
            "chars": len(text), "text": text}
