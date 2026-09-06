# Verifying agent output you cannot read yourself

This pipeline, run against one real corpus — 88 books, 4,425 e-reader highlights, 798
photographed pages — machine-read roughly 3,400 images and 143 documents, then had agents
write dozens of analyses on top of that text. Nobody read the inputs. Nobody read most of the
outputs. This document is the methodology for trusting any of it anyway: what to measure,
what a single measurement cannot tell you, how to calibrate a threshold against a human,
and how to attack an agent's claims hard enough that the survivors mean something. The
short version is at the top of each section; the evidence is underneath it.

---

## The three regimes

Verification problems in a pipeline like this are not one problem. They are three, and
they need different machinery.

| Regime | Question | Method | Cost |
|---|---|---|---|
| **Mechanical** | Did everything arrive, exactly once, pointing at something real? | Count reconciliation, ID uniqueness, reference resolution | Free, deterministic, run every time |
| **Statistical** | Is this extraction good enough to act on? | Multiple independent signals, thresholds calibrated against a hand-scored sample | Cheap signals, expensive calibration |
| **Adversarial** | Is this agent-written claim true? | N independent skeptics per claim, each prompted to refute, each with a distinct lens | Expensive; reserve for claims that will be acted on |

The failure mode is using the wrong one. Counting cannot tell you whether OCR is
correct. A confidence score cannot tell you whether an agent's inference is sound. And no
amount of statistics will catch a claim built on evidence that does not exist — only a
reader who goes and looks will.

---

## 1. OCR verification: four signals, none of them sufficient

**Start by refusing the impossible question.** You cannot confirm per-image OCR
correctness without ground truth, and building ground truth for 3,400 images is the same
labour as not using OCR at all. Ask the tractable question instead — *is this extraction
trustworthy enough that destroying the source image would be safe?* Below the bar, keep
the image and nothing is lost. That reframing is what makes the whole gate designable.
It is the opening comment of `capture/pages/verify.py`.

### The four signals

| Signal | What it detects | How it lies |
|---|---|---|
| `engine_conf` — Apple Vision's own mean confidence | Illegible glyphs | High on perfectly-read text whose *meaning* was destroyed. Tracks legibility, not information retention. |
| `word_validity` — share of alphabetic tokens in a system dictionary | Character soup from a failed extraction | Punishes proper nouns, jargon, and abbreviations, which are absent from `/usr/share/dict/words` |
| `density` — characters recovered per megapixel | A full page yielding twelve characters | Meaningless on images that legitimately contain little text |
| `agreement` — similarity between Vision's text and an independent second extractor | Everything the others miss, because two engines converging is real evidence | Absent until the second engine has run; a "cleaned up" second transcription destroys it |

Each catches a failure class the others are blind to. `verify.py` deliberately keeps them
as four numbers and only collapses them at the gate — as a conjunction, not a weighted
sum, so a single strong signal cannot outvote a weak one:

```python
out["purge_eligible"] = bool(
    out["ok"]
    and out["chars"] >= 40
    and out["engine_conf"] >= 0.80
    and (out["word_validity"] is None or out["word_validity"] >= 0.70)
    and out["agreement"] is not None
    and out["agreement"] >= 0.75
    and not {"ocr_failed", "low_engine_conf", "low_word_validity"} & set(f)
)
```

Note `agreement is not None`. **An image with no second opinion is never eligible** — the
gate fails closed. Running the scorer before the second engine exists yields zero
eligible images out of 604 scored, which is the correct answer, not a bug.

### The conditional-validity finding

Engine confidence was called unreliable, then called a good filter, and both claims were
wrong in the same way. The resolution, in the words of one of the judging agents:

> Engine confidence tracks glyph legibility, not information retention.

The measurements, over 144 judged images:

| Band | Outcome |
|---|---|
| `engine_conf ≥ 0.98` | 98 matches · 10 partial · 1 mismatch |
| `engine_conf < 0.90` | 1 match · 14 partial · 7 mismatch |

That looks like a strong filter, and on this corpus it is — **because most of the corpus
is flat prose.** Inside grids it inverts. A spreadsheet screenshot at confidence 0.85 lost
roughly 400 cells to arbitrary reading order. A comparison table at confidence **1.00**
destroyed every row-to-column binding while transcribing every token perfectly. The
engine was right about the glyphs and the extraction was worthless.

> **Rule: engine confidence is a valid signal only on flat prose. "Contains a grid" is an
> override, never a score input.**

This generalises past OCR. Any confidence score reports the model's certainty about the
sub-task it was optimised for, which is rarely the task you care about. Find the structural
condition under which the score stops meaning what you think, and make that condition a
veto rather than a term.

### Do not let junk poison the calibration corpus

Of 3,372 images, 198 returned no Vision result at all. Effectively all were sub-64px email
tracking pixels and spacer GIFs from forwarded mail — Vision rejects them as "too small."
Labelling those `ocr_failed` would have put a few hundred phantom failures into the
calibration set and hidden any real engine fault behind them, so `verify.py` splits them
out as `junk_pixel`:

```python
err = (rec.get("error") or "").lower()
tiny = rec.get("bytes", 0) and rec["bytes"] < 2048
f.append("junk_pixel" if ("too small" in err or tiny) else "ocr_failed")
```

The same discipline applies to the 630 images that ran fine and returned zero characters.
That is not a failure; it is a photograph of a person or a place. It is flagged `no_text`
and auto-kept, and it never reaches a model.

Measured distribution over the full pass: 3,372 images, 2,544 with recognised text,
828 with none (630 empty + 198 rejected). `engine_conf` median 1.00, p10 0.88.
`word_validity` median 0.78 — low, and low for a benign reason, which is exactly why the
threshold had to be calibrated rather than picked.

---

## 2. Import verification: reconcile to an exact number, or you have not reconciled

**"Close enough" is where silent data loss hides.** The rule is that every unit of
discrepancy gets an explanation naming a specific mechanism, and the arithmetic has to
close.

The notes-app import behind the reference corpus claimed 2,434 notes. The vault had 2,352.
Chasing the 82:

| Step | Count | Explanation |
|---|---|---|
| Source claim | 2,434 | AppleScript `count of notes` |
| − smart folders | −58 | Five saved-search folders count notes that live elsewhere. Correctly not duplicated. |
| − shared folders owned by others | −23 | Two shared folders whose content is not materialised locally |
| **Expected** | **2,353** | |
| **Actual** | **2,352** | Reconciles to within 1 |

The 58 is the load-bearing number. Without it the gap looks like 3.4% data loss; with it
the gap is a rounding error and one deliberate exclusion. The only way to get it is to
enumerate the source's folders and understand what its own count function counts.

The same discipline applied to attachments dissolved a scarier-looking discrepancy. The
source claimed 6,294 attachments; 3,545 files landed. The baseline was wrong, not the
import: **19 notes accounted for 2,852 of the claimed attachments** — logos, tracking
pixels and spacer GIFs inside forwarded email, which explains the 332 `.gif` files. One
forwarded hotel confirmation was credited with 740 attachments and produced 116 embeds,
with its 25.6k-character body intact.

### Reference integrity is the second half

Counts prove arrival. They do not prove the corpus points at anything. `reference/triage.py`
(ran once on the reference corpus; not on the quickstart path — `capture/pages/manifest.py`
is its generic successor) emitted these on every run:

| Check | Result | Why it matters |
|---|---|---|
| Unique source IDs | 2,346 unique, **0 duplicates** | A duplicate ID means one note silently overwrote another |
| Notes with no ID | 6 | Known and enumerated, not "a few" |
| Broken embeds | **0 of 3,512 references** | Obsidian resolves embeds by bare filename; a moved file breaks silently |
| Orphan attachment files | 35 | Files nothing references — the inverse leak |
| Duplicate titles | 45, all in different folders | Expected; would be a collision risk in a flat namespace |

Deduplication (`reference/dedupe.py`, likewise off the quickstart path) is where reference
integrity earns its keep. Collapsing 355 byte-identical
groups (821 redundant files) required **799 embed rewrites across 156 notes**, performed
*before* any file moved, then re-verified: 0 broken embeds, note count unchanged, and
`embed_refs` unchanged at 3,512 — the same references resolving to fewer files. The
detection was trivial; the link integrity was the entire job.

And a correction that survived into the record: 821 files is 23% of the corpus by count
but only ~8% by bytes. **Report the metric that matches the decision.** A count-based
claim about a space saving is a different claim than it appears to be.

### Recount rather than trusting a recorded number — and reconcile the manifest to the files

When this document was first written, the corpus of record held 87 merged book files
carrying 4,423 of the 4,425 crawled highlights, while recomputing from
`out/merged/_manifest.json` gave **88 rows, 4,425 highlights, 798 photographed pages, 44
typed notes.**

The two-highlight and one-book gaps were the same defect: two distinct works normalised to
the same output slug, so the second write overwrote the first. The manifest had 88 rows
against **87 unique slugs and 87 files on disk**, and it therefore overstated the corpus by
one book and two highlights. The recount is what found it. `corpus/merge_corpus.py` now
runs a `disambiguate()` step that gives every row a unique slug, keeping the subtitle only
where it is needed, and the manifest, the slug set and the directory agree.

The point generalises past this bug. A count recorded in prose has no timestamp and no
provenance; a count recomputed from the artifact has both. Recompute — and then reconcile
the recomputed number against the files it claims to describe, because a manifest that
disagrees with its own directory is the cheapest possible detection of a key collision.

---

## 3. Human calibration — and verifying the harness before the humans

**Every threshold in the scorer is a guess until it is measured against a person looking
at images.** `reference/review_sample.py` (ran once on the reference corpus; not on the
quickstart path) builds that review set as a note: image embedded, the OCR
text, the classifier's verdict, and what the pipeline would do.

### Two samples, two different questions

- A **stratified random** sample measures the error *rate*. It is representative, so its
  arithmetic means something.
- A **worst-N** sample finds failure *modes* — the systematic break affecting 3% of images
  that a 50-item random sample will never contain. It is not representative and **its
  arithmetic means nothing.**

Reporting worst-N results as a rate is the classic error, which is why the generator
labels the two surfaces separately and the reviewer scores them separately.

### The round that a display bug invalidated

A calibration round was run and scored:

| Sample | Agreement |
|---|---|
| Stratified random (representative) | 24/26 = 92% |
| Worst-N (not representative) | 10/10 = 100% |
| Purge precision on the representative sample | 3/5 = 60% |

That 60% was the number the review existed to produce, and it was published as the reason
the threshold was too loose. Then the reviewer noticed that the review file was showing
only part of each page's text. It was: the generator truncated OCR at 700 characters under
the heading **"What the OCR actually read."** On one page the header stated 3,429
characters and the body showed about 700, ending in an ellipsis.

**The label was the failure, not the truncation.** "First 700 of 3,429" would have been
fine. Asserting completeness while showing a fifth of the content means a reviewer told
"this is what the OCR read," seeing text that stops mid-page, correctly says *keep* — and
the resulting disagreement measured the harness, not the pipeline.

What survived the retraction, stated honestly:

| Claim | Status after the bug was found |
|---|---|
| Both disputed images are heavily annotated | **Survives** — verified visually, independent of the display |
| "The annotation veto explains both failures" | **Retracted.** Plausible, not established. |
| Purge precision = 60% | **Retracted.** May measure the artifact's defect. Must not set a threshold. |
| Errors run one direction only (never "you should have purged that") | **Probably survives**, but scored against the same broken artifact — indicative, not measured |

> **A review artifact that misrepresents the thing under review is worse than no review,
> because it produces confident numbers that measure the tool instead of the system.**

Verify the verification harness first, and specifically verify that **every field it
renders means what its label says.** The fixed generator emits the full text inside a
collapsed callout (length is free), labels it `Full OCR output — all N characters`, and
where a 20,000-character display cap does bite, says so explicitly: *"This is a display
limit, NOT an OCR failure."*

The same fix has a second half — **render three states, never two.** Images scored before
the `annotations` field existed carry `null`, and showing `null` as "none detected" would
hide precisely the gap that invalidated the first round:

```python
if ann is None:
    ann_line = "Annotation: NOT ASSESSED — scored before this field existed. Check the image yourself."
elif ann:
    ann_line = "Annotation: YES — highlighting / marks present. This VETOES any purge."
else:
    ann_line = "Annotation: none detected"
```

### What the corrected round then showed

Re-running the same 70 images under the corrected rubric moved would-purge from **34 to
5** — an 85% reduction. Across all 142 judged images: 83 annotated (58%), 18 purge-eligible
(13%), 66 MB reclaimable of 731 MB judged (9%). The verification did not tune the feature;
it killed it. The destructive step was abandoned, because the value had never been the disk
space — it was the extracted text, and that survives whether or not the image does.

---

## 4. Adversarial verification: the core technique for agent-written claims

**An agent asked to find relationships will find them.** Plausibility is what a language
model optimises; it is not evidence. The only method that has held up here is to make
refutation someone else's job and give them a quota of nothing.

### The protocol

1. **Generate** candidates from several independent lenses, so the failure modes of one
   generator do not dominate the pool.
2. **Require citations at generation time.** Every claim carries a verbatim quote plus a
   file path and location on each side. A claim that cannot cite is discarded, not
   downgraded.
3. **Spawn N independent skeptics per claim**, each prompted to *refute*, each blind to the
   others, each working from **the primary source files**, not from the claim's own summary.
4. **Give each skeptic a distinct failure lens.** Overlapping skeptics agree cheaply.
   The three that worked:
   - *Does the cited evidence exist and say what the claim says it says?* — quote drift,
     truncation that reverses meaning, fabricated citations.
   - *Is the claim non-trivial?* — genre truisms, restatements, claims that would be true
     of any two items on the shelf.
   - *Is the relation correctly characterised?* — right sources, wrong verb. Equivocation
     on a shared word is the dominant case.
5. **Majority refutation kills the claim.** Default to refuted when uncertain.

### The result

Twenty-eight candidate cross-book edges were generated by four independent lenses, across
25 unique book pairs, and each was attacked by three adversarial verifiers. **Twenty-seven
refutations stand.** One kill was overturned on re-adjudication: two of the three skeptics
had read a stale derived node instead of the raw corpus, and every one of the eight cited
passages turned out to be verbatim in the raw data. That edge is a candidate again, not a
finding — overturning a kill does not make the edge true. **Zero verified cross-book
edges.**

The named failure modes, all of which recur:

- **Manufactured gaps** — by far the most common. "Source A names the problem; only source
  B supplies the drill." Almost always A supplied the drill too, a few pages away, in a
  passage already marked.
- **Rarity inflation** — a rare attribute treated as a significance signal when it is
  explained by mechanism. Non-yellow highlight colours cluster by *reading session*, not by
  meaning, and one colour turned out to be the reader's bullet-list marker.
- **Genre truisms** — two leadership books agreeing is a property of the shelf.

**Report the real yield.** The machinery worked exactly as designed; the premise it was
testing did not survive. That is a successful verification run, and writing it up as
"zero verified edges" rather than quietly shipping the 28 is the point. The twenty-seven
standing refutations are recorded in a **do-not-re-derive appendix** with the killing
argument for each pair, so the next run does not rediscover them at full cost; the
overturned edge goes back into the candidate pool, not into the appendix.

### Refuters need current inputs too

This is the kill that was overturned. Two of the three skeptics on that edge read a derived
book node that still carried photo-only statistics (`highlight_colors: [grey:2]`) instead of
the raw corpus, concluded the book "has no e-reader highlight layer," and used that to kill
the edge. The book has **107 e-reader highlights**, and on re-adjudication every one of the
eight passages the claim cited was verbatim in the raw data. The node was stale, not
wrong-by-design; it had been generated before the highlight join and never rebuilt.
Overturning the kill returns the edge to the candidate pool — it does not make the edge
true. What the episode does establish is a protocol rule: **skeptics read primary sources,
never derived nodes.**

> **A stale or incomplete derived artifact is not inert. It actively corrupts every agent
> downstream that trusts it — including your verifiers.**

Practical consequences:

- Point verifiers at **primary sources**, never at derived nodes, summaries, or the
  generator's own output.
- Rebuild derived artifacts in dependency order before a verification run, and delete
  stale outputs rather than leaving them (`corpus/build_bookcorpus.py` unlinks the previous
  `bookcorpus/*.json` because "stale files from an older membership rule are worse than
  absent ones").
- Treat a refutation as a claim too. It gets the same "does the cited evidence exist" test.

### Convergence is evidence; count it

Three skeptics, blind to each other, attacking three *different* claims, all killed their
targets by pointing at the **same passage** in the same book. They were not coordinating
and were not trying to agree. Independent convergence without coordination is the strongest
positive signal this exercise produced, and it is worth reporting explicitly when it
happens — it upgraded that passage from "one refuter's argument" to the highest-confidence
finding in the graph.

---

## 5. Dispatcher discipline: set the posture before the agent runs, not after

Correcting an analysis after it is written is more expensive than constraining it before,
because by then its prose has been copied into three other documents. Prepend this to
**every** analysis or research agent prompt, verbatim:

> Every claim you produce is inference until it is verified against a primary source. Cite
> sources inline — file path, location, and a verbatim quote. If you cannot cite a primary
> source for a claim, mark it `[INFERENCE]` and state what would verify it.

Three supporting rules, each of which came from a real failure:

- **Judge; do not transcribe.** Asking an agent to emit long verbatim transcriptions of
  personal documents trips output content filtering and kills the whole batch — five
  dispatched agents, five deaths, 14 of 150 images salvaged. Reframing the task to *judge
  Apple Vision's text against the image* cut output from ~300 tokens per image to ~30,
  removed the filter risk entirely, and produced a **stronger** agreement signal: a direct
  verdict on whether the OCR matches beats a string-distance comparison of two
  transcriptions.
- **Tag what you could not assess.** Prompts must specify the value for "I could not read
  this" (`"annotations": null`) and require partial output to be appended per item, so a
  death costs one record rather than a batch.
- **Hedge on sample size in the output, not in the reader's head.** The distillation prompt
  (`agents/distill/DISTILL_PROMPT.md`) requires each analysis to state how many source pages
  it had and that absence of a source
  page is not absence of engagement. Agents comply with this when told; they do not
  volunteer it.

And a bug worth expecting: an agent flagged that the text it was shown (~1,200 chars) did
not match the character count in its own input record (2,820). The batch builder was
truncating, so agents were judging a truncated excerpt against a full page and reading the
missing text as OCR failure — inflating `partial` verdicts across every batch. **Agents
catch harness bugs when the input carries enough metadata for them to notice the
inconsistency.** Ship the counts alongside the content.

---

## 6. The anti-pattern to name: never infer a gap from missing data

This is the single most productive error class in the whole project — four separate
instances, three of which shipped as findings before being caught.

| # | Instance | What went wrong |
|---|---|---|
| 1 | `marks: []` vs `null` | "Catalogued and nothing found" was collapsed with "never assessed." An agent read the empty list as a broken extractor and reported a bug that did not exist. |
| 2 | Photo-only sampling | A distillation asserted the reader had never engaged with a particular chapter of Book A. The e-reader layer holds **22 marks** on it. Photographs are a biased sample of what was marked; the ratio for that book was 53 photographed pages against 167 real highlights, and for Book B 19 against 107. |
| 3 | Stale derived node | A verifier read photo-only statistics on a rebuilt-too-late node and concluded a book had no highlight layer. It has 107. The kill was overturned on re-adjudication (§4); the edge is a candidate again, not a finding. |
| 4 | Volume thresholds | `corpus/merge_corpus.py` dropped books below a highlight floor. `n >= 25` discarded 44 books holding 214 highlights and **20 of the corpus's 44 typed notes**; a later `kindle < 10 AND photos < 5` rule dropped books with real content in both channels and orphaned their nodes. The one floor that remains, `RG_MIN_PAGES` (default 1; the reference corpus used 3), is on photographed pages in `corpus/build_bookcorpus.py`, not on highlight volume. |

Instance 4 is the general form of all of them: **a threshold tuned on volume discards the
highest-value signal whenever value and volume are uncorrelated.** The typed notes were the
rarest and most valuable field in the corpus, and they lived disproportionately in
low-volume books.

The rule, now stamped into every merged book file `corpus/merge_corpus.py` emits (as the
per-page absence disclaimer) and into `agents/distill/DISTILL_PROMPT.md` as rule 3, so every
downstream reader sees it:

> **Never infer a gap from missing data. Only claim an absence with positive coverage of
> the surrounding material in every available channel.**

Concretely, before writing "X is not present":

1. Enumerate the channels where X could be recorded. Absence in one is not absence.
2. Show a positive query result over the surrounding material in **each** channel —
   "I searched all 460 highlights in this book for *cycle time / simultaneous / concurrent /
   capacity*: zero hits" is a claim; "I did not see it" is not.
3. Distinguish *assessed-and-empty* from *never-assessed* in the data model, not in prose.
   Two states in the schema, three states in the renderer.
4. Say what would change the answer.

### The corollary: a failure that returns zero is invisible

The highlight crawler had two bugs that both failed by returning **zero rows**, which is
indistinguishable from "this book has no more highlights." One looked up a pagination token
by id when it lived on a class; the other used a structural child selector that matched on
the first page and never again on the bare continuation fragments. Nothing threw. Every
book capped at roughly 100 highlights, and about 25% of the data would have shipped as if
it were 100%.

Detection came from a smell, not an error: **six unrelated books all landing in a 92–97
band is a cap, not natural variation.** One book went from 97 to 376 once the pagination
was fixed. The total went to 4,425.

> Any extractor whose failure mode is an empty result needs an independent plausibility
> check on its own output distribution. Look for suspiciously tight bands, round numbers,
> and identical counts across unrelated inputs.

The reference crawler ships in v0.3 (Designed); provider selectors drift, and the
plausibility check — `capture/kindle/plausibility.py`, the sorted per-book count vector —
is the part to keep.

A related discipline: when a measurement is attempted and fails, void it loudly rather than
letting the numbers circulate. A first attempt at finding receipts — places outside the book
where a marked passage was used — matched single words and put the noise floor at 782 files (on words like "cause,"
"control," "different"). Its output is unusable and is recorded as void, with the fix named
— distinctive multi-word phrases.

---

## 7. Checklist

Before trusting a machine-read corpus:

- [ ] Counts reconcile to an exact number, with every unit of discrepancy explained by a
      named mechanism
- [ ] Every reference resolves; IDs are unique; orphans are enumerated, not estimated
- [ ] Extraction quality measured by ≥3 independent signals, combined as a conjunction
- [ ] The structural condition under which each signal inverts is identified and made a veto
- [ ] Junk inputs classified as junk, not as failures, before any calibration
- [ ] Destructive gates fail closed when a signal is unavailable

Before trusting a human calibration:

- [ ] The review harness has been checked field-by-field against the underlying data
- [ ] Every label is literally true; nothing asserts completeness it does not have
- [ ] Unassessed renders differently from assessed-and-negative
- [ ] Representative and non-representative samples are reported separately, and only the
      representative one gets arithmetic

Before trusting an agent's claim:

- [ ] Inline citation with path, location, and verbatim quote
- [ ] ≥3 independent skeptics, prompted to refute, with distinct lenses
- [ ] Skeptics read primary sources, never derived artifacts or the claim's own summary
- [ ] Derived inputs rebuilt in dependency order; stale outputs deleted, not left
- [ ] The refutation itself checked for the same defects as the claim
- [ ] Absence claims backed by positive coverage in every channel
- [ ] The real yield reported, including when the yield is zero

---

## Related

- [`CLASSIFY-PATHS.md`](CLASSIFY-PATHS.md) — the two classifier paths, the output contract,
  and why the second-opinion transcription must be verbatim for the agreement signal to
  mean anything.
- `capture/pages/verify.py` — the four-signal scorer and the purge gate.
- `reference/review_sample.py` — the human calibration generator (ran once on the reference
  corpus).
- `reference/triage.py` — the manifest and reference-integrity checks (ran once on the
  reference corpus; `capture/pages/manifest.py` is the generic successor).
