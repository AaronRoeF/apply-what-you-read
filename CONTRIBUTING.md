# Contributing to apply-what-you-read

Thanks for your interest. This is a small, opinionated project: one pipeline, one path, no
service. Contributions are judged against that.

## Quick links

- **Bug?** Open an issue with the `bug` template. If a capture stage is involved, paste the
  plausibility line (the sorted per-book count vector) — a silent zero is a bug even when
  nothing threw.
- **Feature idea?** Open an issue with the `feature` template first. Not every feature lands;
  the project deliberately stays small.
- **Adding a capture format or a Tutor channel?** Each has a contract to hit. Read
  `docs/02-KINDLE.md` (capture) or `docs/reference/AGENTS.md` (Tutor) before writing code.

## PR flow

1. Fork the repo and create a topic branch (`feat/short-name` or `fix/short-name`).
2. Tests must pass: `bash tests/run.sh` (it uses `.venv` if the quickstart built one, else `python3`;
   `pip install pytest pillow` is all it needs). On macOS the Apple Vision test runs once `pip install -r requirements-mac.txt` has been done; otherwise it skips.
3. `bash tests/publish-checks.sh --root .` must report zero errors. It runs in CI too.
4. Every number you add to the docs cites the artifact it was measured from.
5. Open a PR that says what problem it solves, what changes (file by file), and why it fits.

## What we won't merge

- Any book text, highlight text, or personal annotation. The repo ships code, not corpus.
- Telemetry, accounts, or a hosted service of any kind.
- Credential handling for the crawler. It drives the reader's own logged-in browser, or nothing.
- Cloud dependencies on the quickstart path.

## Code of conduct

See `CODE_OF_CONDUCT.md`. Be direct, be kind, prefer evidence over rhetoric.
