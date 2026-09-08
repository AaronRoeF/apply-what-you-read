# 03 — Photographed pages and typed notes

The second channel. It exists because an e-reader cannot capture a pen stroke, a bracket in a
margin, a worksheet you filled in, or any book you read on paper — and because, measured on
one real corpus, a pass built on highlights alone and a pass built on photographs alone reached
confidently different conclusions about the same book. Neither channel is a superset of the
other. `01-HOW-IT-WORKS.md` §3 has the numbers.

## Input

One folder per book, any raster images, an optional sidecar:

```
pages/
  meditations/
    page-01.jpg
    page-02.jpg
    notes.md          # optional
```

`notes.md` carries frontmatter (`title:`, `author:`, `asin:` — all optional) and, in its body,
anything you typed while reading. Without a sidecar the folder name becomes the title
(`meditations` → *Meditations*).

Two rules the manifest enforces:

- **The folder is the title evidence.** A page with no visible header has no other claim to a
  book; the pipeline never guesses a title from an image.
- **Image basenames are unique across the whole `pages/` tree.** Downstream stages key images
  by basename; two folders both holding `page-01.jpg` would silently merge two books. The
  manifest refuses, loudly, and tells you which two.

## Run

```bash
python capture/pages/manifest.py --pages pages/ --out out/manifest.json
python capture/pages/ocr.py --dir pages/ --out out/ocr.jsonl --engine vision   # macOS
python capture/pages/ocr.py --dir pages/ --out out/ocr.jsonl --engine stub     # elsewhere
python corpus/build_bookcorpus.py
python corpus/merge_corpus.py
python vault/build_nodes.py --vault /path/to/vault
```

### OCR engines

`vision` is Apple's Vision framework through PyObjC: local, free, no network, no key, and the
engine this pipeline was built and measured with (`pip install -r requirements-mac.txt`).

`stub` reads `<image>.ocr.txt` beside each image. It is how the fixture and Linux CI run, and
how you plug in text you already have. A missing sidecar is `ok: false` with an error — never
an empty success.

`tesseract` is deliberately not implemented. The seam is one function: implement
`recognize(path) -> record` returning the contract below and register it in
`capture/pages/ocr.py`. `pytesseract.image_to_data` gives per-word confidences to average.

### The OCR record

```json
{"path": "...", "ok": true, "engine": "vision", "n_obs": 41, "mean_conf": 0.93,
 "min_conf": 0.61, "chars": 1830, "text": "...", "width": 3024, "height": 4032}
```

`mean_conf` and `min_conf` are never discarded: a purge decision without a confidence attached
is unfalsifiable. `width`/`height` feed `verify.py`'s density signal (characters per megapixel);
a full-page scan that yields twelve characters is a failure even at high engine confidence.

## What the corpus stage does with it

`corpus/build_bookcorpus.py` owns **membership** — the one place that decides what counts as a
book — and it decides in this order: an agent catalogue that named the book on three or more
pages; a declared title (this manifest, or a sidecar); a notes folder name (`RG_BOOK_FOLDER`,
for imports from a notes app). It also re-checks that each source folder still exists: a
manifest is a snapshot, and a snapshot is evidence of the past, not a claim about the present.

Each page record carries `catalogued`, `gist`, `ann`, `colors`, `marks`. **`null` is not
`[]`.** `colors: null` means no one has catalogued the page's marks yet; `colors: []` means
someone looked and found none. Collapsing the two made an unexamined page look like a clean
one, once, and an agent reported a bug that did not exist.

`RG_MIN_PAGES` (default 1) drops books with fewer OCR'd pages. The reference corpus used 3;
volume floors turned out to discard the highest-value signal, so the default is now "if you
marked it, it is in".

## Cataloguing marks (optional, agent path)

OCR reads the text; it cannot see what *you* did to the text. The catalogue pass is an agent
reading each page image and recording what is there — highlight bands and their colour, pen
marks, brackets, arrows, filled-in fields — without transcribing. The prompt is
`capture/pages/catalog_prompt.md`; batching helpers are `make_batches.py` and
`make_proxies.sh` (downscale oversized photos past the image-read ceiling). Two traps it
names: a "3,940 highlighters" band on a Kindle screenshot is other readers' highlighting, not
yours; a dotted underline beneath a highlight in some apps means a typed note is attached.

`reference/CLASSIFY-PATHS.md` compares this agent path with an API path that was written but
never run against the reference corpus.

## Photographs are a biased sample

You photograph some of what you mark, not all of it. Any conclusion of the form "the reader
never engaged with chapter N" built on photographs alone is the failure this project's own
history warns about most loudly — one such finding was refuted by twenty-two highlights on
that chapter in the other channel. `merge_corpus.py` writes the warning into every merged file,
and every consumer of the corpus is expected to honour it: never infer a gap from missing data.

## From an Apple Notes folder

If your book notes live in Apple Notes — a folder holding one note per book, with photographed
pages, typed remarks, and Apple Pencil handwriting — the pipeline reads that folder directly on
macOS:

```bash
python capture/notes/apple_notes.py --folder Praxis --library <your vault>/books --dry-run
python capture/notes/watch.py --folder Praxis --library <your vault>/books --run
```

Start with `--dry-run`: it names every note and what it would become, and writes nothing.

**What Apple already recognised.** The Notes database on a Mac
(`~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`) stores, per attachment,
the text Apple's own on-device OCR read from each photo and the text the stroke recogniser
read from each Pencil page. That is the text Spotlight searches. The exporter takes it as it
is: it opens a copy of the database read-only, reads one folder and nothing else, and writes
the folder-per-book layout this document describes — one page image per attachment, a text
sidecar per page, a `notes.md` for the typed body — so every later stage is unchanged.

**Three text sources, one rule of authority.** Every sidecar line says where its text came
from: `via: typed`, `via: apple-ocr`, `via: apple-handwriting`, `via: vision`. For a Pencil
page the recogniser's text is authoritative and is never overwritten: the recogniser works
from strokes, and on the same page it recovers a numbered list and clean technical terms that
image OCR mangles. Local Vision runs only where Apple's text is empty, or when you ask for a
second reading; both readings are kept, and the plausibility report prints their overlap per
page so a disagreement is visible instead of silently resolved.

**Four kinds, decided by evidence.** A note holding pages is a **book**. A typed note with no
pages whose title names a book already in your library is a **book-note**, which becomes its own
node linked to that book rather than inventing a book with no pages — that is what `--library`
is for, and on the first real run it was the difference between nineteen notes filed as loose
wisdom and nineteen notes filed under their books. A short note ending in an attribution line
("— Author, Work") is a **quote**. Anything else short and text-only is **wisdom**. A note that
fits none is exported as wisdom marked `unsorted` and named in the report; nothing is dropped.
A trailing number is a continuation ("Meditations", "Meditations 2" → one book), and your own
mapping file beats every rule above.

**Kept flowing.** `watch.py` compares each note's content hash against a small state file and
re-exports only what moved, then optionally re-runs the stages. Apple rewrites modification dates
in bulk on sync, so the hash decides and the date is only a cheap pre-filter. Unchanged files are
not rewritten, so a nightly run is free and mtimes stay meaningful. A note you delete in Apple
Notes deletes nothing here: the disappearance is recorded in the state file and the exported
files stay. The database is copied before it is opened, and opened read-only — your notes are
never written to.

**Tested without your notes.** The database layer sits behind one function, and a generator
builds a three-note synthetic database in the same shape, with fixture images, a fake Pencil
render, and recogniser text, so folder scoping, handwriting authority, the OCR fallback,
continuation titles, the refusal, idempotent re-export, and the watcher all run in CI on Linux.
On a Mac, `--dry-run` lists what the real folder would export, and nothing else.
