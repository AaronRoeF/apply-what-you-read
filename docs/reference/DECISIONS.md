# Decisions and reversals

This is the decision log for the pipeline: what was chosen, what was abandoned, and what
evidence forced each call. It exists because several of the most useful outcomes here were
*reversals* — plans that survived design review and died on contact with measurement. If
you fork this repo, the reversals are the part worth reading first, because they are the
places where an obvious-looking feature turned out to be a net negative and the numbers say
why. Every figure below can be followed back to the pipeline's own output or to the project
record, and all of it was measured on one real corpus (88 books, 4,425 highlights, 798
photographed pages); where a number was later invalidated, it is marked as invalid rather
than deleted.

---

## Summary

| # | Decision | Status | Deciding evidence |
|---|---|---|---|
| 1 | Compiled OCR binary -> Python bindings to the same framework | Reversed | Local toolchain could not build anything; same framework reachable from Python |
| 2 | OCR images, then purge the redundant originals | **Abandoned** | 13% of images / 9% of bytes eligible; ~186 MB against ~118 GB free |
| 3 | One classification path | Reversed to two, documented | Neither path dominates; the API path was never run here |
| 4 | Engine confidence as a keep/purge filter | Narrowed | Valid on flat prose, inverts on grids |
| 5 | Trust all recognised handwriting equally | Reversed | Stroke-derived text is reliable; pixel OCR fabricates entities |
| 6 | Cross-book edges as the primary output | **Abandoned** | 28 candidates generated; 27 refutations stand, one kill overturned to candidate-again; zero verified |
| 7 | Rank marks by rarity | Reversed | Rarity is explained by input friction, not significance |
| 8 | Single-word corroboration matcher | Discarded | Noise floor of 782 files; numbers void |

---

## 1. Toolchain: compiled binary abandoned for bindings to the same framework

The first OCR implementation was a small Swift program (`capture/pages/ocr_vision.swift`, ~2.7 KB) that
read image paths on stdin and emitted one JSON object per line. It never ran. The machine's
Command Line Tools installation shipped a duplicate `SwiftBridging` modulemap alongside a
compiler/SDK version skew, and `swiftc` could not build *anything* — not this program, not
a hello-world. Fixing it properly requires reinstalling the toolchain.

The pivot was to PyObjC (`capture/pages/ocr_vision.py`, ~4.1 KB), which calls the identical
`VNRecognizeTextRequest` API in the identical Vision framework. Same recogniser, same
output, no compiler.

**Cost of the pivot: low, and knowable in advance.** The program was one API call wrapped in
a JSON emitter; 81 lines of Swift became 110 lines of Python against the same framework. Both files
remain in the repo — the Swift version is the faster path if your toolchain works.

**Generalisable:** when a compiled component is a thin wrapper over a system framework,
"the toolchain is broken" is a cheap problem, not a blocking one. Check whether the same
framework has bindings in a language whose toolchain is already working before you spend a
session repairing the compiler. The pipeline went on to OCR 3,372 images with zero genuine
failures on the ported path.

---

## 2. The deletion that did not happen

**Original plan:** OCR every image, classify each as text-dominant / structural / non-text,
and purge the text-dominant ones — the images whose entire information content is now in
the note body as text. Purge was specified as a move to a holding directory, never `rm`,
gated on a human review of a stratified sample.

**Killed by measurement.** The rubric acquired one rule during classification: *any reader
annotation is an absolute veto on purge* — a highlight, a pen mark, a marginal note means
the image is kept regardless of bucket or confidence. That rule alone changed the outcome
by an order of magnitude.

| Measurement | Value |
|---|---|
| Effect of the annotation veto on the same 70 images | would-purge 34 -> **5** (85% reduction) |
| Images carrying reader annotation (of 142 judged) | 83 = **58%** |
| Purge-eligible after the veto | 18 / 142 = **13%** |
| Bytes reclaimed | 66 MB of 731 MB judged = **9%** |
| Extrapolated to the whole large-file tier | ~50 images, **~186 MB** |
| Free disk at decision time | **~118 GB** |

An earlier, separate measurement of the veto on a different candidate set showed the same
direction: 76 purge candidates fell to 48, with **28 removed (37%)** — each one a page the
reader had deliberately marked.

**Why the premise failed.** The corpus is a reading archive. Pages get photographed
*because* they were highlighted; the annotation is the reason the image exists at all. That
makes annotation density near-universal by construction, and it makes the purge rule
self-defeating: purging a text-dominant page keeps the book's printed words and destroys
the reader's marks on them.

**The decisive argument was not the disk space.** It was that the value being chased —
greppable, agent-readable text — had *already been captured*. Every image was OCR'd; the
text lands in the note at write-back whether or not the image survives. Purging adds
nothing to readability. It only destroys images.

**Decision: keep both channels.** Text in the note, image on disk, classification retained
as metadata. Compare the two reclaim operations honestly:

| | Dedupe | Purge |
|---|---|---|
| What it removes | byte-identical copies | judged-redundant originals |
| Judgement required | none | model + human review gate |
| Reclaim | 821 files, ~156 MB | ~50 files, ~186 MB |
| Reversible | yes (a `mv` back) | no, in effect |
| Verdict | **shipped** | **abandoned** |

Dedupe is free and lossless, so it ran. Purge is an irreversible operation for a rounding
error against available disk, so it did not.

**What the classification work bought anyway** — all of it kept as metadata, and this is
now the most valuable output of the effort:

- `annotations` (58% of judged images) — a retrieval signal marking what the reader judged
  important. No model had to infer it.
- `structural` (27%) — images whose extracted text is unsafe read alone, flagging what
  needs table-aware handling downstream.
- `partial` / `mismatch` verdicts (30%) — the quarantine set that protects downstream
  consumers from fabricated entities.

### 2a. The calibration that measured the wrong thing

Before the purge was abandoned, a human calibration run scored the classifier at 92%
agreement on a stratified sample and **60% purge precision**. Both numbers are **void**.

The review artifact generator truncated OCR output at 700 characters under the heading
"What the OCR actually read" — asserting completeness while displaying a fifth of the text.
On one reviewed page the header stated 3,429 characters and the body showed roughly 700,
ending in an ellipsis. A reviewer told "this is what the OCR read," shown text that stops
mid-page, correctly says *keep*. The disagreements may have been reactions to the display
bug rather than to the images.

**The label was the failure, not the truncation.** "First 700 of 3,429" would have been
fine. The generator now emits the full text in a collapsed callout, states the length
explicitly, and marks any display cap as a display cap.

**Rule: a review artifact that misrepresents the thing under review is worse than no review,
because it produces confident numbers that measure the tool instead of the system.**

---

## 3. Two classification paths documented, rather than one chosen

Stage 3 is the only step needing a vision model. It can run two ways, and neither dominates,
so both are documented with a shared output contract and honest selection guidance. See
[`CLASSIFY-PATHS.md`](CLASSIFY-PATHS.md).

- **Path A — API.** `reference/classify.py` with an API key. Unattended, resumable per image,
  reproducible by a stranger, roughly $0.008/image.
- **Path B — agent.** Batch files dispatched to a coding agent that can read images. No
  billing setup, supervised, reproducible only with the same agent harness.

**Honest disclosure: `reference/classify.py` is a reference implementation that was never
executed against this corpus.** Every classification result quoted in this repo came from Path B. The
code is written, the contract is shared, the resume logic is there — but it has not been run
at scale here, and you should treat it accordingly.

Path B's real failure mode is documented because it is not obvious: an early design asked
agents to emit long verbatim transcriptions of personal documents, and **all five dispatched
agents died with `Output blocked by content filtering policy`, salvaging 14 images of 150.**
Each death killed a whole batch.

**Redesign: judge, don't transcribe.** The batch file now ships the deterministic OCR text
*alongside* each image, and the agent returns a bucket plus a verdict on whether the OCR
matches (matches / partial / mismatch) plus a confidence. Output fell from roughly 300 tokens
per image to about 30, the agent never emits document contents, and the agreement signal got
*stronger* — a direct verdict on OCR correctness beats string distance between two
transcriptions. Survival went from 0/5 agents to 6/6 on the next wave.

A side benefit worth stealing: an agent reading its own batch file caught a bug in the batch
generator. It flagged `ocr_text` showing ~1,200 characters against a stated `ocr_chars` of
2,820 — the generator was truncating, so agents were judging a truncated sample against a
full page and reading missing text as OCR failure. The cap was raised to 9,000 and the
affected batch re-run.

---

## 4. Engine confidence is conditionally valid, not simply valid or invalid

This one reversed twice. First reading: the recogniser's own confidence score is unreliable.
Second reading, on aggregate data: it is a good pre-filter. Final position, and the one that
survives: **it is conditional, and the condition is the content type.**

Aggregate over 144 judged images:

| Engine confidence | matches | partial | mismatch |
|---|---|---|---|
| >= 0.98 | 98 | 10 | 1 |
| < 0.90 | 1 | 14 | 7 |

That looks like a strong filter, and on flat prose it is. Within grids it inverts: a
spreadsheet at confidence 0.85 lost roughly 400 cells to arbitrary reading order, and a
comparison table at confidence **1.00** destroyed every row-to-column binding while
returning token-perfect text.

The formulation that resolves it: **engine confidence tracks glyph legibility, not
information retention.** It predicts well because most of the corpus is flat prose. It says
nothing about whether the *structure* carrying the meaning survived.

**Rule: confidence is a valid signal only on flat prose. "Contains a grid" is an override,
never a score input.** A related rubric correction came from the same evidence in the other
direction — a plain bullet-list slide is text-dominant, not structural, because a bullet list
encodes nothing spatially. The original rubric said "slide implies structural" and was wrong.

The verifier consequently refuses to collapse its signals into one number until the end. It
scores four independently — engine confidence, dictionary word validity, characters recovered
per megapixel, and agreement with a second extractor — because each catches a different
failure and their disagreement is itself informative. Word validity is the best cheap
detector of total extraction failure: garbage OCR produces character soup, and soup scores
near zero.

---

## 5. Trust is tiered by input type, not by legibility

Two kinds of handwriting live in this corpus and they have opposite reliability, for a
reason invisible from the output:

| Source | How it is recognised | Trust |
|---|---|---|
| Stylus notes taken on the device | **stroke data** — pen path, order, direction | trusted, authoritative |
| Photographed handwriting (paper, e-ink screens) | pixel OCR only | **quarantined** |

Recognising strokes is a fundamentally easier problem than recognising a flat image of ink.
Measured on one identical file, the stroke-based recogniser produced a coherent sentence plus
a numbered list that the pixel recogniser missed entirely; the pixel recogniser's version of
the same words was garbled at the character level.

The failure mode that forces the quarantine is worse than garbling, though. **Pixel OCR on
handwriting fabricates proper nouns and numerals, and reads fluently while doing it** — a
company name comes back as an unrelated common-word phrase, a quantity of five comes back as
fifteen. Nothing in the output signals that this happened; confidence stays high. For any
downstream consumer that reasons about companies and numbers, a confidently asserted
fabricated entity is strictly worse than a gap, because a gap is visible.

Two operational consequences:

1. **Stroke-recognised text is authoritative and is never overwritten by pixel OCR.** In this
   corpus 237 of 241 stylus-drawing embeds already carried the stroke-recognised text at
   import; the pixel OCR of the same 239 files averaged 0.823 confidence with 129 below 0.90.
   Running it was both redundant and worse.
2. **The quarantine set is narrow and named.** It is *photographed* handwriting only, plus
   anything the classifier scored `partial` or `mismatch` (about 30% of judged images).
   Scoping it precisely is what keeps the rule enforceable.

---

## 6. Cross-book edges: tested, refuted, abandoned

**This was supposed to be the payoff.** The hypothesis: with a corpus of books, marks, and
notes, the valuable structure is a graph of typed, evidence-backed connections *between*
sources — this book supplies the mechanism that book only names; these two contradict each
other and the contradiction was never resolved.

**Method.** Twenty-eight candidate edges were generated by four independent lenses across 25
unique source pairs. Each candidate was then attacked by three adversarial verifiers working
directly from the raw JSON, with a standing instruction that an edge which cannot cite text
is deleted rather than downgraded.

**Result: 28 proposed; 27 refutations stand; one kill was overturned on re-adjudication.
Zero verified cross-book edges.** The overturned edge is a candidate again, not a finding —
overturning a kill does not make the edge true. What overturned it is described at the end
of this section, because it is a lesson about verifiers rather than about books.

The three failure modes are worth naming, because they are what a candidate generator
produces when the premise is wrong:

- **Manufactured gaps.** By far the most common. The shape is "Source A names the problem
  but supplies no remedy; only Source B has the remedy." In nearly every case Source A *did*
  supply the remedy — usually a few pages from the quoted passage, and already marked by the
  reader. The gap was an artifact of the generator's retrieval window, not a property of the
  material.
- **Colour-rarity inflation.** Highlight colours were treated as a meaning signal, with rare
  colours read as emphasis. Verification found colours cluster by **reading session and
  location range** — a highlighter left on for a stretch — as often as by intent. Worse, the
  colour assumed to mean "this is important" turned out to be the reader's **bullet-list and
  procedure marker**. One edge was built on "rarest colour to rarest colour" where the colour
  in question was that book's *third most common*.
- **Genre truisms.** Two books in the same genre agreeing on a genre commonplace is a
  property of the shelf, not a discovery.

**State this plainly: the refutation machinery worked; the premise did not.** The design's
stated top risk was "the graph fills with plausible-but-generic edges," and its stated
mitigation was typed edges plus mandatory evidence plus an adversarial pass. The mitigation
performed exactly as specified. What it revealed is that book-to-book edges are not sitting
there waiting to be found in a personal reading corpus.

**A verification pass that returns nothing is a result, not a failed run.** The output was
recorded as a do-not-re-derive appendix: 27 pairs with the specific refutation that killed
each one, so nobody rebuilds them, plus the one pair marked candidate-again with the
carry-forward caveats from its re-adjudication. The generated graph file's frontmatter reads
`edges: 0`. What survived instead was a smaller and better-evidenced class: four
*intra*-book edges, where a question the reader typed is answered by a passage the same
reader highlighted in the same book.

Two observations from the run that generalise:

- **Independent convergence is evidence.** Three verifiers attacking three *different* edges,
  blind to each other, killed their edges by pointing at the same passage. Unprompted
  agreement between agents that were not coordinating is the strongest signal the exercise
  produced.
- **A stale derived artifact corrupts the verifier too.** This is the overturned kill. One
  edge was refuted by verifiers who had read a derived node built before a data source landed,
  saw statistics implying the source was absent, and concluded the edge had no basis. On
  re-adjudication it emerged that two of the three skeptics had read that stale
  node instead of the raw corpus, and every one of the eight passages the edge cited was
  verbatim in the raw data. The kill was overturned and the edge went back to *candidate* —
  not to *finding*, because a verifier's mistake is not evidence for the claim it failed to
  test. The node was stale, not empty. A derived artifact that is stale or incomplete is not
  inert — it actively corrupts every consumer that trusts it, and a verifier is a consumer.
  The standing instruction that followed: verifiers read the raw corpus, never a derived node.

---

## 7. The reframe: corroboration replaces rarity

The ranking that produced those candidates rested on an inference that does not hold:
**rarity was being read as significance.**

The corpus contains 44 typed notes across 4,425 marks — about 1%. That was treated as
evidence that typed notes are where the reader's most considered thinking lives. The simpler
explanation is **input friction**: typing on an e-reader is annoying. Rarity measures the
keyboard, not the thought. (Measured across the merged manifest: 69 of 88 books contain zero
typed notes at all.) Margin comments in books tend to be ephemeral rather than evergreen, and
a ranking built on their rarity over-weights in-the-moment reactions.

**Replacement signal: corroboration.** Did the mark change anything *outside* the book — does
it appear in a project, a decision, an artifact, a working document produced later? This is
observable rather than interpretive, which is the whole point: it can be checked by grep
rather than argued about.

**Measured outcome of applying it to 28 books:**

| Verdict | Count |
|---|---|
| Corroborated — a receipt exists outside the book | **4** |
| Partial | **11** |
| No receipt outside the book | **13** |

That distribution is itself the argument. If rarity had been tracking significance, far more
than 4 in 28 would show downstream effect.

**Binding rule that follows: every lesson carries a citation, and every lesson lands in
exactly one application** — something live now, something in the reader's own past evidenced
from a file the agent actually read, or a scenario explicitly labelled as hypothetical. None
of the three, not sent. A resurfacing agent that cannot cite its source and say where the
idea lands is a quote bot, and a quote bot trains its reader to skip the section it appears
in. The rule is stated in full, with the failure it exists to prevent, in
[AGENTS.md](AGENTS.md).

---

## 8. A measurement that failed, recorded as failed

The first attempt to compute corroboration mechanically **did not work, and its numbers are
void.** It matched single words from marked passages against the rest of the corpus. Common
abstract nouns — the exact vocabulary that appears in the kind of books being matched — put
the noise floor at **782 files**. Everything corroborated everything. No threshold rescues
that; the signal was never there.

A working version needs **distinctive multi-word phrases**: strings rare enough that a hit is
evidence of derivation rather than of shared vocabulary. Where that was done by hand it
separated cleanly — one book's marks turned up verbatim in a dated downstream artifact, while another
tier's distinctive phrases returned exactly two files corpus-wide, the source note and its own
summary. Nothing else. That is a clean negative, and it is only clean because the phrases were
distinctive.

This is the second instrument in this project that had to be discarded rather than tuned; the
first was the truncating review generator in section 2a. Both produced numbers that looked
like findings.

### The related trap: failures that return zero

Two scraper bugs in the ingest layer — the notebook-view crawler that ships as
`capture/kindle/notebook_crawl.py` in v0.3 — would each have shipped roughly a quarter of the
data as though it were all of it, and **both failed by returning zero**, which is
indistinguishable from "there is nothing more to fetch":

1. The pagination token lived on an element identified by class, not id. The id lookup
   returned null, the loop exited after page one, and every source capped at ~100 items.
2. Continuation responses came back as bare fragments with no wrapper element, so a
   structural child selector matched 98 rows on the first page and 0 on every page after it.

Nothing threw. Detection came from a smell: **six unrelated books all returning 92-97 results
is a cap, not natural variation.** After the fix, one of them went from 97 to 376.

**Rule: a scraper whose failure mode is an empty result needs an independent plausibility
check on its own output.** More generally, this project logged four separate instances of the
same defect class — absence of data being read as a finding — including a threshold tuned on
volume that silently dropped sources holding 20 of the 44 typed notes. Distinguishing "checked
and found nothing" from "never checked" is a schema decision, not a nicety; the pipeline now
carries an explicit `null` versus `[]` distinction for exactly this reason.

---

## 9. Decisions that held

Not everything reversed. These were set early, tested, and never revisited:

| Decision | Why it held |
|---|---|
| **Never write to the source store** | The migration is read-only at the origin. The original store stays intact as the fallback, which is what made every reversal above survivable. |
| **Purge means move, never delete** | thousands of attachment decisions cannot be hand-audited. Everything reclaimed went to a holding directory; reversing any of it is a `mv`. |
| **Fidelity before tidiness on the first pass** | A lossy export cannot be un-lost; a messy one can be cleaned later. |
| **Membership is decided in exactly one place** | An early rule based on folder location silently dropped the three largest sources in the corpus. Membership now lives in one module, `corpus/build_bookcorpus.py`: catalog evidence from three or more catalogued pages first, then a declared title, then the notes-folder rule (`RG_BOOK_FOLDER`) as the last fallback — evidence that something *is* a book outranks a guess from where its file sits. |
| **No volume floors on inclusion** | Every threshold set to reduce noise discarded signal instead, because the thresholds were tuned on volume while the target was corroboration, and the two are uncorrelated. The one floor left is a knob, not a default: `RG_MIN_PAGES` (default 1; the reference corpus used 3) on the photographed-pages channel. |
| **Repoint references before moving files** | The reference-resolution scheme resolves embeds by bare filename, so a move silently breaks every referrer. Deduplication rewrote 799 embeds across 156 notes *before* moving anything, then verified zero dangling references. Detection was easy; not breaking the vault was the work. |

---

## What a forker should take from this

1. **Measure the reclaim before you build the reclaim.** The purge phase was designed,
   specified, partly built, and calibrated before anyone divided 186 MB by 118 GB.
2. **Irreversibility raises the evidence bar, and it should.** The same numbers that make
   dedupe obviously correct make purge obviously wrong, purely because one is undoable.
3. **Run the adversarial pass even when you expect it to pass.** Its most valuable outcome
   here was 27 refutations that stand out of 28 candidates — and the one kill it later
   overturned, which is what exposed the stale-node failure.
4. **Instrument your instruments.** Two of the biggest corrections in this project were
   defects in measurement tools, not in the pipeline, and both produced confident numbers
   first.
5. **Prefer observable signals to interpretive ones.** "Is this mark rare?" is cheap and
   wrong. "Did this mark change anything outside its source?" is harder and checkable.
