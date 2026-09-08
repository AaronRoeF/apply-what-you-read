# The reference corpus, and where every number came from

Every figure quoted anywhere in this project is here, with the command that produced it and the
channel it counts. If a document states one of these numbers differently, the document is wrong.

This file exists because the numbers drifted. Six independent readers reviewing this repository
found the same defect: 88 books in nine places and 89 in four, 4,425 highlights against 5,211, and
a "worst book" figure that the project's own plausibility appendix said was impossible. A project
whose thesis is *a citation you can check in ten seconds* had opened with numbers nobody could
check, including its author.

**The corpus itself does not ship.** `out/` is excluded by directory, so no reader can reproduce
these against the same library. What a reader can do is run the same commands against their own
and get the same *kinds* of number, and check that this repository is at least consistent with
itself. A test enforces the second part.

## The figures

| figure | value | produced by | counts |
|---|---:|---|---|
| books in the merged corpus | 88 | `corpus/merge_corpus.py` → `out/merged/*.json` | both channels, after the membership rule |
| merged records on disk | 89 | `ls out/merged/*.json` | includes one record the membership rule later drops |
| e-reader highlights | 4,425 | `capture/kindle/plausibility.py` | e-reader only |
| photographed pages | 800 | `corpus/build_bookcorpus.py` | photographs only |
| **marks** (highlights + pages) | 5,225 | `corpus/merge_corpus.py` | both channels |
| most highlights in one book | 460 | `capture/kindle/plausibility.py` | e-reader only |
| most marks in one book | 595 | `corpus/merge_corpus.py` | both channels |
| marks the matcher examined | 5,211 | `agents/librarian/candidates.py` | both channels, excluding records with no text |
| the reader's own files searched | 2,235 | `agents/librarian/candidates.py` | markdown under `READER_SURFACES` |
| marks with no verbatim reuse | 5,189 | `agents/librarian/candidates.py` | — |
| candidates | 21 | `agents/librarian/candidates.py` | — |
| noise | 1 | `agents/librarian/candidates.py` | — |
| candidates real on a hand read | about 5 | a person, reading all 21 | — |

## Reading the two that look like contradictions

**88 and 89.** The merge writes one record per book it accepts and the membership rule then drops
a book with no highlights and fewer than three pages. Ninety-nine times in a hundred you want 88,
which is the number of books with nodes. 89 is the file count before the rule is applied, and it
appears here only so that a reader who counts files is not confused.

**4,425 and 5,211 and 5,225.** Three different questions. 4,425 is the e-reader channel alone,
which is what the older analyses in `PITFALLS.md` and `VERIFICATION.md` were measuring. 5,225 is
every mark in both channels. 5,211 is what the corroboration matcher saw, which excludes records
carrying no text at all. Any document quoting one of these must say which.

**460 and 595.** The most-marked book has 460 e-reader highlights; a different book reaches 595
once photographed pages are counted. A figure over 460 is only correct if it says "marks".

## The rule this file exists to enforce

`CONTRIBUTING.md` asks that every number cite the artifact it was measured from. That was an
aspiration until now. `tests/test_docs.py` reads the table above and fails when any document
states one of these figures with a different value beside the same word, which makes the promise
mechanical rather than hopeful.
