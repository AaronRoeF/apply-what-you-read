# praxis — the ideas you actually used

A distilled library tells you what your books say. This tells you which of it changed something,
with a receipt: the passage, and the line in your own writing where it shows up.

```bash
VAULT=~/vault READER_SURFACES=~/writing agents/praxis/praxis-one.sh
```

Two agents run in order, and the order is the design.

**The qualifier proposes.** It reads the corroboration matcher's candidates, the *Apply* sections
of your distillations, the marked passages, and your own writing, and proposes records: a claim in
your words, the author's actual argument, a citation, and evidence of use.

**The adjudicator refuses.** Its only job is to reject. It opens every citation at the line given,
opens every evidence path, checks that the claim is something the author is actually arguing there,
and rejects anything it cannot verify. Unsure is `unverified`, never `applied`. The Tutor draws
only on what survived.

The proposer cannot write to the vault at all — its tool surface forbids it — so it cannot mark its
own homework even by accident.

## Why refusal is the default

An earlier version of this idea looked for relationships *between books*: twenty-eight candidates
from four independent lenses, each attacked by three skeptics reading the raw text. Twenty-seven
refutations stand. The one that was overturned was overturned because two of the three skeptics had
read a stale derived file instead of the source, which makes it a candidate again, not a finding.
Zero verified.

The machinery worked; the premise did not. What survives here is the narrow, checkable version of
the question: not "are these two books related?" but "did this idea leave a receipt in my work?"

## What you get with no writing of your own

Hypotheticals, labelled as such. Without files to check against, every idea is uncorroborated by
construction, and a store that accepted only corroborated records would be empty for a new reader
and would look like a broken tool rather than an honest one. Point `READER_SURFACES` at anything
you write — notes, project files, a journal — and the store starts filling with real receipts.

## Files

| file | what it is |
|---|---|
| `schema.md` | the record contract, and the two rules that are not obvious |
| `qualify.md` | the proposer's prompt |
| `adjudicate.md` | the skeptic's prompt |
| `praxis-one.sh` | runs both, in order, with different tool surfaces |
| `<vault>/praxis/praxis.jsonl` | every adjudicated record |
| `<vault>/praxis/praxis.md` | the survivors, rendered to read |
