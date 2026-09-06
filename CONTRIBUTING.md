# Contributing to reading-graph

Thanks for your interest. This is a small, opinionated project: one pipeline, one path, no
service. Contributions are judged against that.

## Quick links

- **Bug?** Open an issue with the `bug` template. If a capture stage is involved, paste the
  plausibility line (the sorted per-book count vector) — a silent zero is a bug even when
  nothing threw.
- **Feature idea?** Open an issue with the `feature` template first. Not every feature lands;
  the project deliberately stays small.
- **Adding a capture format or a Tutor channel?** Each has a contract to hit. Read
  `docs/02-HIGHLIGHT-EXTRACTION.md` (capture) or `docs/05-AGENTS.md` (Tutor) before writing code.

## PR flow

1. Fork the repo and create a topic branch (`feat/short-name` or `fix/short-name`).
2. Tests must pass: `pytest` on Linux; `pytest -m macos` as well if you touched the
   photographed-pages path.
3. `bash tests/publish-checks.sh` must report zero errors. It runs in CI too.
4. Every number you add to the docs cites the artifact it was measured from.
5. Open a PR that says what problem it solves, what changes (file by file), and why it fits.

## What we won't merge

- Any book text, highlight text, or personal annotation. The repo ships code, not corpus.
- Telemetry, accounts, or a hosted service of any kind.
- Credential handling for the crawler. It drives the reader's own logged-in browser, or nothing.
- Cloud dependencies on the quickstart path.

## Code of conduct

See `CODE_OF_CONDUCT.md`. Be direct, be kind, prefer evidence over rhetoric.
