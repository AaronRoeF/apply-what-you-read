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
| files in `out/merged/` | 89 | `ls out/merged/*.json` | the 88 book records plus `_manifest.json` |
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

**88 and 89.** There are 88 books and 89 files, because `out/merged/` also holds
`_manifest.json`. That is the whole of it. An earlier version of this page said the 89th file was a
book the membership rule drops; that was wrong, and no book in this corpus meets the drop condition
(zero highlights and fewer than three pages). The rule exists and can fire; it has not fired here.

**4,425 and 5,211 and 5,225.** Three different questions. 4,425 is the e-reader channel alone,
which is what the older analyses in `PITFALLS.md` and `VERIFICATION.md` were measuring. 5,225 is
every mark in both channels. 5,211 is what the corroboration matcher saw, which excludes records
carrying no text at all. Any document quoting one of these must say which.

**460 and 595.** The most-marked book has 460 e-reader highlights; a different book reaches 595
once photographed pages are counted. A figure over 460 is only correct if it says "marks".

**798 and 800.** The photographed-pages channel measures 800, in the merged files and in
`_manifest.json` alike, and all 800 carry recognised text. Nine documents in this repository said
798. They have been corrected to the measured value. The honest part of this note is that the
project cannot reconstruct where 798 came from: the page files all predate the documents that
quote it, so the corpus did not grow underneath them. Treat 798 as withdrawn, not reconciled.

## The rule this file exists to enforce

`CONTRIBUTING.md` asks that every number cite the artifact it was measured from. Two tests in
`tests/test_docs.py` enforce part of that, and it is worth being exact about which part, because
the first version of this paragraph was not.

The first test reads the four corpus totals out of the table above and fails any clause that talks
about the corpus and states one of them differently. The second is a hand-written list of the
values this project has actually got wrong before. What they do not do is police every number in
the docs: a total stated in a clause that never mentions the corpus is not caught, and sub-counts
are deliberately exempt, because "one book went from 97 to 376 highlights" is a true sentence and
a check that fails on true sentences gets deleted rather than fixed.

The measure of this is a control probe. A reviewer appended five invented figures to a shipped
document and the original check caught one of them. It now catches three. That is the honest
number, and it is here rather than in a claim that the promise is mechanical.
