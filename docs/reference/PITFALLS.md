# Pitfalls: how this pipeline lied, and how it was caught

This is a catalogue of the failure modes that actually occurred while building a personal-archive
pipeline against one real corpus — 2,352 notes, 3,372 OCR'd images, 143 extracted documents,
800 photographed book pages, and 4,425 e-reader highlights across 78 annotated titles (88 books
in the merged corpus) — together with the symptom, the root cause, the thing that detected it,
and the fix. Almost none of them threw an exception. The pipeline's characteristic failure was to return a
smaller, cleaner, more confident answer than the truth, and to keep doing so until something
outside the pipeline contradicted it. Read the first family carefully; it accounts for four of the
twelve defects below and it is the one a fork of this code is most likely to inherit.

---

## Family 1: absence of data read as a finding

**The shape.** A stage produces less data than the world contains. A later stage — human or agent —
reads the shortfall as information about the world rather than about the pipeline. The output is
not an error; it is a *finding*, expressed fluently, with citations to real records.

Four instances, all in the same project:

| # | What was missing | What was concluded | Cost |
|---|---|---|---|
| 1 | `null` vs `[]` on a per-page `marks` field | "The mark extractor is broken" | An agent filed a bug against code that worked |
| 2 | Photographs of pages the reader never photographed | "The reader never engaged with chapter N" | A shipped, retracted claim |
| 3 | Stale single-channel stats on a derived vault node | "This book has no highlight layer" | A **verifier** killed a candidate edge on a false premise; the kill was later overturned |
| 4 | Books below a volume floor | (silent) | 44 books, 214 highlights, 20 of 44 typed notes dropped |

### 1.1 — `[]` and `null` are not the same absence

The per-page record carried a `marks` field. Pages that had been examined by a cataloguing agent and
found to carry no marks got `[]`. Pages nobody had examined got the same `[]`, because the builder
wrote `c.get("marks", [])` against a possibly-absent catalogue record.

An agent reading the corpus saw hundreds of pages with `marks: []`, correctly reasoned that a
reading archive cannot be that unmarked, and reported an extractor bug. There was no extractor bug.
There was an unexamined majority rendered as a clean examined one.

The fix is to make "assessed" a field of its own rather than an inference from emptiness:

```python
"catalogued": bool(c),
"marks":  c.get("marks", [])  if c else None,   # [] = looked, found none
"colors": c.get("highlight_colors", []) if c else None,
```

and then to propagate that distinction into every human-readable rendering. The merge stage prints
the disclaimer directly into the book file it emits, so a downstream reader cannot miss it:

```
### photo page 3 — NOT CATALOGUED — no mark data extracted;
    absence here means unassessed, NOT unmarked
```

Writing the caveat into the *artifact* rather than into the prompt is the durable half of the fix.
Prompts are per-run; the artifact outlives the run and is read by agents nobody briefed.

### 1.2 — Sampling bias: a channel's silence is not the world's silence

The first analysis pass ran over photographed book pages only. It produced a finding of the form
"the reader never marked the chapter on topic N" — clean, specific, and satisfying to read.

The e-reader channel, joined later, contains **22 highlights on that chapter**. The finding was
false and was retracted.

The mechanism is arithmetic, not subtle. Photographs are a biased sample of what a reader marks:

| Book | Photographed pages | E-reader highlights |
|---|---|---|
| Book A | 53 | 167 |
| Book B | 19 | 107 |

Any "never engaged with X" claim built on the left-hand column is a claim about photography habits.
Every gap finding produced before the join is suspect on the same grounds, and they were treated as
such rather than individually re-litigated.

The rule that replaced it, stated in the merge script's docstring (`corpus/merge_corpus.py`) and
repeated in every downstream dispatch (`agents/distill/DISTILL_PROMPT.md`, rule 3):

> Never infer a gap from missing data. Only claim a gap with positive coverage of the surrounding
> material in **both** channels.

Note what this does *not* say. It does not say "get more data." Two channels do not make a census —
they make two biased samples whose intersection is better evidence than either alone. Neither
channel here is a superset of the other: the e-reader channel has span-level exact text, colour and
location; photographs have pen marks, marginalia, filled-in worksheets, and books never read on a
screen.

### 1.3 — Stale derived artifacts are not inert; they actively lie

The vault carries one generated markdown node per book (`<vault>/books/<slug>.md`, written by
`vault/build_nodes.py`), with frontmatter summarising that book's marks. Those nodes were generated when photographs were the only channel. After the highlight join,
the nodes still read:

```yaml
highlight_colors: [grey:2]
```

for a book with 107 e-reader highlights.

A **verifier** agent — an adversarial reviewer whose entire job is to kill unsupported claims — read
that node, concluded the book had no highlight layer, and refuted a claim whose eight cited passages
were, on re-adjudication, all verbatim in the raw corpus. The kill was overturned; the edge went
back to being a candidate, not a finding (`VERIFICATION.md` §4 has the full account). The safety
mechanism was turned into an attack vector by a file it had every reason to trust.

Two fixes, and the second matters more than the first:

1. The node generator (`vault/build_nodes.py`) now reports the current channel's statistics
   (`kindle_highlights`, `typed_notes`, `kindle_colors`) alongside the photographic ones.
2. The rebuild order is documented as load-bearing and stale outputs are deleted rather than left:

   ```
   corpus/build_bookcorpus.py  →  corpus/merge_corpus.py  →  vault/build_nodes.py
   ```

   ```python
   if dest.exists():
       for f in dest.glob("*.json"):
           f.unlink()  # stale files from an older membership rule are worse than absent ones
   ```

If a generator can leave a file behind that no longer corresponds to any input, it will, and
something downstream will read it.

### 1.4 — Volume thresholds tuned against noise that discarded signal

Two floors were introduced to keep thin material out of the corpus. Both were tuned on
*highlight volume*. The thing actually being sought was *typed notes* — the reader's own words,
which are 44 records in 4,425 (~1%).

Volume and value turned out to be uncorrelated. Measured against the reference corpus's crawl:

| Rejected floor | Books dropped | Highlights dropped | **Typed notes dropped** |
|---|---|---|---|
| `kindle >= 25` for highlight-only books | 44 | 214 | **20 of 44** |
| `kindle < 10 AND photos < 5` | 41 | — | — |

Half the corpus's rarest signal sat below a threshold designed to remove noise. The densest
note-taking anywhere in the library was in a book with fewer than 25 highlights. The second floor
also produced orphans: a book with 9 highlights and 3 photographed pages vanished from the corpus
while its vault node remained, pointing at nothing — instance 1.3 all over again, one stage later.

Both floors were removed:

```python
# No volume floor: if it was marked at all, it is in.
if b["asin"] not in seen_kindle and b["n"] >= 1:
```

and the node generator was made to take its membership from the corpus rather than re-deriving it:

```python
# A node threshold that disagrees with the corpus threshold is how books end up in the
# corpus with no node, or with a node and no corpus behind it. Corpus membership IS node
# membership.
if not pages and not kindle: continue
```

The one floor that remains is on photographed pages rather than highlight volume: `RG_MIN_PAGES`
(default 1; the reference corpus used 3), applied in `corpus/build_bookcorpus.py` before the merge.
A book with fewer OCR'd pages than that is dropped from the page channel; its e-reader highlights
still enter the merge on their own.

**The generalisable lesson, four times over:** a derived artifact that is stale or incomplete is not
inert. It actively corrupts every consumer that trusts it — including the consumers you built to
catch corruption.

---

## Family 2: everything else

### 2.1 — Content filters kill bulk verbatim transcription. Stop transcribing; judge instead

**Symptom.** Five consecutive agents dispatched to transcribe batches of personal-archive images
died with `Output blocked by content filtering policy`, salvaging 14 usable records out of 150. Each
death took the whole batch, not the offending image.

**Root cause.** The task was "emit a long verbatim transcription of this personal document,"
repeated dozens of times per session. A personal archive contains personal documents; long verbatim
reproduction of them is exactly what an output filter is built to stop. Smaller batches would have
reduced blast radius, not incidence.

**Fix — invert the information flow.** Run a deterministic OCR engine first, then ship the OCR text
*alongside* the image and ask the agent for a verdict rather than a transcription:

```json
{"bucket": "text_dominant", "ocr_verdict": "matches", "ocr_conf": 0.95, "annotations": true}
```

Results: output per image fell from ~300 tokens to ~30. Mortality went from 5/5 to 0 — the first
judge batch completed 12/12, and a subsequent wave ran 6/6 agents over 72 images. And the redesign
produced *better* evidence than the thing it replaced: a direct verdict on whether the OCR matches
the page is a stronger agreement signal than string distance between two independent
transcriptions, which conflates "the engine failed" with "the two transcribers formatted
differently."

This is worth generalising. When an agent's output has to reproduce sensitive input, you are
fighting the platform. When its output is a small judgement *about* the input, you are not. Design
for the second shape whenever the pipeline can produce the raw text itself.

### 2.2 — Silent truncation in a review harness mis-calibrated a human

**Symptom.** A human reviewer scored a calibration sample and disagreed with the pipeline on two
purge decisions. Those two disagreements produced a headline number — purge precision 3/5 = 60% —
which was about to be used to set a deletion threshold.

**Root cause.** The review generator truncated OCR text at 700 characters under the heading
**"What the OCR actually read."** On one image the header stated 3,429 characters and the body
showed roughly 700, ending in an ellipsis. A reviewer told *this is what the engine read*, shown a
fifth of a page, correctly says "keep."

**Detection.** The reviewer noticed the mismatch between the stated character count and the visible
text and flagged it. Nothing in the pipeline could have detected it; the artifact was internally
consistent and the code was working as written.

**Consequence.** The calibration was invalidated in full. Both the precision figure and the
explanation offered for the two failures were retracted. What survived — that the pipeline's errors
were all in the same direction, never "you should have deleted that" — was downgraded from measured
to indicative, because it was scored against the same broken artifact.

**Fix.** Show everything, or label the cut explicitly and unmistakably:

```python
DISPLAY_CAP = 20000
excerpt = text[:DISPLAY_CAP] + (
    f"\n\n[… DISPLAY CUT at {DISPLAY_CAP:,} chars — the OCR captured {len(text):,}. "
    "This is a display limit, NOT an OCR failure.]" if truncated
    else "\n\n— end of OCR output —")
```

The heading became "Full OCR output — all N characters," and the reviewer instructions now say the
text is complete, so apparent early stopping is a real finding worth reporting.

**The label was the defect, not the truncation.** "First 700 of 3,429" would have been fine. A
review artifact that misrepresents the thing under review is worse than no review at all, because
it yields confident numbers that measure the tool instead of the system.

The same class of bug hit the machine reviewers independently: the agent batch builder capped
`ocr_text` at 1,200 characters while the record header reported the true length, so agents judged a
truncated excerpt against a full page and scored the missing text as OCR failure. Inflated
`partial` verdicts across a whole batch. An agent caught it by comparing the two fields. Cap raised
to 9,000 with an explicit `ocr_truncated` boolean; zero records now truncate.

### 2.3 — `splitlines()` on JSONL corrupts records silently

**Symptom.** A JSONL file with one record per line yields more lines than it has records.

**Root cause.** Python's `str.splitlines()` splits on eight characters beyond `\n`, including
`\v`, `\f` (U+000C), `\x1c`–`\x1e`, U+0085, and — the ones that matter here — **U+2028 LINE
SEPARATOR** and **U+2029 PARAGRAPH SEPARATOR**. PDF text extraction emits these. `json.dumps(...,
ensure_ascii=False)` writes them raw. Nothing in the round trip complains.

Measured on the output of `reference/extract_docs.py` (ran once on the reference corpus; not on
the quickstart path):

```
out/docs.jsonl        143 records, 143 physical newlines, 10 × U+2028 in one PDF record
  .splitlines()   -> 153 lines  -> 142 parsed,  11 JSON decode failures
  .split("\n")    -> 144 lines  -> 143 parsed,   0 failures
```

One record shattered into eleven fragments. With a `try/except: continue` around the parse — which
is what most loaders have — that record vanishes and the loader reports success.

**Fix.** Use `split("\n")` (or iterate the file object) everywhere a line is a record:

```python
for line in p.read_text().split("\n"):
    if line.strip():
        yield json.loads(line)
```

Two other guards are cheap and worth taking: pass `ensure_ascii=True` on write if the consumer set
is unknown, and assert `len(records) == expected` at every load site.

### 2.4 — Write-back clobbers `mtime`, destroying the only surviving provenance

**Symptom.** After a write-back pass (`reference/writeback.py` — ran once on the reference corpus;
not on the quickstart path), every note's modification date is the time of the pass.

**Root cause.** The importer wrote only the source note's ID into frontmatter — no dates, no folder. The
original created/modified timestamps survived exclusively as filesystem `st_birthtime`/`st_mtime`.
The filesystem *was* the provenance record, and `Path.write_text()` overwrites it.

This is worse than a one-time loss. The write-back reads `st_mtime` to populate a `modified:`
frontmatter field, so the second run stamps every note with the time of the first — the script
destroys the exact data it exists to preserve, and each re-run launders the damage further.

**Fix.** Capture before, restore after:

```python
st_before = md.stat()
md.write_text(new)
os.utime(md, (st_before.st_atime, st_before.st_mtime))
```

Those timestamps turned out to be load-bearing analysis input, not bookkeeping. Two of the project's
most interesting findings are *entirely* timestamp evidence — a ten-day execution of a note-taking
method visible only as a cluster of file dates, and a fourteen-minute gap between a note's last
modification and the creation of a tool derived from it. Delete the mtimes and those findings do not
exist.

### 2.5 — Rewrite references before moving files, never after

**Symptom.** Moving 821 duplicate attachments to a holding directory (`reference/dedupe.py` — ran
once on the reference corpus; not on the quickstart path) would break every note referencing them.

**Root cause.** Obsidian resolves embeds by **bare filename** (`![[Foo 1.jpg]]`), not by path.
Nothing in the reference records where the file lives, so a move is indistinguishable from a
deletion until something tries to render.

**Fix — ordering, not cleverness.** Rewrite every reference to point at the keeper *first*, then
move, then verify zero dangle:

```python
# --- rewrite embeds BEFORE moving, so nothing dangles mid-run ---
updated = EMBED_RE.sub(swap, text)
...
shutil.move(str(src), str(dst))
...
# --- verify nothing dangles ---
on_disk = {p.name for p in attach.rglob("*") if p.is_file()}
```

Rewriting first means the vault is consistent at every instant, including if the process dies
halfway: the worst intermediate state is a reference pointing at a file that still exists under two
names. Rewriting after means a crash leaves the vault broken with no record of what to repair.

Two supporting details. Keeper selection must be **deterministic** — shortest filename, ties
alphabetical — which happens to pick the original over the platform's ` 1`/` 2` copies. And nothing
is deleted: duplicates move to a holding directory, so reversing the entire run is a `mv`. Result:
355 groups, 821 redundant copies, 0.16 GB, 799 embed rewrites across 156 notes, **0 broken embeds
after**.

### 2.6 — A regenerator that clobbers hand-authored fields makes curation impossible

**Symptom.** Regenerating the per-book vault nodes (`vault/build_nodes.py`) would erase any field an
agent or human had added to them.

**Root cause.** The node is a generated file, so the generator owned all of it. But the design calls
for a curated graph layer *on top of* those nodes — `related:` edges, `outcome:` records of what
happened when the book was applied, `applied_in:` receipts for where an idea was used outside the
book. A generator that overwrites those fields
makes the graph unbuildable on its own substrate: every rebuild resets the curation to zero, so
curation never accumulates.

**Fix.** Declare reserved keys, parse them out of the existing file, carry them forward verbatim:

```python
PRESERVE = ("related", "outcome", "applied_in", "status")

def carry(path):
    """Hand-authored frontmatter fields of an existing node, as raw lines (multi-line lists kept)."""
    ...
    # an empty `related: []` is the builder's own default, not a hand edit — drop it so it re-derives
    return {k: v for k, v in kept.items() if not (len(v) == 1 and v[0].strip().endswith(": []"))}
```

The parser must handle list and block continuations, and it must treat an empty stub as absent so
the generator can re-emit it. The corresponding rule in the writer is the mirror image: a generator
writes `related: []` as a **reserved stub** it never populates itself.

Generalise it as an ownership contract, stated in the file that enforces it: derived fields belong
to the generator, reserved fields belong to the curator, and no field belongs to both.

### 2.7 — Tightening a membership rule to fix one bug dropped the three largest sources

**Symptom.** A rebuild of the book corpus silently lost the three largest book note sets in the
archive — 115, 34 and 21 captured pages respectively.

**Root cause.** Membership was the notes-folder rule (`RG_BOOK_FOLDER`) and nothing else. Those three
notes sit one level up, in the parent archive folder, outside the named folder. An earlier, looser
rule (`>= 5 images`) had the opposite failure: it promoted work decks to books. Each fix for one
direction re-opened the other.

**Fix — prefer evidence over structure.** A folder name is a guess about content; an agent that read
the page and named the book is evidence. Trust the catalogue (three or more catalogued pages naming
the same book), then a declared title (`capture/pages/manifest.py`'s folder-per-book layout or a
`notes.md` sidecar), and fall back to the notes-folder rule (`RG_BOOK_FOLDER`) only where neither
reached:

```python
BOOK_FOLDER = os.environ.get("RG_BOOK_FOLDER", DEFAULT_FOLDER)   # the notes-folder rule

def note_book(n):
    named = [strip_author(cat[im["name"]]["book"]) for im in n.get("images", [])
             if im["name"] in cat and cat[im["name"]].get("book")]
    if len(named) >= 3:
        return collections.Counter(named).most_common(1)[0][0], "catalog"
    if n.get("book"):                      # a manifest or sidecar that declares its title
        return n["book"].strip(), "declared"
    if BOOK_FOLDER in n.get("folder", ""):
        ...
```

Two things make this safe. The rule records *how* each book was matched (`catalog` / `declared` /
`folder`), so the provenance of a membership decision is inspectable. And membership is decided in
**exactly one place** — an earlier version re-derived it independently in the node generator, so when the rule
proved wrong it had to be fixed in two files and was fixed in one.

### 2.8 — A scraper whose failure mode is "fewer results" needs a plausibility check on itself

**Symptom.** None. Zero exceptions, zero warnings, complete-looking output for every book.

**Root cause.** Two independent bugs in a paginated web crawler, both failing by returning zero:

1. The pagination continuation token lives on an element identified by **class**, not id.
   `getElementById` returned `null`, the loop exited after page one, and every book capped at
   roughly one page of results.
2. Continuation responses are **bare fragments** with no outer container element, so a structural
   child selector rooted at that container matched 98 rows on page one and 0 on every page after.

Both would have shipped roughly a quarter of the data as if it were all of it.

**Detection came from a smell, not an error.** Six unrelated books all returned counts in a 92–97
band. That is a cap, not natural variation — real reading behaviour does not converge on a
five-count window across unrelated titles. Once fixed, one book went from 97 to 376 highlights;
the corpus maximum is 460.

Post-fix the same check passes cleanly on the reference corpus, and it is worth keeping as a
permanent assertion:

```
78 books · 4,425 annotations · max 460 · 17 books above 100 · 0 books in the 92–97 band
```

That assertion now lives in `capture/kindle/plausibility.py` — the sorted per-book count vector,
printed every run. The reference crawler itself ships in v0.3 (Designed); provider selectors drift,
and the plausibility check is the part to keep.

**The lesson:** when a scraper's failure mode is an empty result, no amount of error handling will
tell you anything. It needs an independent plausibility check on its own output distribution.

---

## Checks that would have caught these earlier

Ordered by how much they would have caught for how little they cost.

**1. Reconcile counts across every stage boundary, and assert it.** Records in must equal records
out plus records explicitly rejected, with the rejection reason recorded. This catches 1.4, 2.3 and
2.7 outright.

It also caught a defect that was live in this pipeline for some time. The merged corpus manifest
reported **88 books** while `out/merged/` held **87 files**, because two distinct works — a book and
a third-party summary of the same book — normalised to the same slug, so the second write silently
overwrote the first. Two highlights were lost and the manifest overstated the corpus by one.
`corpus/merge_corpus.py` now runs a `disambiguate()` step that gives every row a unique slug, paying
for the subtitle only when a collision occurs, and the manifest and the directory agree. Two lines
of assertion would have surfaced it the day it appeared, and they are still worth adding:

```python
assert len({r["slug"] for r in manifest}) == len(manifest), "slug collision"
assert len(list(DEST.glob("*.json"))) - 1 == len(manifest)
```

**2. Reconcile counts across *channels*, not just stages.** For every entity present in more than
one source, compare the per-entity counts and flag large asymmetries. `photos=19, kindle=107` is a
sampling-bias warning that prints itself. This is the cheapest possible defence against Family 1.

**3. Make "not assessed" a first-class value and test for it.** Never let an empty container stand
in for an unexamined one. Assert that no summary statistic is computed over a population containing
`null` assessments without reporting the `null` count alongside it.

**4. Round-trip test every generator.** Generate, hand-edit a reserved field, regenerate, assert the
edit survives byte-for-byte. Five lines of test. Without it, 2.6 is discovered by losing curation
you cannot reconstruct.

**5. Plausibility bounds on any scraper or extractor.** Assert the output distribution is not
degenerate: no suspicious clustering near a round number, a maximum meaningfully above any suspected
page size, a spread wider than a single page's worth. `0 results in the 92–97 band` is a real test.

**6. Freshness assertions between a generator and its output.** If `vault/build_nodes.py` reads
`out/merged/`, refuse to run — or at minimum warn loudly — when any input is newer than the output
it claims to describe. Every instance of 1.3 is a freshness violation.

**7. Never let a display path silently reshape data.** Any truncation, rounding, or sampling in a
human- or agent-facing artifact must be labelled at the point of the cut, with the true magnitude
named. If a heading asserts completeness, the code under it must enforce completeness.

**8. Preserve filesystem metadata explicitly, and test that you did.** `stat` before, `os.utime`
after, and an assertion in the test suite that a no-op write-back leaves every `mtime` unchanged.

**9. Prefer verdicts to reproductions when an agent is in the loop.** It is cheaper, it is more
robust to platform filtering, and — the part that surprises people — it usually produces a stronger
signal than the reproduction would have.

---

## What this pipeline still gets wrong

Stated plainly, because a pitfalls document that claims to be complete is committing the defect it
describes.

- The slug collision in check 1 is fixed by `disambiguate()`, but the stage-boundary assertions in
  check 1 are still not written; the next collision of a different shape will be found the same
  slow way.
- `reference/classify.py` — the API classification path — has **never been executed** against this
  corpus. It is a reference implementation, off the quickstart path. It also still uses
  `splitlines()` in three places (see 2.3).
- Highlight-colour detection from photographs (`reference/detect_highlights.py`) measured ~55%
  agreement with agent labels and was not shipped as a stage. Any analysis that treats photographed
  colour as data is unsupported.
- A first attempt to find receipts — places outside the book where a marked passage was used —
  matched on single words and put the noise floor at 782 files. Its numbers are void. A working
  version needs distinctive multi-word phrases.
- Twenty-eight candidate cross-book edges were generated by four independent lenses and each
  attacked by three adversarial verifiers. Twenty-seven refutations stand. One kill was overturned
  on re-adjudication: two of the three skeptics had read a stale derived node instead of the raw
  corpus (instance 1.3), and every one of the eight cited passages turned out to be verbatim in the
  raw data. That edge is a candidate again, not a finding — overturning a kill does not make the
  edge true. **Zero verified cross-book edges.** The refutation machinery works. The premise that
  such relationships are sitting there waiting to be found does not — at least not at this corpus
  size, and not by these methods.
