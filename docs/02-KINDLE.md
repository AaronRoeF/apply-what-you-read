# 02 — Getting your Kindle annotations out

Most of the value is in files you already have. This document covers three of them first —
the device's `My Clippings.txt`, the Kindle app's "Export Notes" HTML, a Readwise CSV — and
the one command that turns any of them, or all three at once, into
`out/kindle-highlights.json`. A reader with a Kindle and this section should not need
anything else to get to that file.

The second half is for readers whose provider offers no export: the reference crawler that
drove a notebook web view, its structural boundaries, and — the part worth reading if you
read nothing else — the two parser bugs that made that extractor silently return a quarter
of the data while reporting complete success. Both failed by returning **zero**, which is
indistinguishable from "no more data". Nothing threw. The check that caught them now runs on
every file parse too.

---

## Three file formats first

Every parser normalises to the same record (`capture/kindle/schema.py`): per book an `asin`
(never null — synthesised when the source has none), `title`, `author`, and the
annotations; per annotation an `id`, `color` (or null), `page` (or null — many sources carry
none), `location` (always present), `text`, and `note` (`""` when absent, never null). The
merge stage (`corpus/merge_corpus.py`) reads that file and nothing else from this channel.

### (a) `My Clippings.txt` — the device file

Plug the Kindle in over USB. It mounts as a drive; the file is `documents/My Clippings.txt`.
Every Kindle writes it as you read, with no account and no app involved, which makes it the
most universal on-ramp — and the lossiest.

What it carries: title and author, the page number when the edition has one, the location
range, a timestamp, and the selected text. One record per highlight, note or bookmark,
separated by a line of ten `=`:

```
Meditations (Marcus Aurelius)
- Your Highlight on page 1 | Location 100-104 | Added on Sunday, March 1, 2026 8:00:00 AM

Remember how long thou hast already put off these things, ...
==========
```

A typed note and a bookmark use the same header with `Note` or `Bookmark` in place of
`Highlight` — `- Your Note on page 3 | Location 142 | Added on …` followed by the note text,
`- Your Bookmark on page 50 | Location 600 | Added on …` with no body. Older firmware writes
`- Your Highlight at location 100-104 | Added on …` with no page at all; the parser reads both.

What it loses and what it does wrong, all of which the parser (`capture/kindle/clippings.py`)
handles:

- **No colour.** The device file does not record it. If colour matters to you, use one of
  the other two formats.
- **It accumulates.** Re-selecting a longer span leaves the shorter one behind as a
  separate record. The parser drops a highlight whose text is contained in a later,
  overlapping one — the reader re-selected, and the longer span wins.
- **Duplicates on re-sync.** Exact duplicates (same start location, same text) appear
  whenever the device re-syncs; the first is kept.
- **Two metadata forms.** Newer firmware writes `on page N | Location A-B`; older devices
  write `at location A-B`. Both parse.
- **Notes are separate records.** A typed note is its own record at a single location; it
  attaches to the highlight whose range contains it, and a note with no containing
  highlight is kept as a note-only record rather than dropped.
- **Bookmarks** are dropped; they carry no text.
- **BOM and CRLF.** The file starts with a UTF-8 byte-order mark and uses Windows line
  endings. Both are stripped.
- **A non-empty file that yields zero records is an error**, not a clean exit. The command
  prints `EMPTY PARSE` with the first block of the file and exits 1.

Pass `--diagnose` to print one line per record as it is read — kind, page, location range,
title — followed by a tally: `duplicates=… superseded=… notes_attached=… notes_orphan=…
bookmarks=… unparsed=…`. If the count you expected and the count you got disagree, this is
where the difference is.

### (b) The Kindle app's "Export Notes" HTML

In the Kindle app on a phone or tablet, open the book, open its notebook, and choose the
export option; the app emails one HTML file per book to whatever address you give it. Email
it to yourself and save the attachment.

It keeps the two things the device file loses: **colour**, and the **page** number where the
edition has one. The structure is a flat sequence of `div`s — `bookTitle`, `authors`,
`sectionHeading`, then pairs of `noteHeading` and `noteText`, with the colour in a `span`
inside the heading. A `Note` heading immediately following a highlight attaches to that
highlight. The parser (`capture/kindle/notebook_html.py`) uses the standard library only, and
a non-empty file with none of those `div`s is an error that names the selectors it looked
for, so a mis-saved file cannot pass as an empty book.

### (c) A Readwise CSV export

From Readwise, export your highlights as CSV. The parser (`capture/kindle/readwise_csv.py`)
is **header-driven**: columns are found by name, with aliases, never by position, and a
missing required column (`Highlight`, `Book Title`) is a loud error that lists the headers
actually present and the alias table to extend. It keeps **colour** and the typed **note**.
It carries **no page number** — `page` is null on every record — and the `Amazon Book ID`
column is empty for books not bought on Kindle, in which case the record gets a synthetic
`asin` derived from title and author (prefixed `x`, so it can never collide with a real one).

### (d) The one command

```bash
# one source
# first: source .venv/bin/activate   (built by quickstart.sh; `python` is then its interpreter)
python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" --out out/kindle-highlights.json
python -m capture.kindle html ~/Downloads/meditations.html --out out/kindle-highlights.json
python -m capture.kindle readwise ~/Downloads/highlights.csv --out out/kindle-highlights.json

# several files of one kind
python -m capture.kindle html book-one.html book-two.html --out out/kindle-highlights.json

# several sources at once, merged
python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" \
    html ~/Downloads/meditations.html readwise ~/Downloads/highlights.csv \
    --out out/kindle-highlights.json

# a re-run, diffed against the last output
python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" \
    --out out/kindle-highlights.json --previous out/kindle-highlights.prev.json
```

`--out` defaults to `$RG_OUT/kindle-highlights.json`. Each kind keyword applies to every
path after it until the next keyword.

When several sources are given they **merge by book and dedupe by annotation** — the same
highlight seen in two exports lands once. The annotation id is a hash of title, location
and text (`kh:…`), so it is the same whichever file produced it; the book key is the Amazon
id when the source carries one and the synthetic id otherwise. One consequence to know
about: a Readwise row that carries a real Amazon id and a clippings record for the same
book — which has none — key differently and land as two book records with the same title.
If the plausibility line reports more books than you own, that is the first thing to check;
prefer one source per book in that case.

Run on the fixture, the output is:

```
parsed clippings fixtures/meditations/clippings/My Clippings.txt: 35 annotations in 1 book(s)
wrote out/kindle-highlights.json: 1 books, 35 annotations
plausibility: books=1 annotations=35 sorted counts = [35]
  no plausibility flags
```

`fixtures/meditations/` carries all three formats for the same book — `clippings/My
Clippings.txt`, `export-html/meditations.html`, `readwise/highlights.csv` — and the record
they should all produce, `expected/kindle-highlights.json`. Running all three through the
merged form of the command yields one book and 35 annotations, which is the dedupe working.

### (e) What each loses

| Source | Colour | Page | Typed notes | Amazon id | Needs cleaning |
|---|---|---|---|---|---|
| `My Clippings.txt` | **lost** | when the edition has one | yes — attached by location range | no; synthetic | yes: superseded spans, re-sync duplicates, bookmarks — all dropped by the parser |
| Export Notes HTML | kept | kept | yes — attached to the preceding highlight | no; synthetic | no; one book per file |
| Readwise CSV | kept | **lost** | kept | when Readwise has it | no |

Store both `page` and `location`, require neither. In the reference corpus, 1,751 of 4,425
annotations carried a page and 2,674 carried only a location; a schema that made `page`
mandatory would have dropped 60% of the data.

### (f) The plausibility line, printed every run

The last thing every run prints is the sorted per-book count vector, from
`capture/kindle/plausibility.py`. It is a print statement, and it is the only reason the two
crawler bugs in the next section were ever found. Read it every run. Its flags are printed,
never fatal:

| Flag | What it means |
|---|---|
| `PAGE_CAP_SUSPECTED` | Three or more books with counts within 8 under the same round number (25, 50, 100, 200, 500, 1000). Unrelated books do not agree on a count; a cluster just under a round number is a page cap wearing a costume. For a file parse it usually means the export itself was truncated. |
| `ZERO_VS_NULL` | Books present with zero annotations, listed by title. "Looked, found nothing" is a real state and is shown so it cannot hide. |
| `RECRAWL_DIFF` | With `--previous`: per-book deltas against the earlier output. Two runs on the same input that disagree mean something is racing; two runs on a re-synced device that disagree tell you what changed. Identical runs say so. |

---

## The reference crawler (v0.3, Designed): technique and boundaries

The file parsers in the section above involve none of the questions that follow —
authentication, pagination, provider markup — and are the right first choice whenever an
export exists. What follows is for a provider that offers none: the technique, its
boundaries, and the two bugs. The crawler itself, `capture/kindle/notebook_crawl.py`, is
Designed for v0.3 — status labels are defined in the README's status table — and the
measurements below are from the ad hoc crawl that produced the reference corpus.

### The boundaries, first, because they are structural

These are not aspirations. They are properties of how the technique works and how this
repository is laid out.

1. **It runs only inside a session the reader authenticated themselves.** A browser
   is already logged in; automation attaches to that browser and drives it. The tooling
   never sees, stores, or transmits a password, a cookie jar, or a token. There is no
   credential path to secure because there is no credential path.
2. **It retrieves only the reader's own annotations** — the spans they selected and the
   notes they typed. Not book text, not chapters, not anything the reader did not
   personally mark.
3. **Extracted content never enters version control.** See the rule below. The repository
   ships code; the corpus stays on the reader's disk.
4. **Redistribution is out of scope.** The corpus is single-user and local. Nothing in this
   pipeline publishes, syncs, or shares extracted text, and nothing should be added that does.
5. **Terms of service vary by provider and are the reader's responsibility.** Read the
   agreement for the account you hold before running anything against it.

#### The .gitignore that enforces #3

The repository root `.gitignore`:

```gitignore
# Run artifacts and the local venv never enter git.
.venv/
out/
*.jsonl
ocr_vision
.env
.env.*
*.egg-info/
__pycache__/
.DS_Store
demo-vault/
```

Every stage of the pipeline writes to `out/`. The crawl output, the parsed exports, the
merged corpus, the per-book markdown — all of it lands under an ignored directory by
construction, so the default state of a new artifact is "uncommitted". That is the design:
forgetting to exclude a file is the failure mode, so the exclusion is on the directory, not
the file. A reader forking this repo gets scripts and gets nothing of the original
reader's library.

### The shape of the problem

An authenticated notebook view typically exposes:

| Surface | What it gives you |
|---|---|
| Library sidebar | Every title in the account, including titles with zero annotations |
| Per-title annotation list | The reader's spans, server-rendered, **first page only** |
| Continuation control | An opaque token identifying where the current page stopped |
| Per-annotation metadata | Colour or category, a position identifier, and the typed note if any |

Two things follow immediately. First, a client operating in the page context can read all
of this with ordinary DOM queries — there is no need to reverse-engineer a private API, and
the DOM is the more stable target because it is what the provider ships to its own users.
Second, **the annotation list is paginated and the page size is small**, which is where all
the difficulty lives.

#### The record to aim for

Whatever the provider's markup, normalise to a flat record per annotation — the same record
the file parsers emit. The fields that proved to carry weight, in the corpus behind this
repo:

| Field | Notes |
|---|---|
| `id` | Provider-stable identifier; the dedupe key across re-crawls |
| `text` | The exact selected span |
| `note` | The reader's typed note, usually absent |
| `color` | Provider's highlight category |
| `page` / `location` | Position. **Both**, because neither is always present |

### Pagination via continuation token

The loop is: render the first page, read the token, request the next slice, append,
repeat until the token is absent or the slice is empty.

```js
// Sketch. Selectors are per-provider; inspect the live DOM rather than
// copying anyone's.
let token = readToken(document);
const rows = [...parseRows(document)];
while (token) {
  const frag = await fetchNextSlice(token);   // returns HTML, not JSON
  const batch = parseRows(frag);
  if (batch.length === 0) break;             // <-- the dangerous line
  rows.push(...batch);
  token = readToken(frag);
}
```

The line marked dangerous is correct code. It is also the line that converts every parser
bug downstream of it into a clean, quiet, successful-looking early exit.

#### Bug one: the token was on a class, not an id

The continuation token was rendered on an element carrying it as a **class**, while the
extractor looked it up by **id**. `getElementById` returned `null`, the `while` condition
was false on the first evaluation, and the loop exited after page one. Every book capped at
roughly the provider's page size.

```js
// Wrong — assumes an id because ids are what tokens "usually" have.
const token = document.getElementById('next-token')?.value;

// Right — read the attribute the page actually uses.
const token = document.querySelector('.next-token')?.value;
```

The lesson is narrow and practical: **the selector for the token element is not an
implementation detail, it is the loop condition.** Get it wrong and the loop does not
error, it terminates. Verify the token selector against a live second page before trusting
the loop at all.

#### Bug two: continuation responses are bare fragments

Page one arrives wrapped in a container element. Pages two and beyond arrive as **bare
fragments with no wrapper** — the container exists only in the full-page render. A
structural child selector anchored on that wrapper therefore matched every row on page one
and nothing afterwards:

```js
// Matched 98 rows on page 1, 0 on every page after it.
frag.querySelectorAll('#annotation-list > .annotation-row');

// Matches on both shapes.
frag.querySelectorAll('.annotation-row');
```

Same failure signature as bug one: a real HTTP 200, real HTML, zero parsed records, and a
loop that concludes the book is finished.

### How they were caught: output plausibility, not an exception

Neither bug produced a stack trace, a non-200, an empty response body, or a log line that
looked wrong. The crawl reported zero errors. It was caught by looking at the **shape of
the output**:

> Six unrelated books all returned counts in a 92–97 band.

Unrelated books do not naturally agree on a count. A tight cluster just under a round
number is a page cap wearing a costume. Dense-marking behaviour is heavy-tailed — a few
titles far above everything else — and heavy-tailed distributions do not produce a mode
at 95.

Correcting the selectors changed one title from **97 records to 376**. Measured from the
corrected crawl artifact in `out/` (gitignored, so these are the only numbers that leave
the reader's disk):

| Metric | Value |
|---|---|
| Titles in the account | 82 |
| Titles with annotations | 78 |
| Annotations retrieved | 4,425 |
| Crawl errors | 0 |
| Titles exceeding 100 annotations | 17 |
| Largest single title | 460 |

Seventeen titles above 100 in the corrected run, none in the corrupted one. The pre-fix
crawl would have shipped roughly a quarter of the data with a clean bill of health.

### The generalisable rule

**Any extractor whose failure mode is an empty result needs an independent plausibility
check on its own output.** "No exception raised" is not evidence of completeness for this
class of program, because the null result and the correct result are the same value.

Concrete checks, cheapest first:

| Check | What it catches |
|---|---|
| **Distribution of per-unit counts** | Page caps and truncation. Print the sorted count vector. Clustering below a round number is the signature. Real distributions are lumpy and long-tailed. |
| **Coverage span vs. expected range** | Early exit within a unit. If position identifiers stop at 30% of a known length, the extractor stopped, the reader did not. |
| **Cross-channel reconciliation** | Systematic omission. Compare against an independent capture of the same material — an export, a second device, photographs. Disagreement is information; agreement on both sides is the only clean signal. |
| **Zero-vs-null discipline** | The extractor's own confusion. An empty list means "looked, found nothing". A null means "never looked". Collapsing them makes an unexamined unit look like a clean one. |
| **Re-crawl diff** | Nondeterministic truncation. Two runs that disagree on counts mean the loop is racing something. |

Add the first of these to the crawler itself. It is a `sorted(counts)` print statement and
it is the only reason the bugs above were found at all. In this repository it is
`capture/kindle/plausibility.py`, and the first, fourth and fifth checks in the table are
its three flags; the v0.3 crawler carries regression tests for both bugs, each asserting
that an empty parse of a non-empty response body is an error.

---

## Three second-order lessons from the resulting corpus

**Position identifiers are not uniform, so do not require one.** In the corpus behind this
repo, 1,751 of 4,425 annotations carry a page number and 2,674 carry only an internal
location offset. A schema that made `page` mandatory would have dropped 60% of the data —
another silent-zero, one schema layer up. Store both, require neither.

**Highlight colour is a weaker semantic signal than it looks.** The distribution is
Yellow 3,993, Pink 177, Aqua 136, Orange 106, uncoloured 13 — one default and a thin tail.
An early design in this project weighted rare colours as high-importance marks. Checking it
against the data showed colour clustering by *reading session* (a highlighter left on for a
stretch of pages) at least as often as by meaning, and one non-default colour turned out to
be the reader's list-and-procedure marker rather than an emphasis marker. Rarity is not
significance when rarity is explained by friction. Capture the colour; do not build
semantics on it without checking what the reader actually did with it. If you *know* what
your colours mean, say so: a colour key declared in `<vault>/READER.md` outranks any
inference an agent could make from frequency (see `04-VAULT.md`).

**Absence in one channel is not absence of interest.** This corpus merges e-reader
annotations with photographs of physical pages. Analysis built on the photographs alone
produced confident findings of the form "the reader never engaged with chapter N" — which
the e-reader annotations falsified outright, in one case with 22 marks on the chapter said
to be untouched. The merge exists because neither channel is a superset: the account has
span-level exact text, the photographs have pen marks, marginalia, and books never read
digitally. `corpus/merge_corpus.py` writes the warning into every file it emits, and any
consumer of the corpus is expected to honour it: **never infer a gap from missing data;
claim one only with positive coverage of the surrounding material in both channels.**

---

## Before you trust an extractor of this kind

- [ ] Verify the continuation-token selector against a live second page, not page one.
- [ ] Verify the row selector against a continuation fragment, not the full-page render.
- [ ] Print the sorted per-unit count vector at the end of every run and read it.
- [ ] Assert that an empty parse of a non-empty response body is an **error**, not an exit.
- [ ] Distinguish empty from unassessed in the output schema.
- [ ] Confirm `out/` is ignored before the first run, not after.
