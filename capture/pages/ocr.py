#!/usr/bin/env python3
"""capture/pages/ocr.py — the OCR seam. One record contract, pluggable engines.

    python capture/pages/ocr.py --dir pages/ --out out/ocr.jsonl [--engine vision|stub]

Record, one JSON object per line (the contract every engine must emit and every downstream
stage reads):

    {"path", "ok", "engine", "n_obs", "mean_conf", "min_conf", "chars", "text",
     "width", "height"}            + "error" when ok is false

Engines:
  vision   Apple Vision via PyObjC (macOS only; local, free, no network, no API key).
           The engine this pipeline was built and measured with. `capture/pages/ocr_vision.py`.
  stub     Reads `<image>.ocr.txt` next to each image and reports it as the recognised text
           with confidence 1.0. For CI on Linux, for fixtures, and for "I already have the
           text" cases. `capture/pages/ocr_stub.py`.
  tesseract  Not implemented here on purpose. To add an engine, implement
           `recognize(path) -> dict` returning the record above and register it in ENGINES;
           `pytesseract.image_to_data` gives per-word confidences to average.

`width`/`height` come from Pillow when it is installed (they feed verify.py's density
signal — characters per megapixel — which was silently None before this seam existed).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

RASTER = {".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".gif", ".tiff", ".tif", ".bmp"}
FIELDS = ("path", "ok", "engine", "n_obs", "mean_conf", "min_conf", "chars", "text", "width", "height")


def image_size(path: pathlib.Path) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:  # noqa: BLE001 — size is a bonus signal, never a reason to fail OCR
        return 0, 0


def _vision(path: pathlib.Path) -> dict:
    try:
        from . import ocr_vision          # imported as a package (tests, python -m)
    except ImportError:
        import ocr_vision                 # run as a script: capture/pages/ is sys.path[0]
    return ocr_vision.recognize(path)


def _stub(path: pathlib.Path) -> dict:
    try:
        from . import ocr_stub
    except ImportError:
        import ocr_stub
    return ocr_stub.recognize(path)


def _tesseract(path: pathlib.Path) -> dict:
    raise NotImplementedError("tesseract engine not shipped — implement recognize(path) -> record "
                              "(see the module docstring) and register it in ENGINES")


ENGINES = {"vision": _vision, "stub": _stub, "tesseract": _tesseract}


def recognize(path: pathlib.Path, engine: str = "vision") -> dict:
    rec = {"path": str(path), "ok": False, "engine": engine, "n_obs": 0, "mean_conf": 0.0,
           "min_conf": 0.0, "chars": 0, "text": "", "width": 0, "height": 0}
    try:
        r = ENGINES[engine](path)
    except NotImplementedError:
        raise
    except Exception as exc:  # noqa: BLE001 — one bad image must not kill the run
        rec["error"] = f"{type(exc).__name__}: {exc}"
        return rec
    rec.update({k: v for k, v in r.items() if k in FIELDS or k == "error"})
    rec["engine"] = engine
    if not rec.get("width"):
        rec["width"], rec["height"] = image_size(path)
    return rec


def iter_images(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in pathlib.Path(root).rglob("*") if p.is_file() and p.suffix.lower() in RASTER)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", required=True, help="recursively OCR every raster image under this directory")
    ap.add_argument("--out", required=True, help="JSONL destination (usually $RG_OUT/ocr.jsonl)")
    ap.add_argument("--engine", choices=sorted(ENGINES), default="vision")
    ap.add_argument("--progress-every", type=int, default=100)
    args = ap.parse_args(argv)
    paths = iter_images(pathlib.Path(args.dir))
    if not paths:
        print("ocr: no raster images found", file=sys.stderr)
        return 1
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ok = 0
    with out.open("w", encoding="utf-8") as sink:
        for i, p in enumerate(paths, 1):
            rec = recognize(p, args.engine)
            ok += bool(rec["ok"])
            sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if args.progress_every and i % args.progress_every == 0:
                print(f"  ocr {i}/{len(paths)}", file=sys.stderr)
    print(f"ocr[{args.engine}]: {len(paths)} images, {ok} ok -> {out}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
