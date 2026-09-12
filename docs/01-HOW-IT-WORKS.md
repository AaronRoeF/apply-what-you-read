# 01 — How it works

This document explains what this system is and how it is assembled, end to end. It is
written for someone who has cloned the repo and wants to understand the shape before
reading code: what problem the pipeline solves, why the output substrate is markdown
rather than a database, what each stage takes in and hands on, what each stage actually
measured against one real corpus, and the two structural rules — a fixed rebuild order and
a single membership authority — that keep the derived layers from lying to the agents that
read them.

Every figure below is a measurement on that one real corpus — the reference corpus: 88
books, 4,425 highlights, 800 photographed pages — unless a sentence says otherwise. None of
it is a property of the code; it is what the code found on one library. The public-domain
fixture in `fixtures/meditations/` is what the quickstart runs on.

---

## 1. The problem: a decade of annotations that are write-only

A reader who marks passages accumulates a large, high-quality, pre-labelled dataset and
then never reads it again. Two channels hold it, and neither is queryable:

- **Photographed pages.** Pictures of book pages, taken because the page was marked. On the
  reference corpus they lived inside a notes app as image attachments. Nothing can grep a
  JPEG.
- **E-reader highlights.** Span-level marks with colour and location, held in a vendor
  account behind a login, visible only through a web UI — or, when the provider offers one,
  in an export file that is easy to obtain and easy to lose track of.

The corpus this pipeline was built against had **2,352 imported notes** carrying **3,545
attachment files**, of which **3,372 were raster images**. Of those, **2,544 (75%)
contained recognisable text**. The e-reader account held **4,425 annotations across 78
books**, including **44 typed notes** the reader typed.

The marks are the valuable part. A highlight is a judgement the reader already made — no
model had to infer it — and in the classified sample **83 of 142 images (58%)** carried
the reader's own markup. The reason the density is that high is structural rather than
lucky: pages get photographed *because* they were marked, so the annotation is the
selection criterion for the image existing at all.

None of it was addressable. The photographs were pixels; the highlights were behind an
account. The point of this system is to turn both into text on disk that an agent can
search, join, and cite.

---

## 2. The substrate choice: markdown in a vault, not a database

Every stage terminates in markdown files inside a vault — an Obsidian vault if you use
one, a plain folder if you don't. Intermediate artifacts are JSON/JSONL on local disk.
There is no database anywhere in the pipeline.

The reason is that the consumer is an agent, and agents are good at exactly the operations
a filesystem of plain text supports:

| Requirement | Why markdown-on-disk wins |
|---|---|
| Search | `grep` works. No schema, no query language, no server to be running. |
| Citation | A claim can cite `path:line`. A row id cannot be opened by a human. |
| Provenance | Frontmatter travels with the content and survives being copied around. |
| Human review | The same file the agent reads is the file the reader reads and edits. |
| Diffing | Git shows what a regeneration changed. A table mutation shows nothing. |
| Durability | A corrupt row is a corrupt file, not a corrupt store. |

There is one non-obvious consequence worth stating up front, because it dictates the
structure of the last two stages: **markdown files are simultaneously generated and
hand-edited.** The book nodes are rewritten by a script *and* annotated by hand. That is
why `vault/build_nodes.py` carries a `PRESERVE` list and parses hand-authored fields out of
the existing file before overwriting it:

```python
PRESERVE = ("related", "outcome", "applied_in", "status")
```

Those fields are knowledge, not derived data. A regenerator that clobbered them would make
it impossible to build a knowledge graph on top of its own generator's output.

Storage location is also a decision, not an accident. On the reference corpus,
distillations were originally written into a gitignored analysis tree (it held personal
analysis of other kinds). Book distillations are not sensitive, and putting them there cost
version history for no benefit — so the layout is now two tracked directories side by side:
the canonical book nodes in `<vault>/books/` and the distillations they join in
`<vault>/distill/`.

---

## 3. The two channels, and why neither is a superset

```
PHOTOGRAPHED PAGES                        E-READER HIGHLIGHTS
pen marks, marginalia,                    exact span text, colour,
filled-in worksheets, printed             page/location, typed notes,
books never read digitally                every book read on the device
        |                                          |
        | biased sample:                           | complete for its books,
        | only the pages chosen for a photo        | blind to paper and pen
        v                                          v
                 +-------------------------+
                 |  corpus/merge_corpus.py |
                 +-------------------------+
```

This is the single most important design fact in the system, and it was learned by getting
it wrong. Analyses built on photographed pages alone produced confident "the reader never engaged
with chapter N" findings that the highlight data falsifies outright: one book had **0
photographed pages** on a chapter against **22 highlights** on the same chapter. The ratios
generally are stark — that book had **53 photographed pages vs 167 highlights**; another
had **19 vs 107**.

The rule this produced is written into the merge script's docstring and restated verbatim
in every downstream prompt:

> Absence of a photo is not absence of interest. Never infer a gap from missing data; only
> claim one with positive coverage of the surrounding material in **both** sources.

---

## 4. Pipeline diagram

Two on-ramps, one corpus, one node per book. Stages marked *ran once* belong to the
reference corpus and live under `reference/`; the quickstart path does not run them.

```
  PHOTOGRAPHED PAGES                             KINDLE: device / app / Readwise
  pages/<book>/*.jpg (+ notes.md)                          |
          |                                                | [7] HIGHLIGHT JOIN
          | [1] capture/pages/manifest.py                  |   python -m capture.kindle
          |     (reference corpus: reference/triage.py     |     clippings | html | readwise
          |      over a notes-app import — ran once)       |   (or the v0.3 reference crawler)
          v                                                v
   out/manifest.json                             out/kindle-highlights.json
   note<->image map; agents read this,           82 books / 78 with marks
   not the corpus                                4,425 annotations / 0 errors
   (reference: 2,352 notes / 3,545 files)                  |
          |                                                |
  +----------------------------+  +---------------------------------+  |
  | [2] capture/pages/ocr.py   |  | [3] reference/extract_docs.py   |  |
  |     --engine vision | stub |  |     PDF / DOCX / PPTX — ran once |  |
  |     3,372 images           |  |     143 documents               |  |
  +-------------+--------------+  +---------------+-----------------+  |
                |                                 |                    |
                +----------------+----------------+                    |
                                 v                                     |
                   out/ocr.jsonl (+ out/docs.jsonl)                    |
                                 |                                     |
                                 | [4] capture/pages/verify.py  4 signals, uncollapsed
                                 | [5] reference/dedupe.py      355 groups / 821 copies — ran once
                                 | [6] reference/writeback.py   OCR -> note bodies — ran once
                                 v                                     |
                   [ corpus/build_bookcorpus.py ]                      |
                     MEMBERSHIP DECIDED HERE                           |
                     out/bookcorpus/*.json                             |
                                 |                                     |
                                 +----------------+--------------------+
                                                  v
                                     [8] corpus/merge_corpus.py
                                     out/merged/*.json + *.md
                                     88 books / 4,425 highlights
                                     800 photo pages / 44 typed notes
                                                  |
                                 +----------------+-----------------+
                                 v                                  v
                    [9] distill (agents)               [10] vault/build_nodes.py
                    <vault>/distill/distill-<slug>.md  <vault>/books/<slug>.md
                    every book distilled (88)          88 nodes, 1:1, no orphans
                                 |                                  ^
                                 +----------------------------------+
                                   distillation body is joined
                                   into the node at build time
```

---

## 5. Stages

| # | Stage | Script | In | Out | Measured (reference corpus) |
|---|---|---|---|---|---|
| 1 | Capture (pages) | `capture/pages/manifest.py` — on the reference corpus, `reference/triage.py` over a notes-app import, ran once | `pages/<book>/` + optional `notes.md` | `out/manifest.json` | 2,352 notes, 0 broken embeds, 2,346 unique source ids |
| 2 | OCR | `capture/pages/ocr.py --engine vision` (or `stub` off macOS) | raster images | `out/ocr.jsonl` | 3,372 images, 2,544 with text, ~2.99M chars |
| 3 | Document extraction | `reference/extract_docs.py` — ran once; not on the quickstart path | PDF/DOCX/PPTX | `docs.jsonl` | 143 docs, 1,501,157 chars, 0 failures |
| 4 | Verification | `capture/pages/verify.py` | `ocr.jsonl` | `scored.jsonl` + report | 4 signals per image; nothing purge-eligible without a second opinion |
| 5 | Dedupe | `reference/dedupe.py` — ran once; a folder of images has no embeds to rewrite | notes-app attachments | holding dir + report | 355 groups, 821 copies, 0.16 GB, 0 dangling embeds |
| 6 | Write-back | `reference/writeback.py` — ran once; on the public path the vault node is the write target | `ocr.jsonl`, `docs.jsonl`, judgements | note bodies | idempotent callouts; `Drawing*` embeds skipped |
| 7 | Highlight join | file import (`python -m capture.kindle …`, Shipped) or the reference crawler (v0.3, Designed) | `My Clippings.txt` / Export Notes HTML / Readwise CSV — or the account | `out/kindle-highlights.json` | 82 account books, 78 with marks, 4,425 annotations |
| 8 | Merge | `corpus/merge_corpus.py` | `bookcorpus/`, `kindle-highlights.json` | `out/merged/` | 88 books, 4,425 highlights, 44 of 44 typed notes |
| 9 | Distill | `skills/distill/distill.md` + `agents/distill/DISTILL_PROMPT.md` | `out/merged/*.json` | `<vault>/distill/distill-<slug>.md` | every book (88) distilled; corroboration is the signal |
| 10 | Nodes | `vault/build_nodes.py` | `out/merged/` + distillations | `<vault>/books/<slug>.md` | 88 nodes, 1:1 with corpus, zero orphans either direction |

Status labels (Shipped, Proven, landing, Designed) are defined once, in the status table in
the README.

### [1] Capture — the manifest, and why the source's own counts did not mean what they said

On the public path, capture is `capture/pages/manifest.py`: one folder of photographs per
book under `pages/`, an optional `notes.md` sidecar carrying `title:` / `author:` / `asin:`
and anything typed while reading, and out comes `out/manifest.json` — one record per book
folder plus its image map, and the manifest's own `root`, so liveness can be re-checked later
against the folder that produced it. Duplicate image basenames across folders are refused,
loudly, because downstream stages key images by basename. `03-PHOTOS-AND-NOTES.md` walks it.

The reference corpus arrived differently, and the rest of this section is about that path.
Its pages were image attachments inside a notes app, exported through the app's GUI importer
— one-way, read-only, because the notes store is only readable through sanctioned
interfaces. The pipeline never writes to the source; the source is the only true original
and stays intact as the fallback. `reference/triage.py` turned that imported tree into the
manifest. It ran once, it is not on the quickstart path, and `capture/pages/manifest.py` is
its generic successor. The lessons carry.

`reference/triage.py` produced one record per note plus the note↔image map. This exists
because **no agent can read thousands of notes and thousands of images to answer one
question.** It reads the manifest, then targets its reads. The manifest also recovered
provenance the importer dropped: the importer writes exactly one frontmatter field and
leaves the original created/modified dates as filesystem `birthtime`/`mtime`, so the script
reads them off `stat` and puts them where they can be queried.

Two baseline numbers from the source app were wrong, and both would have been read as
import failures:

- The app's note count included **smart folders** — saved searches over notes that live
  elsewhere. 58 notes were counted twice.
- The app's attachment count included forwarded-email junk. **19 notes accounted for 2,852
  "attachments"** — logos, tracking pixels, spacer GIFs. Real attachment files on disk:
  3,545.

Lesson worth generalising: verify the baseline before you verify against the baseline.

### [2] OCR — Apple Vision through PyObjC, local and free

`capture/pages/ocr.py --engine vision` dispatches to `capture/pages/ocr_vision.py`, which
runs `VNRecognizeTextRequest` over each image via PyObjC. No network, no API key, no
per-image cost. It emits one JSON object per image: `path`, `ok`, `engine`, `n_obs`,
`mean_conf`, `min_conf`, `chars`, `text`, and the image's `width` and `height` — the last
two are what make the density signal in stage 4 measurable. Off macOS, `--engine stub`
produces the same record shape from the sidecar text, so the rest of the pipeline can be
exercised anywhere.

Two design notes:

- **Confidence is never discarded**, because a downstream deletion decision without a
  confidence attached is unfalsifiable.
- One bad image must not kill a 3,500-image run, so `recognize()` catches broadly and
  records the error in the record rather than raising.

A Swift implementation exists (`capture/pages/ocr_vision.swift`) and is the more natural
binding, but the toolchain on the build machine could not compile it; PyObjC reaches the
same framework.

`ok=false` fired 198 times, and almost all of them are not failures — Vision rejects
sub-64px images, and in a notes archive those are overwhelmingly email tracking pixels.
`capture/pages/verify.py` reclassifies them as `junk_pixel` for exactly this reason:
labelling ~300 tracking GIFs as OCR failures would poison the calibration corpus with
phantom failures and hide any real engine fault behind them.

### [3] Document extraction — the scanned-PDF trap

`reference/extract_docs.py` ran once, on the reference corpus; documents are outside the
public input scope (books as highlights and page photos) and the quickstart never touches
it. It stays because the trap it found generalises.

It emits the *same JSONL shape* as the OCR stage, so verification and write-back consume
images and documents through one path.

PDFs are the interesting case. Most carry a real text layer, which is exact rather than
recognised. But a scanned PDF has no text layer, and silently emitting an empty string for
it looks identical to a successful extraction of a blank page. So each page is tested, and
the method is recorded **per page**:

```python
if len(text) >= SCANNED_PAGE_THRESHOLD:   # 50 chars
    methods.append("text_layer"); confs.append(1.0)   # exact, not recognized
else:
    page.get_pixmap(dpi=200).save(tmp.name)           # render, then OCR
```

Measured across 143 documents: **109 pure text-layer, 20 mixed, 14 fully scanned with no
text layer at all.** Roughly a quarter of documents needed the render-and-OCR fallback. A
pipeline without that fallback would have reported 14 successful extractions of nothing.

### [4] Verification — score trustworthiness, not correctness

You cannot confirm per-image OCR correctness without ground truth, so
`capture/pages/verify.py` does not try. It answers the tractable question: *is this
extraction trustworthy enough that deleting the source image would be safe?*

Four signals, deliberately **not collapsed into one number** until the end:

| Signal | What it detects |
|---|---|
| `engine_conf` | Vision's own mean confidence. Weak alone, real in combination. |
| `word_validity` | Share of alphabetic tokens in a system dictionary. Garbage OCR is character soup and scores near zero. Best cheap failure detector. |
| `density` | Characters per megapixel. A full-page scan yielding 12 characters is a failure at any confidence. |
| `agreement` | Similarity to an independent second extractor. Strongest available evidence without ground truth. |

Two hard-won rules live here.

**Engine confidence is conditional, not good or bad.** Aggregated over 144 judged images,
`conf >= 0.98` gave 98 matches / 10 partial / 1 mismatch, while `conf < 0.90` gave 14
partial / 7 mismatch / 1 match. It predicts well *because most of the corpus is flat
prose*. Inside grids it inverts — a table can read token-perfect and still lose every
row↔column binding, because OCR serialises column-first. The formulation an independent
reviewer produced is the right one: **engine confidence tracks glyph legibility, not
information retention.** "Contains a grid" is therefore an override, never a score input.

**Annotation is an absolute veto**, checked before any confidence arithmetic:

```python
if rec.get("annotations"):
    f.append("has_annotation")
    out["purge_eligible"] = False
    return out
```

On an annotated page a `matches` verdict measures the wrong thing: the text is captured,
the *selection over* the text is not, and the selection is usually why the page was
photographed.

`word_validity` had a median of 0.78 on this corpus — low, because proper nouns and
abbreviations are not in `/usr/share/dict/words` (point `RG_DICT` at a better word list if
you have one). Thresholds here mean nothing until calibrated against a hand-verified sample.
Uncalibrated scores are just numbers.

### [5] Dedupe — the hard part is link integrity, not detection

`reference/dedupe.py` ran once, on the reference corpus. Its whole job is rewriting embeds
inside note bodies, and a folder of images has none — which is why it is not a public stage.
The lesson is the part to keep.

Byte-identical duplicates are the cheapest reclaim in the pipeline: no model, no judgement,
no information loss. It should run *before* classification, since every duplicate
classified is a wasted pass.

Detection is a SHA-256 group-by. The difficult part is that Obsidian resolves embeds by
**bare filename**, so moving a file silently breaks every note referencing it. The script
therefore rewrites embeds to the keeper **first**, then moves, then verifies zero dangle.
Keeper selection is deterministic — shortest filename, ties alphabetical — which reliably
picks the original over the source app's `" 1"` / `" 2"` copies.

Measured: **355 groups, 821 redundant copies, 0.16 GB, 799 embed rewrites across 156
notes, 0 broken embeds afterwards.** Attachments went 3,545 → 2,724. Nothing is deleted;
duplicates move to a holding directory, so reversing the run is a `mv`.

One honest correction on the headline: 821 files is 23% of the corpus *by count* but only
about 8% *by bytes*. Duplicates skew small.

### [6] Write-back — the step that actually made the reference vault readable

`reference/writeback.py` ran once, on the reference corpus. It writes into imported note
bodies, and the public path has no notes to write into — there, the vault node built in
stage 10 is the write target. Everything before this stage produced data *about* the
corpus; write-back put that data where an agent reading the vault would find it: a
collapsed callout after each embed, containing the recognised text as plain text on disk.

Three invariants, each of which prevents a specific observed failure:

1. **Native handwriting text is authoritative and is never overwritten.** Stylus notes are
   stored as stroke data — pen path, order, direction — and the platform's stroke recogniser
   beats image OCR badly on identical files, because recognising strokes is an easier
   problem than recognising a flat image of ink. The importer already placed that text in
   the note body: **237 of 241 such embeds (98%) already carry it.** So `Drawing*` embeds
   are skipped entirely; adding a Vision callout there buries better text under worse.
2. **Idempotent.** Insertion is gated on a sentinel string, so the script can be re-run as
   classification data improves without duplicating callouts.
3. **Body text is never rewritten.** Only frontmatter is replaced and callouts appended.
   The note's own content is the irreplaceable part.

There is a fourth, subtler rule in the code, and it is the kind of bug that destroys
provenance silently:

```python
st_before = md.stat()
md.write_text(new)
os.utime(md, (st_before.st_atime, st_before.st_mtime))
```

The filesystem *is* the provenance record for original dates. Writing the file clobbers
`mtime`. Without the restore, the script destroys the very timestamps it just wrote into
frontmatter, and every re-run stamps every note with the time of the previous run.

**A note on the abandoned purge.** The original plan was to delete text-dominant images
after OCR. It was scoped, built, calibrated — and then abandoned on evidence. Under the
corrected rubric only **18 of 142 images (13%)** were purge-eligible, worth **66 MB of 731
MB judged (9%)**, against an irreversible operation requiring a human review gate. The
decisive argument was not the ratio: *the value was never the disk space, it was the OCR
text, and the text lands in the notes at write-back whether or not the image survives.*
Classification metadata was kept — the annotation flag, the structural flag, and the
partial/mismatch quarantine set are all retrieval signals — and nothing was deleted.
`reference/CLASSIFY-PATHS.md` documents both classifier implementations. Note that the API
path (`reference/classify.py`) ships as a **reference implementation that was never executed
against this corpus**; the judgements in `out/` came from the agent path.

### [7] Highlight join — three file formats first, then the crawl whose failure mode is silence

On the public path the highlights arrive as files you already have or can get in a minute:
the device's `documents/My Clippings.txt`, the Kindle app's "Export Notes" HTML, or a
Readwise CSV. One command parses any of them, or several at once, into
`out/kindle-highlights.json`:

```bash
python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" --out out/kindle-highlights.json
python -m capture.kindle clippings a.txt html b.html readwise c.csv --out out/kindle-highlights.json
```

Sources merge by book and dedupe by annotation id, and the plausibility line — the sorted
per-book count vector — prints at the end of every run. `02-KINDLE.md` covers each format,
what it loses, and the flags. This is the on-ramp to use whenever an export exists.

The reference corpus took the other road. Its highlights were pulled by driving the vendor's
notebook web UI in the reader's own already-logged-in browser and harvesting span text,
colour, page/location, and typed notes. Result: **82 books in the account, 78 with marks,
4,425 annotations, 0 errors.** Colour distribution: Yellow 3,993 · Pink 177 · Aqua 136 ·
Orange 106. The crawler that did it is the reference implementation,
`capture/kindle/notebook_crawl.py` (v0.3, Designed), for readers whose provider offers no
export. Provider markup drifts; the technique and the checks are what carry.

Two parser bugs are worth documenting because they are the most instructive failure in the
whole system. Both would have shipped roughly a quarter of the data as if it were all of
it, and **both failed by returning zero**, which is indistinguishable from "this book has no
more highlights":

1. The pagination token lives on an element with a **class**, not an id. `getElementById`
   returned null, the loop exited after page one, and every book capped at ~100.
2. Continuation responses are **bare fragments** with no outer wrapper element, so a
   structural child selector matched 98 rows on page one and 0 on every page after it.

Nothing threw. Detection came from a smell: **six unrelated books all landed in a 92–97
band, which is a cap, not natural variation.** One book went from 97 to 376 once fixed.

**The generalisable rule: a scraper whose failure mode is an empty result needs an
independent plausibility check on its own output.**

That check is now `capture/kindle/plausibility.py`, and it does not care which on-ramp
produced the file: the sorted count vector prints for a clippings parse exactly as it would
for a crawl, and it flags a cluster just under a round number (`PAGE_CAP_SUSPECTED`), books
with zero annotations (`ZERO_VS_NULL`), and per-book deltas against a previous run
(`RECRAWL_DIFF`, with `--previous`). It is printed, never fatal. Read it.

### [8] Merge — the corpus of record

`corpus/merge_corpus.py` joins photographed pages to highlight spans on a normalised title
key and writes two files per book: a JSON record for machines and a markdown rendering for
reading, plus `_manifest.json` over the lot. Books present in only one channel are still
books.

Measured on `out/merged/`: **88 books, 4,425 highlights, 800 photographed pages, 44 of 44
typed notes.** Of those 88, 10 are photo-only, 18 have both channels, and the rest are
highlight-only.

An earlier build lost two highlights here, and the defect is worth knowing because nothing
errored: two distinct works — a book and a third-party summary of that book — normalised to
the same slug, so the second write clobbered the first, and the manifest claimed 88 books
over a directory holding 87 files. `disambiguate()` now keeps the subtitle only where a
collision demands it, falling back to the Amazon id when the subtitle does not separate
them, and the manifest rows and the files agree.

Every markdown file this stage emits carries the sampling-bias warning inline, and pages
without extracted mark data are labelled explicitly rather than left blank:

```
### photo page 3 — NOT CATALOGUED — no mark data extracted;
    absence here means unassessed, NOT unmarked
```

### [9] Distill — agents over the merged corpus

Distillation is the one stage where a model is doing judgement rather than extraction. One
agent per book reads the merged record and produces a distillation into
`<vault>/distill/distill-<slug>.md`. `agents/distill/DISTILL_PROMPT.md` holds the contract
and `skills/distill/distill.md` is the interactive form; the method is adapted from a
published book-reading technique and credited in each output. `05-DISTILL.md` is the
tutorial.

The prompt's load-bearing constraints, all of them reactions to observed failure:

- Claims from public research about the book are tagged as such; unverifiable named
  frameworks are marked `[unverified]` with what would confirm them.
- The "what was never marked" section must hedge for sample size, because **absence of a
  photograph is not absence of reading**.
- The payload is the apply section. Generic verbs are declared a failure condition.

Result: on the reference corpus, **every book (88) was distilled.** Corroboration is the
signal (`agents/distill/DISTILL_PROMPT.md`, rule 2); the first 28 distillations to carry
an explicit `corroborated:` verdict in frontmatter returned **4 `true`, 11 `partial`,
13 `false`.** That field exists because of a correction the reader made to the ranking
model: rarity was being read as significance, when rarity is explained by friction. 44 typed
notes in 4,425 highlights is ~1% because typing on an e-reader is annoying, not because those
moments were profound. The replacement signal is **corroboration** — did the mark leave a
receipt *outside* the book: appear in a project, a deck, a decision, a cadence. Observable,
not interpretive.

One caution on the corroboration matcher: a first mechanical attempt used single-word
matching and hit a **782-file noise floor** on words like "cause", "control", "different".
Those numbers are void. A working version needs distinctive multi-word phrases.

### [10] Nodes — one canonical vault file per book

`vault/build_nodes.py` writes `<vault>/books/<slug>.md` from the merged corpus: frontmatter
statistics, provenance links back to the source, and the distillation body joined in from
`<vault>/distill/distill-<slug>.md` with its own frontmatter stripped, if one exists. It
refuses an empty corpus, moves orphans to `books/_orphaned/` rather than deleting them,
writes only on change, refuses basename collisions loudly, and spools to `RG_OUT/spool` when
the vault is unwritable. `04-VAULT.md` states the contract. **88 nodes, 1:1 with the corpus,
zero orphans in either direction.**

The node is where hand-authored knowledge and generated data meet, which is why the
`PRESERVE` mechanism in §2 exists, and why the script has no membership threshold of its
own — see §7.

On the reference corpus a separate generated graph file held the
cross-book analysis and a **do-not-re-derive appendix**. Twenty-eight candidate edges were
generated by four independent lenses and each attacked by three adversarial verifiers.
Twenty-seven refutations stand. One kill was overturned on re-adjudication: two of the three
skeptics had read a stale derived node instead of the raw corpus, and every one of the eight
cited passages turned out to be verbatim in the raw data. The edge is a candidate again, not a
finding — overturning a kill does not make the edge true. **Zero verified cross-book edges**,
across 25 unique book pairs. The named failure modes are worth carrying into any fork:
*manufactured gaps* (book A "lacks the drill" that book A supplies a few pages later),
*colour-rarity inflation* (non-yellow marks cluster by reading session as often as by
meaning), and *genre truisms* (two leadership books agreeing is a property of the shelf).
The refutation machinery worked; the premise that book↔book edges are waiting to be found
did not. What survived were four intra-book edges: a question the reader typed, and the
answer sitting in the same book, already highlighted by the same reader. The Librarian
(v0.3, Designed) inherits that refute-by-default posture.

---

## 6. Rebuild order, and why it is not a style preference

```
corpus/build_bookcorpus.py  ->  corpus/merge_corpus.py  ->  vault/build_nodes.py
```

Run them in that order. `corpus/merge_corpus.py` reads `out/bookcorpus/`;
`vault/build_nodes.py` reads `out/merged/`. A stale merge produces stale nodes.

The reason this is stated as a rule rather than left to inference is that **a stale derived
artifact is not inert — it actively corrupts every agent downstream that trusts it.** That
is not a theoretical concern. It happened, and it happened in the worst possible place: a
*verifier* agent — the component whose entire job is to catch false claims — read a book
node that still carried photo-only statistics after the highlight layer had landed, saw
`highlight_colors: [grey:2]`, concluded the book "has no highlight layer", and killed a
candidate edge on that basis. The book has 107 highlights. That kill is the one overturned on
re-adjudication in stage 10 — and the edge is still only a candidate.

The same defect class showed up four times on this project, and every instance is the same
shape: **absence of data read as a finding, or as nothing at all.**

| # | Instance | Consequence |
|---|---|---|
| 1 | `marks: []` (catalogued, nothing found) collapsed with `null` (never assessed) | An agent reported a nonexistent extractor bug |
| 2 | Photo-only sampling — absence of a photo read as absence of interest | A shipped "never engaged with this chapter" finding, falsified by 22 highlights |
| 3 | Stale nodes carrying photo-only statistics | A verifier killed a candidate edge on a false premise |
| 4 | `corpus/merge_corpus.py` volume floors | Dropped books with real content in both channels; orphaned their nodes |

Instance 4 deserves its numbers, because it shows how a reasonable-looking threshold
destroys signal. A filter of `n >= 25` highlights dropped **44 highlight-only books holding
214 highlights and — the part that actually hurt — 20 of the corpus's 44 typed notes**,
including the densest note-taking anywhere in the library. A second filter,
`kindle < 10 AND photos < 5`, silently dropped books with real content in both channels but
not much in either, leaving their nodes pointing at nothing. Both thresholds were tuned on
**volume** when the target was **corroboration**, and the two are uncorrelated.

The current rule is no volume floor in the merge at all: if it was marked, it is in. The one
threshold that remains sits on the page channel, in `corpus/build_bookcorpus.py`:
`RG_MIN_PAGES`, the number of OCR'd pages below which a book is dropped. It defaults to 1 —
any photographed page counts — and the reference corpus ran with 3.

Three defences against this class are built into the code, and are the parts most worth
copying:

1. **Distinguish empty from unassessed.** `catalogued: bool(c)` is carried alongside the
   data so `[]` and `null` never collapse.
2. **Delete stale outputs before regenerating.** Both `corpus/build_bookcorpus.py` and
   `corpus/merge_corpus.py` unlink their destination directories first, because *stale files
   from an older membership rule are worse than absent ones*.
3. **Write the trap into the artifact.** The merged markdown states the sampling-bias rule
   inline, so an agent reading only the artifact still gets the warning.

---

## 7. Membership is decided in exactly one place

**`corpus/build_bookcorpus.py` decides which notes belong to which book. No other script
may re-derive that decision.**

`vault/build_nodes.py` says so in its own docstring and enforces it by having no threshold:

```python
# MEMBERSHIP IS DECIDED IN ONE PLACE. A book is a node iff it is in the corpus with at
# least one Kindle highlight or one photographed page. No second list.
if not pages and not kindle:
    continue
```

The rule exists because the alternative was tried. The node builder used to re-derive
membership from the manifest with its own copy of the notes-folder test — the rule that is
today's `RG_BOOK_FOLDER`. When that rule proved too tight, **the bug had to be fixed in two
places and was fixed in one.** Two components with independent copies of a membership rule
do not stay in sync; they drift, and the drift presents as orphans — a book in the corpus
with no node, or a node with no corpus behind it. Both have already misled agents on this
project.

The rule itself is also worth reading, because "walk the folders" is the obvious approach
and it is wrong:

```python
BOOK_FOLDER = os.environ.get("RG_BOOK_FOLDER", ...)   # the notes folder that marks a note as a book

def note_book(n):
    named = [strip_author(cat[im["name"]]["book"]) for im in n.get("images", [])
             if im["name"] in cat and cat[im["name"]].get("book")]
    if len(named) >= 3:
        return collections.Counter(named).most_common(1)[0][0], "catalog"
    if n.get("book"):
        return n["book"].strip(), "declared"
    if BOOK_FOLDER in n.get("folder", ""):
        ...
```

Folder membership alone silently dropped the three largest book notes in the reference
vault — **115, 34, and 21 images respectively** — because they sat directly in an archive
folder rather than under the notes folder the rule expected. The opposite heuristic (any
note with ≥5 images is a book) was too loose in the other direction: it promoted work decks
to books. The reading archive is not clean — decks, forms and clippings OCR as perfectly
prose-like text, so a page-shape filter cannot separate them from book pages. The
false-positive rate was never measured; the rule below sidesteps it rather than tuning it.

So the rule is: **trust the catalogue, and require agreement.** An agent that looked at a
page and named a book is evidence; a folder name is a guess. A note is assigned to a book
when at least three of its images independently name that book; failing that, when the note
*declares* its book — a folder-per-book manifest from `capture/pages/manifest.py`, or a
sidecar `title:`, which on the public path is the normal case; and only then by membership
of the notes folder named in `RG_BOOK_FOLDER`, the fallback for imports the catalogue never
reached. Titles are joined on a canonicalised key, because catalogue agents wrote author
suffixes inconsistently — three variants for one author — which fragments the join key if
not stripped.

A related deterministic trick sits in `reference/resolve_titles.py`: e-readers crop the
running header, so a photographed page often carries no title and an agent looking at the
image alone correctly refuses to guess. But the page is embedded in a note, and the note is
named after the book. The title is recoverable from container membership without a model.
**The strongest evidence is the container, not the pixels** — and that script restricts
itself to notes-folder membership precisely because an earlier version that accepted any
note with ≥5 images mis-titled work decks as books. That one rule became the only rule
`capture/pages/manifest.py` has: the folder is the title evidence.

---

## 8. Known gaps

Stated plainly so nobody builds on a false floor:

- **The reference crawler ships in v0.3 (Designed).** Provider selectors drift; the
  plausibility check is the part to keep.
- **The corroboration matcher does not exist yet.** The single-word prototype's numbers are
  void; multi-word phrase matching is the replacement and is unbuilt.
- **`classify.py` never ran against this corpus.** It is a reference implementation of the
  API path; the judgements in `out/` came from the agent path.
- **`detect_highlights.py` is not shipped.** Deterministic colour detection validated at
  roughly 55% against agent labels, which is not good enough to gate anything.
- **Calibration of the purge threshold was invalidated and never redone.** The review
  artifact truncated OCR text at 700 characters under a label asserting completeness, so
  the resulting precision figure may have measured the review tool rather than the
  pipeline. The generalisable lesson: *a review artifact that misrepresents the thing under
  review is worse than no review, because it produces confident numbers that measure the
  tool instead of the system.* The purge was abandoned for independent reasons (stage 6, above), so nothing downstream depends on that number — but do not reuse it.

---

## Where next

`02-KINDLE.md` for the highlight on-ramp, `03-PHOTOS-AND-NOTES.md` for the page channel,
`04-VAULT.md` for the node contract, `05-DISTILL.md` for the distillation. Before you fork
any of it, read `reference/PITFALLS.md`: twelve defects, almost none of which threw.
