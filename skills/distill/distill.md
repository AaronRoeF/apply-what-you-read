---
name: distill
description: >
  Use this skill when the reader wants a book reduced to the part that actually
  matters — the vital ~20% they can scan and apply — not a chapter-by-chapter
  summary. Triggers: "distill [book]", "distill this book", "distill [title]",
  "read [book] the fast way", "give me the 20% of [book]", "the gist of [book]",
  "what's [book] actually about", "TL;DR [book]". Applies Thomas Dev Brown's
  "How To Read A Book A Day" method: find the key elements, take the 20% that
  carries the book, restate it in plain English, then produce a teach-back and
  an apply layer. File-first — if the reader supplies a PDF/EPUB/Kindle-highlights
  export or a book node from this pipeline, distill the real text; otherwise
  research public sources and TAG the fidelity. Output is inline by default;
  save to the vault only on "save it". Do NOT use for explaining a single
  concept in depth, for ghost-writing in the reader's voice, or when the reader
  genuinely wants an exhaustive close reading — distill is the 20%, by design.
---

<!--
SKILL SUMMARY: distill
=========================
Reduce a book to its applyable 20% using Thomas Dev Brown's "read a book a day"
method. Understand it, then be able to use it — without reading every word.

WHAT IT DOES:
  Runs five moves on a book:
    Frame     get the best available source; tag fidelity (text vs public)
    Skeleton  find the key elements — thesis, structure, intro/conclusion
    The 20%   extract the vital fifth that carries the book; cut the filler
    Plain     restate each core idea jargon-free (comprehension, not transcription)
    Teach+Apply  a teach-back test + concrete "use it now" actions

WHEN TO USE:
  - "distill [book]" / "the gist of [book]" / "give me the 20% of [book]"
  - The reader wants to absorb a book fast and actually apply it
  - The reader points at a book node in the vault, or drops a file, and wants the essence

WHEN NOT TO USE:
  - Explaining ONE concept in depth (a teaching skill's job, not a distillation)
  - Writing prose in the reader's voice
  - A genuine exhaustive close reading — distill is deliberately the 20%

OUTPUT:
  Inline markdown by default. "save it" → $VAULT/distill/distill-<slug>.md, which
  vault/build_nodes.py transcludes into the book's node on the next rebuild.

KEY IDEA:
  The method's whole claim: you don't need to read faster, you need to read
  smarter. Master the 20% that carries the book, prove you own it by teaching
  it back, then apply it. Fidelity honesty is non-negotiable — never pass
  public-source inference off as if it came from the text.
-->

# distill — A Book, Reduced to the Part You'll Use

**WHY:** Most book summaries recreate the table of contents — a dutiful walk through every chapter that leaves you with notes you'll never reopen. Thomas Dev Brown's *How To Read A Book A Day* rejects that: a book's argument rides on a vital ~20%, and the rest is illustration, repetition, and padding. Take the 20%, understand it well enough to teach it, and apply it — and you've extracted the book's actual value in an hour. `distill` is that method, run for you.

**WHO:** The reader — someone who reads to *use*, not to finish, and whose context lives in `$READER_CONTEXT` when it is set. Don't pad, don't recap for its own sake, and don't bury the payload. The apply layer is the point; everything above it earns it.

**HOW:** Five moves, in order. The order matters: you find the skeleton before you cut, you cut before you simplify, and you only ask "how do I use this" once you actually understand it.

---

## The five moves

| | Move | What it does |
|---|------|--------------|
| **1** | **Frame** | Get the best available source and **tag the fidelity**. File-first. |
| **2** | **Skeleton** | Find the key elements *instantly* — thesis, structure, intro, conclusion. Surface the author's *intended* takeaways, not a reader's tangents. |
| **3** | **The 20%** | Extract the vital fifth: the handful of ideas the book's argument stands on. Cut ruthlessly. |
| **4** | **Plain** | Restate each core idea in jargon-free words. This is the retention move — comprehension, not transcription. |
| **5** | **Teach + Apply** | A teach-back (explain-to-a-friend + a self-test) and a concrete apply layer. Wisdom is knowledge *applied*. |

---

## How to run it

### 1 — Frame (get the source, tag the fidelity)

**File-first, always.** If the reader has given you — in this conversation or on disk — a PDF, EPUB, `.txt`, a Kindle-highlights export, or a book node from this pipeline (`$VAULT/books/<slug>.md`, whose merged corpus record sits at `$RG_OUT/merged/<slug>.json`), distill *that*. The real text is the only path to the real 20%; the reader's own highlights are the judgment layer to weave in.

If there's no file, research public sources: the publisher's description, the table of contents, the author's own interviews and talks, reputable summaries used only as leads, and widely-quoted passages. Corroborate across sources; one blog's claim about a book is a lead, not a fact.

**Then tag the fidelity on the very first line of output**, non-negotiable:
- `[from the full text]` — you distilled a provided file.
- `[from public sources]` — you distilled description/TOC/reviews/summaries.
- `[from partial text: <what>]` — e.g. highlights only, or first three chapters.

This tag is a promise about how much to trust the distillation. It exists because the failure mode here is quietly presenting inference as if you'd read the book. See **Fidelity discipline** below — it's the load-bearing rule of this skill.

### 2 — Skeleton (find the key elements instantly)

Before cutting anything, map the shape:
- **The thesis** — the one claim the whole book is arguing for. If you can't state it in a sentence, keep reading the structure until you can.
- **The structure** — the parts/sections and what each is *for* (not what it's titled — what job it does in the argument).
- **Intro and conclusion** — where non-fiction authors state their intended takeaways most plainly. Weight these.

The output of this move is internal — it's how you earn the 20%. Don't dump the skeleton on the reader unless they ask; it becomes the "Key elements" line, distilled.

### 3 — The 20% (take the vital fifth)

Extract the **3–6 core ideas** the book actually turns on. The discipline is subtraction:
- **The drop test:** remove an idea. If the book's argument still stands, it wasn't in the 20% — it was illustration. Cut it.
- Collapse repeated points into one. Authors restate; you don't.
- Anecdotes, case studies, and worked examples are *evidence for* the ideas, not ideas. Name the idea; drop the anecdote (or keep one as a hook if it's the fastest way to make the idea land).
- If you find yourself listing 12 "key" ideas, you haven't distilled — you've re-outlined. Force it back to 6 or fewer.

### 4 — Plain (say each idea without the jargon)

Restate every core idea in the words you'd use at dinner. This is Brown's comprehension move: if you can only reproduce the author's phrasing, you've memorized, not learned. Strip the branded vocabulary (every business book coins terms) down to what it actually means. Keep one coined term only if it's genuinely the handle worth remembering — and define it in plain words when you do.

### 5 — Teach + Apply (prove it, then use it)

Two products, both concrete:

- **Teach-back.** A 2–3 sentence "explain it to a smart friend" version of the whole book — the test Brown sets: *if you can't teach it in your own words, you didn't learn it.* Then **one self-test question** the reader could only answer if they actually understood the argument (not a trivia question about a chapter title).
- **Apply now.** 3–5 concrete actions specific to *this* book — things the reader could do this week. "Reflect on the ideas" is not an action. "Before your next decision, write the one-line version of what you're actually optimizing for" is. The apply layer is why this skill exists; make it the sharpest part. Where the reader's own highlights exist, tie an action to one of them.

Then stop. Optionally one line on who should read the whole book anyway (the 20% isn't always enough — say so when it isn't).

---

## Output template (inline default)

```
# <Book Title> — <Author>
*[from the full text]  |  [from public sources]  |  [from partial text: …]*

**The 20% — what carries the book**
1. <core idea, one line>
2. …            (3–6 total, no more)

**In plain English**
<the whole book in 2–3 jargon-free sentences>

**Key elements** (the author's intended takeaways)
<1–2 lines distilled from thesis + structure + conclusion>

**Teach-back**
<explain-to-a-friend paragraph>
› Self-test: <one question that proves comprehension>

**Apply now**
- <concrete action>
- …            (3–5, specific to this book)

<optional: "Read the whole thing if you want <X> — the 20% skips it.">
```

Deliver the sections; don't narrate the method ("First I'll frame…"). Match length to the book — a 120-page how-to gets a tight pass; a dense 500-page argument earns more. The structure creates the depth; padding doesn't.

---

## Worked example (what good looks like)

Distilling the source book itself — and modeling the fidelity tag:

---

# How To Read A Book A Day — Thomas Dev Brown
*[from public sources]*

**The 20% — what carries the book**
1. You don't need to read *faster* — you need a smarter target: the vital fraction of a book that carries its message.
2. Roughly **20% of a book** holds its core knowledge; master that and you own the book.
3. Find the key elements first (contents, headings, intro, conclusion) to surface what the author actually intends you to take away.
4. Aim for **comprehension, not word-for-word** recall — then reinforce by reciting it and sketching a mind map.
5. The proof you learned it: you can **teach it in your own words**. Then apply it — wisdom is knowledge applied.

**In plain English**
Reading a book a day isn't a speed trick. You skim to find the handful of ideas that matter, understand those deeply instead of reading every sentence, and lock them in by explaining them out loud and using them. If you can teach it, you've got it.

**Key elements** (the author's intended takeaways)
A repeatable method — target the 20%, comprehend over memorize, teach-back to verify — practiced daily, starting with non-fiction and a different book each day.

**Teach-back**
Most of a book is illustration wrapped around a few load-bearing ideas. Skim the structure to find those ideas, understand them in plain language rather than memorizing sentences, and confirm you've learned them by teaching them to someone else — then put them to use.
› Self-test: *Given a new non-fiction book, what's the first thing you do — and why is it not "start reading page one"?*

**Apply now**
- Next non-fiction book: read the contents, intro, and conclusion first; write the thesis in one sentence before reading a single chapter.
- As you read, keep only ideas that pass the drop test — if the argument survives without it, don't note it.
- After finishing, close the book and say the whole thing in three sentences out loud.
- Sketch a six-branch mind map from memory; the gaps are what you didn't actually learn.
- Teach it to one person this week.

Read the whole thing if you want the author's worked practice routine — the 20% skips the day-by-day drills.

---

Notice: the fidelity tag is the first thing on the page, the 20% is genuinely ~5 ideas (not 15), and the apply layer is specific enough to do tomorrow.

---

## On request: save it

**"save it" → vault.** Write to `$VAULT/distill/distill-<book-title-kebab>.md` (create `distill/` if absent). The `distill-` prefix is load-bearing: wiki-style links resolve by basename across the whole vault, so an un-prefixed file would collide with the book node `books/<slug>.md` and make every `[[slug]]` ambiguous. `vault/build_nodes.py` joins distillations on exactly this `distill-<slug>.md` shape and transcludes the body into the node on the next rebuild — it never writes into your distillation. Same section structure as the inline output. Frontmatter:

```
---
name: "<Book Title>"
type: distillation
book: "<Book Title> — <Author>"
source: apply-what-you-read
fidelity: full-text | public-sources | partial
corroborated: true | false | partial      # did any marked idea leave a receipt in the reader's own writing? (see agents/distill/DISTILL_PROMPT.md, Rule 2)
method: "Thomas Dev Brown, How To Read A Book A Day (2015)"
created: <YYYY-MM-DD>
related: []
---
```

Credit the method to Thomas Dev Brown in a provenance line. If the reader wants a mind map, render a single self-contained HTML file — a central hub (book + author), one branch per core idea, a numbered "apply now" strip — and let the branch count follow the 20%. No external dependencies; the map is the reinforcement step from the method made literal.

---

## Fidelity discipline (the load-bearing rule)

Every claim about a book you haven't read in full is **inference until verified against the text.** This skill's one way to lose trust is to present a confident distillation of a book you only read *about*.

- **Tag every output** with its fidelity on line one. No exceptions.
- **`[from public sources]` means hedge the specifics.** State the thesis and themes (well-corroborated), but do not invent chapter contents, coined-term definitions, or "the author says X" quotes you can't source.
- **When a named technique or framework can't be verified, mark it `[unverified]`** and say what would confirm it — don't guess at what an acronym stands for or what a model contains. (This skill was born from exactly that mistake: a branded strategy surfaced in reviews with no verifiable expansion; the honest move was to leave it out, not invent it.)
- **Never upgrade the tag to flatter the output.** Partial text is partial text.

This is the repository's standing inference rule applied to books: cite the primary source, or mark it inference.

---

## Quality bar & anti-patterns

- **The chapter-recap trap.** If your output reads like the table of contents with sentences, you've summarized, not distilled. Distill to the 20%; a TOC recap is the exact thing the method rejects.
- **Don't inflate the 20%.** Six ideas max. A list of fifteen is a re-outline wearing a distillation's clothes.
- **The apply layer must be concrete and book-specific.** Generic self-help verbs ("reflect," "internalize," "be mindful") are a tell that you didn't actually extract anything usable.
- **The teach-back test must require understanding.** If the answer is a fact you could look up in the index, it's trivia, not a comprehension test.
- **Fidelity honesty over polish.** A hedged `[from public sources]` distillation that's honest beats a confident one that fabricates. Tag it, hedge the specifics.
- **Fiction is a different job.** The method is built for informational/non-fiction. For a novel, distill themes and argument, not "how to apply it" — and say plainly that a novel's value often *is* the full read.
- **Don't narrate the method.** Deliver the five sections; the structure should be felt, not announced.
- **Match effort to the book.** A slim how-to gets a short pass. Don't manufacture depth the book doesn't have.

---

## Provenance

The method is Thomas Dev Brown's, from *How To Read A Book A Day: The Ultimate Guide to Quickly Retain and Absorb Information* (2015). The contribution here is the enforced pipeline — skeleton before cut, cut before simplify, comprehend before apply — and the fidelity-tagging discipline that keeps a distillation honest about how much of the book it actually saw.
