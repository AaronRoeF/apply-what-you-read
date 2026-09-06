# reference/ — ran once, on one corpus

These scripts are kept because the documentation cites them and because the decisions they
forced are the most transferable part of this repository. They are **not** on the quickstart
path and most of them assume an input that a fresh reader does not have: a notes-app export
with embedded images, wikilinks, and per-note frontmatter.

Run them from the repository root; their relative paths (`out/...`) assume it.

| script | what it did | why it is here and not in `capture/` |
|---|---|---|
| `triage.py` | Built the first corpus manifest from a notes-app export (one record per imported note plus the note↔image map). | Bound to that export's layout. `capture/pages/manifest.py` is the generic successor: a folder of images plus an optional sidecar. |
| `dedupe.py` | Collapsed byte-identical duplicate attachments and repointed the notes' embeds at the keeper. | Its whole job is rewriting embeds inside note bodies; a folder of images has none. See `docs/reference/DECISIONS.md` for the link-integrity lesson. |
| `writeback.py` | Wrote recognised text and provenance back into the imported notes. | Writes into note bodies — the public path has no notes to write into. The vault node is the public write target. |
| `resolve_titles.py` | Resolved book titles for header-less pages from their parent note. | Its one rule (the container is the title evidence) became `manifest.py`'s only rule. |
| `review_sample.py` | Generated the human calibration sample that gated a purge. | The purge was abandoned on measurement (`docs/reference/DECISIONS.md` §2); the calibration story is what remains. |
| `watch.py` | Live dashboard for the OCR pass. | Cosmetic; reads, never writes. |
| `extract_docs.py` | Extracted text from PDF / DOCX / PPTX attachments. | Documents are outside the public input scope (books as highlights and page photos). |
| `classify.py` | Reference implementation of the API classification path. | **Never executed against the corpus** — the judgements in `out/` came from the agent path. See `docs/reference/CLASSIFY-PATHS.md`. |
| `detect_highlights.py` | Deterministic highlight-colour detection. | **Not shipped as a stage** — validated at roughly 55% agreement with agent labels, which is not good enough to gate anything. Kept as the measurement, not the tool. |

If you fork this repo to import a notes-app export of your own, start with `triage.py` and read
`docs/reference/PITFALLS.md` first — almost none of its twelve defects threw an exception.
