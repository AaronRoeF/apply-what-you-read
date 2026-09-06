#!/usr/bin/env bash
# tests/run.sh — the one test entry point. Runs pytest with the repo's own venv when one exists
# (`.venv/`), else whatever `python3` is on PATH. Extra arguments pass through to pytest.
#
#   bash tests/run.sh                 # everything that runs on this platform
#   bash tests/run.sh -m "not macos"  # Linux CI selection
#   bash tests/run.sh -m macos        # the Apple Vision OCR path only
#
# Exit code is pytest's. A missing pytest is a hard failure, not a skip — a suite that cannot
# run must not look green (docs/reference/PITFALLS.md: almost none of the failures threw).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; else PY="$(command -v python3)"; fi
"$PY" -c "import pytest" 2>/dev/null || { echo "tests/run.sh: pytest not importable by $PY — pip install pytest pillow" >&2; exit 2; }
exec "$PY" -m pytest -q --rootdir "$ROOT" "$ROOT/tests" "$@"
