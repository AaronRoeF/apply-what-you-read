# The Librarian and the Tutor

This pipeline is not the product. It is the substrate for two agents that were designed
before the corpus existed and then partly invalidated by it: a **Librarian** that finds and
records relationships in a reader's annotation corpus and writes them to Praxis, and a
**Tutor** that reads Praxis and delivers one lesson on a cadence. This document states the
design as it stands *after* the corrections, says which parts of the original are known
wrong, and shows the evidence for each change. Read it before you fork this repo to build the
same thing — the most useful content here is the part that says "don't."

**Status.** The Tutor has run in the author's instance for several weeks as of this release — three deliveries a
day through a local runner, with a ledger, a journal, and a weekly adjudication of outcomes —
and its public port (`agents/tutor/`) lands in v0.2: *Proven, landing*. The Librarian's
refutation protocol has run once, by hand, on the real corpus; its automated corroboration
matcher (`agents/librarian/candidates.py`) is *Designed*, for v0.3. The labels are the ones in
the status table in the README. The substrate both agents consume is complete and verified,
and every number below was measured on one real corpus (88 books, 4,425 highlights, 798
photographed pages).

---

## The two agents

| | Librarian | Tutor |
|---|---|---|
| Job | write typed, evidence-backed relationships into Praxis | read Praxis and deliver one lesson on a cadence |
| Input | merged corpus + the rest of the vault | Praxis |
| Output | Praxis, plus the reserved `related:` field on each node | one lesson into a channel the reader already opens |
| Failure mode | plausible-but-generic edges | becoming wallpaper — or a fabricated memory |
| Kill condition | edges that cannot cite text | seven consecutive delivered lessons silent on both passive channels |

---

# THE LIBRARIAN

## Pipeline

```
   notes ──▶ [1] EXTRACT ──────────▶ concept records (cached by content hash)
                                        │
                                        ▼
                              [2] CANDIDATE GEN   deterministic · no model · no API
                                        │  top-K per note
                                        ▼
                              [3] JUDGE           the only model step
                                        │  typed edge + quote + source path
                                        ▼
                              [4] REFUTE          adversarial · defaults to refuted
                                        │
                                        ▼
                              [5] WRITE           reserved field only, never bodies
```

In v0.3 the five steps map one-to-one onto `agents/librarian/`: `extract.py`, `candidates.py`,
`judge.md`, `refute.md`, `write.py`.

## The cost-control principle

**Search is deterministic; judgement is not. The model only ever judges a shortlist — it
never searches.**

This is the whole reason the design is affordable. The author's vault measured 5,012 markdown
files at the time of writing, of which 2,352 came from the notes-app import. That is roughly
12.5 million unordered pairs. No model considers that, and none should: nearest-neighbour
retrieval is a solved deterministic problem, and relationship typing is not.

Candidate generation uses local sentence embeddings plus signals already present for free —
shared tags, hand-authored wikilinks, shared book source — and hands the judge on the order
of ten candidates per note. Step [3] is the only line item that scales with model price.
Step [2] scales with CPU.

## Invariants

These are hard rails. An implementation that breaks any of them is a different system.

| Invariant | Why |
|---|---|
| **Never assert an edge without citable evidence** — a quote from each side plus both source paths | An edge that cannot point at text is deleted, not downgraded. This is the only rule that stops the graph filling with "both books mention leadership." |
| **Never write into note bodies** | The reader's own words are not editable by an agent. Blast radius is the entire justification for a recurring job over thousands of files. |
| **One reserved agent-owned frontmatter field** (`related:`) | Everything else in frontmatter belongs to the human. `vault/build_nodes.py` already enforces the mirror of this rule — it carries `related:`, `outcome:`, `applied_in:` and `status:` forward verbatim across every rebuild, with `related:` reserved for the Librarian, because a generator that clobbers hand-authored knowledge makes the graph unbuildable on top of its own output. |
| **OCR verdict gates trust** | Edges sourced from text the classifier scored `partial` or `mismatch` (about 30% of judged images) are marked low-confidence and never surface without a caveat. |
| **Idempotent and incremental** | Re-runs must not duplicate edges or re-pay for unchanged notes. Cache on content hash. |

There is a sharp trust line inside handwriting, and the graph must respect it. Stylus notes
taken on the device are stored as stroke data and recognised by the platform's own stroke
recogniser; 237 of 241 drawing
embeds in the imported corpus (239 files) already carry that text, and it is authoritative —
never overwrite it with pixel OCR. *Photographed* handwriting has no stroke data, and pixel
OCR on it fabricates proper nouns and numerals fluently and silently. Same hand, same page; one is a graph source
and the other is quarantined. The distinction is stroke data, not legibility, and it is
invisible unless you know to look.

## Node classes

The corpus is not one kind of material. It is three, and the interesting edges run *between*
classes rather than within them.

| Class | What it is | Measured |
|---|---|---|
| **Source material** | passages the reader marked — other people's ideas they judged worth keeping | 4,425 span-level highlights + 798 photographed pages across 88 merged book files |
| **Original thinking** | the reader's own notes — stroke-recognised handwriting, typed notes, journals | 239 drawing files, 237 of 241 embeds carrying stroke-recognised text; 44 typed notes inside the highlight corpus |
| **Working entities** | structured records the reader maintains: entity files and project state files | several hundred entity files; 138 project state files |

## Typed edges

**An untyped graph carries no information.** If every edge is "related", the structure is a
similarity index with extra steps: it can tell you two notes resemble each other, which you
could already get from the embedding, and it cannot tell you *how* — which is the only part
that changes what a reader does next. Type is what makes an edge a claim, and a claim is what
can be refuted in step [4]. An untyped edge cannot be attacked, so it cannot be verified, so
it cannot be trusted.

Within-class (source ↔ source):

| Edge | Meaning |
|---|---|
| `elaborates` | B develops an idea A introduces |
| `contradicts` | two sources the reader trusts disagree |
| `exemplifies` | B is a concrete case of A's abstraction |
| `same-concept` | independent sources converging on one idea |

Cross-class — these are the four that justify building anything at all:

| Edge | Spans | What it tells the reader |
|---|---|---|
| `origin` | thinking → source | the framework in their own notes is one they marked in a book months earlier |
| `converged` | thinking → source | they arrived at something independently that a book also says — confirmation, or a reinvented wheel |
| `applies-to` | source → entity | a marked passage bearing on a live account, person, or project |
| `unapplied` | source → ∅ | an idea they marked and never used anywhere |

`unapplied` is only computable because both classes are in the graph. Neither corpus alone can
tell you what someone learned and never spent.

---

## THE RE-SCOPE — Librarian v0 computes `unapplied` only

**Current recommendation: ship no cross-book edges at all in Librarian v0. Compute one thing —
passages the reader marked that left no receipt anywhere else in their corpus.** That is what
`agents/librarian/candidates.py` (v0.3, Designed) is specified to do.

This is a downgrade from the original design, and it is the correct one on evidence.

### Why: the headline output does not exist in the assumed quantity

The cross-book hypothesis was tested before any Librarian code was written. Twenty-eight
candidate edges across 25 unique book pairs were generated by four independent lenses and each
attacked by three adversarial verifiers working from the raw corpus JSON. **Twenty-seven
refutations stand. One kill was overturned on re-adjudication: two of the three
skeptics had read a stale derived node instead of the raw corpus, and every one of the eight
cited passages turned out to be verbatim in the raw data. That edge is a candidate again, not
a finding — overturning a kill does not make the edge true. Zero verified cross-book edges.**
The refutation machinery — typed edges, mandatory evidence, adversarial second opinion —
worked exactly as designed. The premise did not. Three failure modes recurred:

- **Manufactured gaps.** "Book A names the problem; only Book B supplies the drill." Almost
  always Book A supplied the drill too, a few pages away, in a passage the reader had already
  highlighted.
- **Colour-rarity inflation.** Treating a rare highlight colour as a significance signal. See
  the next section.
- **Genre truisms.** Two leadership books agreeing is a property of the shelf, not a discovery.

Four edges survived the pass, and all four are *intra-book*: a question the reader typed, and
the answer sitting in the same book in a passage they had already marked. The 27 refutations
are recorded in a do-not-re-derive appendix in the generated graph file, with the one
candidate-again pair and its carry-forward caveats, so a future run does not pay to
rediscover them. The overturned kill is its own lesson — verifiers read the raw corpus, never
a derived node — and is written up in [DECISIONS.md](DECISIONS.md) §6.

### Why `unapplied` specifically

**It is the one edge type untouched by every correction, because `unapplied` *is* the
corroboration test.** The replacement selection signal (below) asks whether a mark changed
anything outside the book. `unapplied` is that same question with the answer "no". Every
correction that invalidated another edge type either strengthened this one or left it alone.

**It requires an absence detector, not a connection discoverer.** That difference is the whole
argument:

| | Connection discoverer | Absence detector |
|---|---|---|
| Question | "does a relationship exist between A and B?" | "does this exact phrase appear anywhere else?" |
| Mechanism | embedding + model judgement | string search |
| Can hallucinate a relationship | yes | **no — there is nothing to hallucinate** |
| Cost | per-pair model call | one pass over the filesystem |

Measured on the author's vault: a full recursive `grep` for a distinctive multi-word phrase
across all 5,012 markdown files returns in under 0.2 seconds. Running it once per highlight is
minutes of CPU and zero API spend.

### The two things that make it work

**1. Phrases must be distinctive and multi-word.** A first attempt using single-word matching
is void and its numbers must not be reused — it put the noise floor at 782 files. Measured on
the same vault: the single common word `control` matches 1,046 of 5,012 files; the ordinary
three-word phrase `sense of control` matches 3. Distinctiveness is not a tuning parameter, it
is the difference between a signal and a coin flip.

**2. The detector must exclude its own output.** In one hand-run search, a candidate phrase
returned exactly two hits corpus-wide: the source note, and **the pipeline's own generated
distillation of that same note**. A receipt search that counts derived artifacts
self-corroborates every mark it examines. Exclude `<vault>/distill/`, `<vault>/books/`,
`<vault>/praxis/`, the attachment tree, and anything else the pipeline itself authored — then
verify the exclusion list by inspecting hits, not by trusting it.

A 28-book manual application of this test returned **4 corroborated, 11 partial, 13 with no
receipt anywhere else** — and the highest-corroboration book in the corpus is also one of the
lightest by annotation metrics: all-default-colour highlights, no typed notes, no photographed
pages. Annotation intensity and downstream impact were anti-correlated in that case, which is
the clearest possible argument against ranking on annotation density.

---

## Known wrong in the original design: the highlight-colour model

The original design ranked highlights by colour tier and weighted rare colours as high-signal.
**This is invalidated and any code written against it inherits the error.**

- **Colour clusters by reading session as often as by meaning** — a highlighter left on for a
  stretch of reading produces a run of one colour in one location range, which reads as a
  deliberate tier and is not.
- **In this corpus, pink is the reader's bullet-list and procedure marker, not an emphasis
  marker.** The tiering was inferred from a small photographed sample and did not survive
  contact with 4,423 span-level marks.
- **Colour also tracks the capture device.** Grey is an e-ink renderer's default, not a choice.
  Dark mode renders yellow as dark olive. Normalise by capture app before any numeric colour
  comparison.
- **Crowd-sourced "popular highlights" render in banding that resembles the reader's own
  highlight.** Unhandled, the graph attributes other readers' judgements to the reader — and
  popular highlights are by construction the most generic passages in a book. Detection rule:
  a highlighter-count label near the band means it is not the reader's mark.

`agents/distill/DISTILL_PROMPT.md` was rewritten against this finding. Its first ground rule
is *rarity is not significance*: non-default colours are treated as deliberate
differentiation, never as emphasis; colour rarity is never an argument; and a colour key the
reader declares in `<vault>/READER.md` outranks the prompt. If you are carrying an older copy
of that prompt that says "weight these heavily", treat its tiering as historical.

The distribution that survives is simply that yellow is the default and carries little signal
on its own: 3,993 yellow against 177 pink, 136 aqua, and 106 orange in the full crawl.

---

# THE TUTOR

## The design principle

**A resurfaced quote alone is a fortune cookie.** Showing someone an isolated passage they
once marked produces mild recognition and teaches nothing. The value is in the *connection* —
or in the *absence*. The quote is the delivery mechanism; the lesson is the payload: the
claim, its citation, enough of the author's argument to stand alone, and exactly one
application — intelligible to someone with nothing else loaded.

One lesson shape the re-scope makes cheap is the `unapplied` one: *you marked this, it has
never appeared anywhere else in your corpus, and here is where it could land.* It still needs
a citation and an application like every other lesson.

## Selection priority

1. **Receipt** — items with a demonstrable connection to a project, decision, or entity
   file, or a demonstrable absence of one.
2. **Live relevance** — material connected to what the reader is working on this week, read
   from their active project state files. This is the whole difference between a tutor and
   a quote bot.
3. **Hub position** — a marked passage connected to many others is load-bearing, not a stray.
4. **Time since last surfaced** — spaced, and never the same item twice inside a window.

Note what is *not* on this list and was on the original: highlight colour, and rarity of typed
notes. Both were demoted. Typed notes are about 1% of all marks (44 in 4,425) because typing
on an e-reader is annoying, not because those moments were profound. **Rarity is not
significance when rarity is explained by friction.**

## The binding rule

> **Every lesson carries a citation — book and location, or `file:line`. And every lesson
> lands in exactly one application: `current` (something live now), `past` (something in the
> reader's own past, evidenced from a file the agent read this run), or `hypothetical` (a
> scenario, explicitly labelled, opening with "Say…" or "Suppose…"). None of the three, not
> sent.**

This is a hard gate, not a ranking heuristic. A citation is always required; a receipt is not
— a lesson can be worth delivering before the idea has been used anywhere, which is the whole
point of `unapplied`. What the gate forbids is the fabricated memory: a hypothetical rendered
in the register of the reader's own history is the worst failure this system can produce,
worse than silence, because the reader cannot tell it from something they lived. Never stretch
to manufacture a `current`; a clean, labelled `hypothetical` beats a forced mapping.

The gate exists because the alternative is an agent that argues from absence, and this project
produced four separate instances of absence-of-data being read as a finding. It also cuts both
ways: for an `unapplied` item, the evidence the Tutor must show is the *verified emptiness* —
the phrase, the search, the exclusion list, and the zero. An `unapplied` claim with no
reproducible search behind it is exactly the failure the rule exists to prevent.

## Delivery

**Into a channel the reader already opens.** The tutorial's default is stdout; after that,
whatever channel you already open — a daily note, a phone message, email, a chat webhook
(`agents/tutor/run.sh` in v0.2 carries `stdout`, `email`, `imessage` and `slack`). The reason
is the same for every one of them: a channel that gets skimmed is a channel where this dies
quietly. Cadence is a knob, not a decision — the author's instance started at two deliveries a
day and moved to three. Keep each lesson small enough that reading it is never a decision.

Frame every item as *available*, never as a deficiency. Praxis carries this as a standing
instruction: each item is something the reader's own library already contains and has not yet
cashed. An agent that reports on what someone failed to do gets turned off, and it deserves
to be.

## Feedback and the kill condition

Outcomes are scored on two passive channels, and never by asking the reader to click:

- **`edit`** — a downstream edit citing the lesson within 14 days. Scored only on `current`
  rows: a `past` or `hypothetical` lesson can produce no downstream edit, so `edit` is `n/a`
  there and the second channel alone decides.
- **`opened`** — the cited note surfacing in the vault's recent files.

A row is *resolved* once its check-due date has passed and both channels are filled; a
resolved row with neither hit is `silent`. Downweight what stays silent.

**Explicit kill condition: seven consecutive resolved rows silent on both channels ⇒
`status: off` in the ledger frontmatter.** It is set loudly — the reason goes in the
frontmatter, the OFF line prints at the top of the weekly adjudication and every run after it
— and it stays off until the reader flips it back. A tutor nobody reads is worse than none,
because it trains the reader to skip that channel, and that channel is shared with things that
matter. Going dark silently is the failure this rule exists to prevent. This is stated as a
design commitment, not an aspiration; ship it with the metric wired up or do not ship it.

### The ledger

The ledger is the append-only table of delivered lessons and their outcomes, and the kill
switch lives in its frontmatter:

| date | item | citation | check-due | edit | opened | outcome | app_type |
|---|---|---|---|---|---|---|---|

`citation` is the source evidence — book and location, or `file:line`. `app_type` is the
application the lesson was sent with (`current`, `past` or `hypothetical`), and it is the
trailing column for a reason: the `edit` channel is scored only on `current` rows, and without
the column every `past` and `hypothetical` lesson would score silent on `edit` — the kill
condition would turn the loop off for working correctly.

---

# Status and open questions

The labels are the README's. The substrate both agents consume is complete, and every row
below was measured on one real corpus:

| Substrate | State |
|---|---|
| Imported note corpus | 2,352 files, verified, 0 broken embeds |
| Merged book corpus | 88 book files, 4,425 highlights, 44 typed notes |
| Vault book nodes | 88, 1:1 with the corpus, zero orphans either direction |
| Reserved `related:` field | present on every node, preserved across rebuilds, empty until the Librarian lands (v0.3) |
| Distillations | every book distilled (88 of 88); 28 carry a hand-run corroboration verdict |
| Praxis, the applied index | 27 adjudicated idea→use rows across 16 books; zero verified cross-book edges (27–1); 4 intra-book edges; a do-not-re-derive appendix of 27 refutations plus one candidate-again pair |
| Tutor | running in the author's instance for several weeks as of this release with ledger, journal and weekly adjudication; public port in v0.2 |

## Design questions, and where they landed

1. **Where do edges live — reserved frontmatter, or a separate graph layer?** Frontmatter makes
   edges visible in the vault's own graph view and backlinks with no new tooling. A separate
   layer keeps agent output entirely out of the reader's files. This trades native tooling
   against blast radius, and on thousands of files it is close to a one-way door. **Answered in
   practice: both.** A separate Praxis store (`<vault>/praxis/`) holds the lessons and the
   relationships; the nodes carry only the reserved `related:` field, which the Librarian writes
   and `vault/build_nodes.py` preserves. Agent output stays out of the reader's files except
   for that one field.
2. **Cadence: one item a day, or three a week?** Daily builds a habit and risks becoming
   wallpaper; weekly is easier to keep high-quality. **It is a knob, not a decision** — see
   *Delivery*. The author's instance started at two deliveries a day and moved to three; the
   kill condition, not the cadence, is what protects against wallpaper.
3. **What counts as corroboration?** The 28-book corroboration pass was run by agents applying
   judgement, not by a shipped matcher. The distinctive-phrase extractor, the exclusion list,
   the noise floor, and the threshold for "partial" are the specification of
   `agents/librarian/candidates.py` (v0.3) and remain its first build task. **Still open —
   Designed.**

## One substrate caveat found while writing this document — since fixed

`corpus/merge_corpus.py` derived output filenames from a slug of the book title truncated at
the first colon, and two distinct works in this corpus — a book and a third-party summary of
it — slugged identically. The manifest held 88 rows against 87 files on disk: one record
overwrote the other, and its 2 highlights were the exact difference between the 4,425 crawled
and the 4,423 then present. Harmless at this magnitude, and the same class of defect as the
four silent drops documented in [PITFALLS.md](PITFALLS.md) — a threshold or a key collision
that discards data while reporting success. It is fixed: a `disambiguate()` step now pays for
the subtitle only when a collision occurs, and falls back to the source identifier when the
subtitle does not separate the two works. If you fork this and change the keying, key on the
source identifier, not the title.
