# 08 — The Librarian: what you marked and never used

Read this last. It is the part of the project that returned a negative result, and the negative
result is the most useful thing in the repository.

## The thesis that failed

The original plan was a graph of connections *between* books: this idea in one book answers that
idea in another, and the reader gets a map of their own thinking.

It was built and tested. Four independent lenses — separate agents, each looking for one kind of
relationship — produced twenty-eight candidate edges. Each candidate was then attacked by three
adversarial verifiers whose only job was to refute it against the raw text, not against any derived
file.

**Twenty-seven refutations stand.** One was overturned on re-adjudication, because two of the three
skeptics had read a stale derived node instead of the source; that edge is a candidate again, not a
finding. Overturning a refutation does not make an edge true.

Zero verified cross-book edges, out of twenty-eight.

The machinery worked exactly as designed. The premise did not. Building the agent anyway would have
produced a beautiful map of things that are not so, and every one of them would have carried a
citation. **A verification pass that returns nothing is a result**, and this one saved building the
wrong thing.

So the cross-book graph is not on the roadmap, and this document exists to stop anyone rebuilding it
by accident.

## What survived: a narrower question

Not "are these two books related?" but "did this idea leave a receipt in my own writing?"

```bash
READER_SURFACES=~/writing python agents/librarian/candidates.py
```

For every marked passage, up to three distinctive phrases are taken and searched across your files.
Three answers:

| status | meaning |
|---|---|
| `unapplied` | the phrase appears nowhere — an idea marked and never spent |
| `noise` | the phrase appears in more files than the floor allows; its presence proves nothing |
| `candidate` | it appears somewhere — **a question for a judge, never a finding** |

## How often the candidates are wrong, measured

On the reference library — 88 books, 5,211 marks, 2,235 of the reader's own files — this produced
**21 candidates**. Read by hand, about five were a real idea travelling from a book into the work:
a named practice from a management book appearing in an operating document, a framework's term of
art reused in a plan. The rest were phrases of the English language that happen to occur in both
places: "a leap of faith", "does the heavy lifting", "vp of engineering". Every match was true.
Most meant nothing.

Tightening did not fix it. Requiring each phrase to carry a token rare *within the library* removed
four of twenty-five and left the coincidences untouched, because those phrases are genuinely rare
inside a shelf of business books while being common in English.

That is the boundary of a phrase matcher, and naming it is more useful than hiding it. **This stage
is recall.** It finds every place a mark could have been used, cheaply, with no model and no
network, and the Praxis adjudicator decides which are real.

`unapplied` is the robust half and needs no judge: **5,189 of 5,211 marks** had no verbatim receipt
anywhere. That is the number the whole pipeline exists to reduce.

## The five rules, and the failure behind each

| rule | why |
|---|---|
| never one or two words | "the system", "first principles" match everything |
| at least two non-stop tokens | otherwise "of the same as" is a candidate |
| the stoplist is corpus-derived too | a shelf of management books says "leader" everywhere; a hand-written stoplist cannot know that |
| a noise floor: a phrase in more than max(25, 2%) of your files | an ancestor of this check matched a phrase in 782 files and called all 782 evidence |
| a mirror floor: a file matching more than 10 distinct phrases | one review file holding the scanned pages supplied 60 of the first 102 receipts — every one the book quoting itself |

A phrase in too many files is noise. A file with too many phrases is a mirror. The two floors are
the same idea seen from each side, and the second one cannot be replaced by a path rule: the file
that caused it had an ordinary name in an ordinary directory.

## Not built

`judge.md` and `refute.md` — an agent pair that adjudicates a candidate, refuting by default and
quoting both sides — and `write.py`, which would touch only a reserved `related:` field on a node.
The Praxis adjudicator already does the judging for the applied index; the standalone pair is for
the cross-book case, which is refuted, so it is designed and deliberately unbuilt.
