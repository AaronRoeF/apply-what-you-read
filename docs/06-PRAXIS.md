# 06 — Praxis: the ideas you actually used

Read this when your vault has distilled books in it and you want to know which of them changed
anything.

A distilled library tells you what your books say. Praxis is the smaller, harder store: the ideas
that left a receipt in your own work, each one with the passage and the line where it shows up.

```bash
VAULT=~/vault READER_SURFACES=~/writing bash agents/praxis/praxis-one.sh
```

`READER_SURFACES` is a colon-separated list of directories holding **your own writing** — project
notes, a journal, drafts. It is the only place a receipt can exist.

## What comes out

`<vault>/praxis/praxis.md`, newest first:

```
### Take the ten minutes before the first meeting rather than looking for a quieter week.
Marcus argues the retreat people seek elsewhere is available at any moment, and that looking
elsewhere for it is itself the avoidance.
**Used:** named it "the retiring" and did it before the morning call twice this week — `journal/2026-03-11.md:8`
*(citation: Meditations loc 269 🩷)*
```

Every record has a citation you can open and evidence you can check. `praxis.jsonl` beside it holds
the same records with the rejections, which are worth reading once: they show you what the system
refused to believe about your own reading.

## Two agents, and the order is the design

**The qualifier proposes.** It reads the corroboration matcher's candidates, the *Apply* sections
of your distillations, your marked passages, and your writing, and proposes records.

**The adjudicator refuses.** Its only job is to reject. It opens every citation at the line given,
opens every evidence path, checks the claim is something the author actually argues there, and
rejects what it cannot verify. Unsure is `unverified`, never `applied`.

The proposer cannot write to the vault at all. Its tool surface forbids it, so it cannot mark its
own homework even by accident. That is not suspicion of the model; it is that a store of "ideas you
used" is only worth reading if something was genuinely trying to keep records out of it.

## Why refusal is the default

An earlier version of this looked for relationships *between books*. Twenty-eight candidates came
from four independent lenses, and three skeptics attacked each one against the raw text.
Twenty-seven refutations stand. The one overturned was overturned because two of the three skeptics
had read a stale derived file instead of the source — which makes it a candidate again, not a
finding. Zero verified.

The machinery worked; the premise did not. What survives is the narrow version of the question:
not "are these two books related?" but "did this idea leave a receipt in my work?" That one is
checkable, and a checkable question with a small answer beats an interesting question with an
unfalsifiable one.

## What you get with nothing of your own written down

Hypotheticals, labelled. Without files to check against, every idea is uncorroborated by
construction. A store that accepted only corroborated records would be empty on your first run and
would look like a broken tool rather than an honest one. As you write, the receipts appear.

## The other direction: what you never used

```bash
READER_SURFACES=~/writing python agents/librarian/candidates.py
```

The same evidence, inverted. For every marked passage it asks whether a distinctive phrase from it
appears anywhere in your writing, and reports three answers: `unapplied` (nowhere), `noise` (a
phrase so common its presence proves nothing), and `candidate` (somewhere — a question for the
adjudicator, not a finding).

`unapplied` is the robust half and needs no agent at all. On the reference library it was 5,189 of
5,211 marks: a ranked list of the books you marked heavily and never spent. That number is not a
failure of the reader. It is the thing the whole pipeline exists to reduce.

Read [the matcher's own README](../agents/librarian/README.md) before trusting a `candidate`: it
states, with numbers, how often it is wrong.

## Next

[07-TUTOR](07-TUTOR.md) — one cited lesson at a time, delivered where you will see it.
