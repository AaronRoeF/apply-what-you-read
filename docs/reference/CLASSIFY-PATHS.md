# The classifier — two paths

The classifier — the step between OCR and verification — is the only step in this
pipeline that needs a vision model. Everything else is deterministic: OCR
(`capture/pages/ocr.py --engine vision`), document extraction
(`reference/extract_docs.py`), scoring (`capture/pages/verify.py`), write-back
(`reference/writeback.py`).

Neither path is on the quickstart path. Path B, the agent path, is what produced the
judgements for the reference corpus; Path A, `reference/classify.py`, is a reference
implementation that has **never been executed** against that corpus. Document
extraction and write-back likewise ran once on the reference corpus and are kept under
`reference/`.

There are two ways to run it. They call the same underlying models, and both
feed `capture/pages/verify.py` and the write-back stage — but **they no longer emit the same
record.** Path A returns a second verbatim transcription; Path B was redesigned
to return a *verdict* on the OCR instead, because bulk transcription of personal
documents trips output filtering (see below, and `PITFALLS.md` §2.1). Pick on
operational grounds, and know which record you are getting.

```
                       ┌─────────────────────────────────────┐
   ocr.jsonl ─────────▶│  CLASSIFY                           │
   docs.jsonl          │  bucket + second opinion (see below) │
                       └──────────────┬──────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            PATH A: API                         PATH B: agent
   `reference/classify.py` + API key         a coding agent + batches
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
                            out/classify*.jsonl
                                      │
                                      ▼
                        verify.py  →  write-back  →  purge
                                     (purge abandoned on measurement;
                                      see VERIFICATION.md §3)
```

## Choosing

| | **Path A — API** | **Path B — agent** |
|---|---|---|
| Needs | Anthropic API key + billing | A coding agent that can read images |
| Cost | ~$0.008/image (Sonnet) | subscription compute |
| Runs | unattended, hours | supervised, across sessions |
| Idempotent | yes — resumes per image | per batch; a dead batch is redone |
| Reproducible by a stranger | **yes** | only with the same agent harness |
| Emits | bucket + second verbatim transcription | bucket + verdict on the OCR + `annotations` flag |
| Feeds `agreement` | yes | no — the verdict replaces it, and is the stronger signal |

**Choose Path A** if you want to walk away, if you are processing thousands of
images, or if anyone else needs to reproduce your run.

**Choose Path B** if you do not want to set up billing, if you already work
inside a coding agent, or if you are processing a few hundred images and can
supervise the run.

### Known failure mode on Path B

A batch can die mid-run with `Output blocked by content filtering policy`. A
personal archive contains personal documents, and a long verbatim transcription
of one can trip a safety classifier — killing the **whole batch**, not just the
offending image. Measured here: five consecutive transcribe-style batches, five
deaths, 14 usable records out of 150.

Mitigations, in order of effectiveness:

1. **Do not ask for a transcription at all.** Run the deterministic OCR first,
   ship its text *alongside* the image, and ask the agent to judge the two
   against each other. Output falls from ~300 tokens per image to ~30, the agent
   never reproduces document contents, and mortality went from 5/5 batches to
   0/6. This is the fix; the rest are damage control.
2. **Write output incrementally**, one line per image, so a death costs only
   the in-flight image.
3. **Keep batches small** (10–15 images). Note what this does and does not buy:
   it bounds the blast radius of a death, it does not reduce the chance of one.
4. **Re-run the dead batch split in half.** Repeat until the offending image is
   isolated, then classify it by hand or leave it `structural` (keep the image).

Path A can hit refusals too, but per request — one image fails, the run
continues.

## The output contracts

Both paths write JSONL, one object per image, keyed on `path` and carrying
`bucket`. They diverge on how the second opinion is expressed.

**Path A — transcription:**

```json
{"path": "…/_attachments/scan.jpg",
 "bucket": "text_dominant" | "structural" | "non_text",
 "text": "verbatim transcription",
 "description": "one sentence — structural images only",
 "model_conf": 0.0-1.0}
```

`text` is the **second OCR opinion**. `verify.py` compares it against Apple
Vision's output to produce the `agreement` score that gates the purge. It must be
verbatim: a transcription that "cleans up" the source silently destroys the
agreement signal and makes a correct extraction look like a disagreement.

**Path B — verdict:**

```json
{"path": "…/_attachments/scan.jpg",
 "bucket": "text_dominant" | "structural" | "non_text",
 "ocr_verdict": "matches" | "partial" | "mismatch",
 "ocr_conf": 0.0-1.0,
 "annotations": true | false | null,
 "description": "one sentence — structural images only"}
```

The verdict is a *direct* judgement on whether the deterministic OCR matches the
page, which is a stronger agreement signal than string distance between two
transcriptions — string distance conflates "the engine failed" with "the two
transcribers formatted differently". `annotations` is three-state on purpose:
`null` means the image was never assessed for the reader's markup, and must not render
as "none found".

## Path A — API

Reference implementation, never executed against the reference corpus; read the code
before trusting the invocation.

```bash
printf 'ANTHROPIC_API_KEY=%s\n' 'sk-ant-…' > .env && chmod 600 .env
./.venv/bin/python reference/classify.py --ocr out/ocr.jsonl --out out/classify.jsonl
```

Resumable: re-running skips paths already present in the output file. Images
where Vision found no text are skipped entirely (auto-keep, no model call), as
are files under 2 KB (email tracking pixels).

## Path B — agent

```bash
./.venv/bin/python capture/pages/make_batches.py --ocr out/ocr.jsonl --min-bytes 1000000 --size 12
```

Then dispatch one agent per batch, asking for the Path B verdict record above —
the bucket rubric is the `PROMPT` constant in `reference/classify.py`, which both
paths share — and concatenate the per-batch files:

```bash
cat out/classify_batch_*.jsonl > out/classify.jsonl
```

## Order the work by bytes, not by count

Purging reclaims disk, and disk is distributed very unevenly across a notes
archive. Measured on the one real corpus this pipeline was built against (3,372
images from a notes-app export):

| Threshold | Images | Share of payload |
|---|---|---|
| every image with text | 2,544 | 98% |
| ≥ 500 KB | 1,222 | 83% |
| ≥ 1 MB | 430 | **57%** |

**430 images held 57% of 2.07 GB.** Classifying the largest images first gets
most of the benefit for a fraction of the work, whichever path you choose.
`--min-bytes` exists for exactly this.
