#!/usr/bin/env bash
# quickstart.sh — the one path. Runs the whole pipeline on the public-domain fixture, so you
# see what it does before pointing it at your own library. No personal data, no credentials,
# no network beyond what you already cloned (plus pip, once, for two packages).
#
#   bash quickstart.sh                 # fixture -> parse -> pages -> merge -> node (seconds)
#   bash quickstart.sh --with-claude   # ...then distill the fixture book with the claude CLI
#
# Python: needs 3.11+. This script finds the newest 3.11+ interpreter on your machine
# (python3.13 … python3.11, then python3), builds ./.venv with it if there is none, and uses
# that venv for every step. A too-old .venv is rebuilt. If no 3.11+ exists, it tells you how to
# get one and stops — it never runs the pipeline on an unsupported Python.
#
# Env (all optional): RG_OUT (default ./out), VAULT (default ./demo-vault), OCR_ENGINE
# (default stub; `vision` on macOS runs Apple Vision on the fixture's page images).
#
# Every step prints what it wrote. The last block is the node this produced — open it.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"
WITH_CLAUDE=0
for a in "$@"; do case "$a" in --with-claude) WITH_CLAUDE=1 ;; -h|--help) sed -n '2,19p' "$0"; exit 0 ;; *) echo "unknown arg: $a" >&2; exit 2 ;; esac; done

export RG_OUT="${RG_OUT:-$ROOT/out}"
export VAULT="${VAULT:-$ROOT/demo-vault}"
OCR_ENGINE="${OCR_ENGINE:-stub}"
FX="$ROOT/fixtures/meditations"

step() { printf '\n▶ %s\n' "$*"; }
py_ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; }
py_ver() { "$1" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null; }

step "python"
PY=""
if [ -x "$ROOT/.venv/bin/python" ]; then
  if py_ok "$ROOT/.venv/bin/python"; then PY="$ROOT/.venv/bin/python"; echo "  using .venv (python $(py_ver "$PY"))"
  else echo "  .venv is python $(py_ver "$ROOT/.venv/bin/python") — too old; rebuilding it"; rm -rf "$ROOT/.venv"; fi
fi
if [ -z "$PY" ]; then
  BASE=""
  for cand in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$cand" >/dev/null 2>&1 && py_ok "$(command -v "$cand")"; then BASE="$(command -v "$cand")"; break; fi
  done
  if [ -z "$BASE" ]; then
    cat >&2 <<EOF
  apply-what-you-read needs Python 3.11 or newer, and none was found on PATH
  (python3 here is $(py_ver python3 || echo 'missing')).
  Get one, then re-run this script — it builds the venv itself:
    macOS:   brew install python@3.13      (or the installer at python.org)
    Ubuntu:  sudo apt install python3.12 python3.12-venv
    Windows: python.org installer, then run this under WSL or Git Bash
EOF
    exit 1
  fi
  echo "  building .venv with $BASE (python $(py_ver "$BASE"))"
  "$BASE" -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/python" -m pip install -q --upgrade pip
  "$ROOT/.venv/bin/python" -m pip install -q pillow pytest
  PY="$ROOT/.venv/bin/python"
fi

step "1/6  Kindle highlights: My Clippings.txt -> $RG_OUT/kindle-highlights.json"
"$PY" -m capture.kindle clippings "$FX/clippings/My Clippings.txt" --out "$RG_OUT/kindle-highlights.json"

step "2/6  photographed pages: manifest + OCR ($OCR_ENGINE) -> $RG_OUT/manifest.json, ocr.jsonl"
"$PY" capture/pages/manifest.py --pages "$FX/pages" --out "$RG_OUT/manifest.json"
"$PY" capture/pages/ocr.py --dir "$FX/pages" --out "$RG_OUT/ocr.jsonl" --engine "$OCR_ENGINE"

step "3/6  book corpus (pages joined per book) -> $RG_OUT/bookcorpus/"
"$PY" corpus/build_bookcorpus.py

step "4/6  merge both channels -> $RG_OUT/merged/"
"$PY" corpus/merge_corpus.py

step "5/6  one node per book -> $VAULT/books/"
"$PY" vault/build_nodes.py --vault "$VAULT" --corpus "$RG_OUT/merged"

if [ "$WITH_CLAUDE" -eq 1 ]; then
  step "6/6  distill the fixture book with claude -> $VAULT/distill/distill-meditations.md"
  bash agents/distill/distill-one.sh meditations --context "$FX/reader-context.md"
  "$PY" vault/build_nodes.py --vault "$VAULT" --corpus "$RG_OUT/merged"
else
  step "6/6  distill (skipped — re-run with --with-claude, or open Claude Code here and say: distill Meditations)"
fi

NODE="$VAULT/books/meditations.md"
[ -f "$NODE" ] || { echo "quickstart: FAILED — expected $NODE to exist" >&2; exit 1; }
printf '\n✓ done. Your first node:\n  %s\n\n' "$NODE"
head -20 "$NODE" | sed 's/^/  │ /'
cat <<EOF

Next (first: source .venv/bin/activate — then \`python\` is this venv's):
  your own Kindle   python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" --out out/kindle-highlights.json
                    (or: html <Export Notes>.html · readwise <export>.csv)   then steps 4-5 again
  your own pages    put photos in a folder per book, then steps 2-5 with --pages <that folder> (OCR_ENGINE=vision on macOS)
  the tests         bash tests/run.sh
  the loop          docs/README.md — v0.2 adds Praxis and the Tutor (not in this release)
EOF
