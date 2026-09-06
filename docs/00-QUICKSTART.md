# 00 — Quickstart: the fixture, end to end, in under a minute

Nothing here touches your data. The repository ships a public-domain book (*Meditations*,
Marcus Aurelius, Project Gutenberg #2680 — see `fixtures/meditations/SOURCE.md`) with synthetic
highlights in every format the pipeline reads, five "photographed" pages, and a small reader
journal. You run the whole pipeline on it, read the node it produces, and only then point the
same commands at your own library.

## 0. Prerequisites

- **Python 3.11 or newer, somewhere on your machine.** The quickstart finds the newest 3.11+
  interpreter on your PATH (`python3.14`, `python3.13`, `python3.12`, `python3.11`, then `python3`), builds
  `.venv/` with it, and installs the two packages it needs (Pillow for the fixture's page
  images, pytest for the tests). You do not create the venv yourself. **macOS ships Python
  3.9 as `python3`**, which is too old; get a newer one first (`brew install python@3.13`, or
  the installer at python.org) and the quickstart will pick it up. If nothing 3.11+ is found
  it says so and stops — it never runs on an unsupported Python.
- macOS only if you want real OCR of photographed pages (Apple Vision). Elsewhere the quickstart
  uses a stub engine that reads pre-transcribed text; the rest of the pipeline is identical.
- [Claude Code](https://claude.com/claude-code) for the distill step and everything after it.
  The quickstart runs without it.

```bash
git clone https://github.com/AaronRoeF/apply-what-you-read && cd apply-what-you-read
bash quickstart.sh
```

## 1. What you will see

One block per stage. This is the real output of a run on a clean machine; paths print in full
(shortened here to the repository-relative form).

```
▶ python
  building .venv with /usr/local/bin/python3.13 (python 3.13.x)     ← first run only

▶ 1/6  Kindle highlights: My Clippings.txt -> out/kindle-highlights.json
parsed clippings fixtures/meditations/clippings/My Clippings.txt: 35 annotations in 1 book(s)
wrote out/kindle-highlights.json: 1 book(s), 35 annotations
plausibility: books=1 annotations=35 sorted counts = [35]
  no plausibility flags

▶ 2/6  photographed pages: manifest + OCR (stub) -> out/manifest.json, ocr.jsonl
  notes              1
  notes_with_images  1
  raster_images      5
  sidecars           1
ocr[stub]: 5 images, 5 ok -> out/ocr.jsonl

▶ 3/6  book corpus (pages joined per book) -> out/bookcorpus/
  BOOK                                           pgs   cat      chars  via
  Meditations                                      5     0      6,196  declared
  TOTAL                                            5     0

▶ 4/6  merge both channels -> …/apply-what-you-read/out/merged/
BOOK                                         kindle photo note ≠yel
Meditations                                      35     5    5    0

1 book(s) -> …/apply-what-you-read/out/merged/

▶ 5/6  one node per book -> demo-vault/books/
build_nodes: 1 written, 0 unchanged, 0 orphaned, 0 collisions, 0 spooled -> demo-vault/books

▶ 6/6  distill (skipped — re-run with --with-claude, or open Claude Code here and say: distill Meditations)

✓ done. Your first node:
  demo-vault/books/meditations.md
  │ ---
  │ name: "Meditations"
  │ type: book
  │ …                                              ← the first 20 lines of the node

Next (first: source .venv/bin/activate — then `python` is this venv's):
  …
```

Four lines are worth pausing on.

**`sorted counts = [35]`** is the plausibility vector. With one book it looks trivial. With
eighty it is the only thing that ever caught the extractor returning a quarter of the data
while reporting success (`02-KINDLE.md`). Read it every run.

**`via declared`** in stage 3 says how the book was recognised: this manifest declared its title.
The other two ways are an agent catalogue that named it on three or more pages, and a
notes-folder rule for imports from a notes app (`03-PHOTOS-AND-NOTES.md`).

**`0 orphaned, 0 collisions, 0 spooled`** are the three ways the node builder refuses to lose
or corrupt work: a book that leaves the corpus is moved aside, never deleted; a second file
with the same basename anywhere in the vault is refused, because wiki links resolve by
basename; a vault that cannot be written spools the node instead of dropping it.

**The clippings file carries no colour** (`kindle_colors: []` in the node). The app's Export
Notes HTML and a Readwise CSV do. If colour matters to you, use one of those — `02-KINDLE.md`.

Run it again: `1 written` becomes `1 unchanged`. Unchanged nodes keep their modification time,
so "recently modified" in your vault stays meaningful.

## 2. Read the node

```bash
cat demo-vault/books/meditations.md
```

Frontmatter first — the contract every downstream stage relies on (`04-VAULT.md`) — then the
source counts, then `*Not yet distilled.*`. That last line is the hand-off to the next step.

## 3. Distill it (needs Claude Code)

Interactively, from a Claude Code session opened in the repository — Claude Code discovers the
skill through `.claude/skills/distill/SKILL.md`, which points at the canonical text in
`skills/distill/distill.md`:

> distill Meditations

or headlessly:

```bash
bash quickstart.sh --with-claude
```

Both write `demo-vault/distill/distill-meditations.md` — the book's 20%, your marks mapped
onto it, a corroboration section that says which marked ideas left a receipt in the fixture's
reader journal, and an *Apply now* list. The node is rebuilt and now transcludes it. What the
method is, why the fidelity tag on line one matters, and exactly what leaves your machine when
the agent runs: `05-DISTILL.md`.

## 4. Now your own library

First, in the shell you will use:

```bash
source .venv/bin/activate      # the venv the quickstart built; `python` is now its interpreter
rm -rf out/                    # it holds only the fixture's results; left in place, the fixture's book would merge into YOUR vault
```

(Every stage reads and writes under `out/`, or under `RG_OUT` if you set it. Steps 4–5 merge
whatever is there — so the fixture's manifest and OCR output would give your vault a
*Meditations* node you never read.)

| you have | run | then |
|---|---|---|
| a Kindle (plug it in; `documents/My Clippings.txt`) | `python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" --out out/kindle-highlights.json` | steps 4–5 of the quickstart: `python corpus/merge_corpus.py`, then `python vault/build_nodes.py --vault <your vault>` |
| the Kindle app's *Export Notes* email (HTML) | `python -m capture.kindle html notebook.html --out out/kindle-highlights.json` | same |
| a Readwise export (CSV) | `python -m capture.kindle readwise highlights.csv --out out/kindle-highlights.json` | same |
| photographed pages | a folder anywhere with one sub-folder per book (`<folder>/<book-slug>/*.jpg`, optional `notes.md`); then `python capture/pages/manifest.py --pages <folder> --out out/manifest.json`, `python capture/pages/ocr.py --dir <folder> --out out/ocr.jsonl --engine vision` (macOS; `stub` elsewhere), `python corpus/build_bookcorpus.py`, then steps 4–5 | `03-PHOTOS-AND-NOTES.md` |

Several sources merge: `python -m capture.kindle clippings a.txt readwise b.csv --out …` dedupes
the same highlight seen twice. Set `VAULT` to your real vault (an Obsidian vault or a plain
folder — `04-VAULT.md`) and `RG_OUT` if you want the working files somewhere other than `./out`.

The one rule for your own data: **nothing under `out/` or your vault ever enters this
repository.** `out/` is git-ignored by directory, so the default for a new artifact is "not
committed" (`reference/PITFALLS.md` on why the exclusion is on the directory, not the file).

## 5. The tests

```bash
bash tests/run.sh
```

Runs everything that works on your platform (the Apple Vision test only on macOS with
`requirements-mac.txt` installed) using the venv the quickstart built. Contributions are
expected to keep it green — `CONTRIBUTING.md`.

## 6. Where this goes

Praxis (`06-PRAXIS.md`) and the Tutor (`07-TUTOR.md`) close the loop — an index of ideas you
actually used, and one cited lesson a day to a channel you already open — and the Librarian
(`08-LIBRARIAN.md`) looks for relationships and is built to refuse most of what it finds.
**None of the three is in this release.** The README's status table says which version each
arrives in; `docs/reference/AGENTS.md` has the designs and the evidence behind them.
