# Known gaps

What this project does not do, or does not do reliably, as of v0.2.0. Every entry here came from
adversarial review of the shipped code, and each one is written down because a gap you can read is
cheaper than a gap you discover.

## The Tutor's hypothetical marker is a floor, not a proof

A hypothetical lesson must carry an `APPLY:` line opening "Say " or "Suppose ", and outside quoted
spans no other line may address you. Both are enforced in code and tested.

**What that does not guarantee:** that a lesson never asserts something you did. The claim is
semantic, and no lexical rule decides it. English drops the subject, so a sentence like
"Tuesday, ten minutes before the nine o'clock — that was this passage" asserts a memory without
ever saying "you", and passes. Review demonstrated this against three successive implementations:
a verb denylist, a broader denylist with exemptions, and the current form constraint.

An earlier version of `07-TUTOR.md` promised such a lesson "can never be read as something you
did". That promise was withdrawn rather than defended.

**What to rely on instead, precisely.** A `current` or `past` lesson must name a real file inside
your vault or your own writing, and the message must reproduce a four-word run from it. The
citation is resolved too: a file citation must exist, and a work citation must name a book your
vault actually holds. Both are enforced in code and tested.

The citation checked is the one printed in the message, and the runner refuses a lesson whose
message and record disagree about it. An earlier version validated only the recorded citation, so
a lesson could print a citation for a book that does not exist while recording a real one.

A citation matches a book on your shelf by exact title, by a run of two or more shared words, or
by a single word when that word is the book's whole title. So a shelf holding *Dune* matches
"Dune, Book One", while "Habits, p. 12" does not match *Atomic Habits* — a citation that opens the
wrong book is a broken promise even though something opens. Works you have distilled but have no
node for count as being on the shelf.

Two limits on that, because an earlier draft of this page overstated it. **Quoting a file is not
the same as the file supporting the claim** — the check bounds fabrication from nothing, not
misattribution of something real. And **a vault with no `books/` directory yet cannot be checked
against**, so on a new reader's first runs the work citation is unverified and the check is
skipped rather than failing them.

**Known holes in the form check itself** (narrow, needing hostile composition, open for 0.2.1):
two stray quote characters can mask prose as a quotation; the quotation exemption is line-scoped,
so a genuine two-line quotation that addresses its reader is wrongly refused while a single-line
fake one is wrongly allowed; text after a compliant "Suppose " opener on the APPLY line is
unchecked; and a homoglyph for a Latin character defeats the token match.

## The corroboration matcher is recall, not evidence

`candidates.py` finds every place a marked phrase appears in your writing. On the reference library
that was 21 candidates from 5,211 marks, of which roughly five were a real idea travelling into the
work; the rest were phrases of the English language occurring in both places. `unapplied` is the
robust half. Treat a `candidate` as a question for the Praxis adjudicator, never as a finding. The
numbers and the reasoning are in [08-LIBRARIAN](../08-LIBRARIAN.md).

## Photographs are a biased sample, and so is any single channel

A pass built on photographed pages alone concluded a reader had never engaged with a chapter they
had marked twenty-two times on their e-reader. Neither channel is a superset of the other. Every
generated file says so; do not remove that line when you fork this.

## Smaller, open for 0.2.1

- **A comma in your vault path breaks the agents' permissions**, because the rule list they are
  given is comma-separated and the syntax has no escape. Spaces and parentheses are fine; a comma
  is not. Both runners now refuse at the start and name the reason, rather than letting you debug
  an agent that quietly read nothing.
- `candidates.py` holds a surface file in memory several times over; a very large file can spike
  memory. It fails loudly and destroys nothing.
- The Tutor's stale-lock break races: measured at **1 run in 12** when two are started
  back to back against an already-stale lock, which delivers the same lesson twice. The shipped
  schedules are hours apart, so it needs a manual double-start to reach.
- **A Tutor that has never succeeded can fail silently.** The loud failure row is written to the
  ledger, and the ledger is only created after a first successful send — so an installation that
  has never worked has nowhere to record why. The scheduling examples log to `/tmp`, which macOS
  purges. Redirect the log somewhere durable until you have seen a lesson arrive.
- `candidates.py` follows symlinked markdown files out of the directories you gave it, so a link
  inside your writing can pull a file from anywhere into a receipt. Point it at directories you
  would show a colleague, as its own documentation says.
- A line separator character (U+2028) inside a candidate record can break consumers that split the
  output by lines, and the Praxis runner does not surface that error — the applied count
  under-reports instead.
- A named pipe with a `.md` name inside your surfaces makes `candidates.py` wait forever.
- The Notes exporter builds a database URI without escaping, so a temporary directory whose path
  contains `?` silently drops the read-only flag on the copy it opens.
- The 3,000-character ceiling counts characters; the colour markers the prompt mandates cost three
  bytes each, so a maximal message can exceed some push services' byte limits.

## Not built, on purpose

The cross-book knowledge graph. Twenty-eight candidate edges, twenty-seven standing refutations,
zero verified. [08-LIBRARIAN](../08-LIBRARIAN.md) explains why rebuilding it would be a mistake.
