# Documentation

Two tracks. The **tutorial** is numbered and takes you from a clone to a lesson; the
**reference** is what was measured, decided, and refuted while building it — read those before
you fork.

## Tutorial

| doc | read it when |
|---|---|
| [00-QUICKSTART.md](00-QUICKSTART.md) | first. The fixture end to end in under a minute, then your own library. |
| [01-HOW-IT-WORKS.md](01-HOW-IT-WORKS.md) | you want the shape before the code: the stages, the substrate choice, the two structural rules that keep derived layers from lying. |
| [02-KINDLE.md](02-KINDLE.md) | you are getting highlights out of a Kindle: the three file formats, and the crawler technique with its boundaries and its two silent-zero bugs. |
| [03-PHOTOS-AND-NOTES.md](03-PHOTOS-AND-NOTES.md) | you read on paper, or mark with a pen. Local OCR, the catalogue pass, and why photographs are a biased sample. |
| [04-VAULT.md](04-VAULT.md) | one markdown node per book: the contract, the rules the builder enforces, Obsidian optional. |
| [05-DISTILL.md](05-DISTILL.md) | the 20% that carries a book, your marks mapped onto it, and the fidelity tag on line one. |
| 06-PRAXIS.md · 07-TUTOR.md | v0.2 — the applied index and the cadence delivery. |
| 08-LIBRARIAN.md | v0.3 — relationships, refuted by default. |
| [FAQ.md](FAQ.md) | "I don't use a Kindle", "does it upload anything", "why did it find nothing". |

## Reference

**Start with [reference/PITFALLS.md](reference/PITFALLS.md).** It is the most transferable
document in the set. The others describe what was built; that one describes how the pipeline
lied, what caught it, and the checks that would have caught it sooner. Almost none of the
failures threw an exception.

| doc | read it if |
|---|---|
| [reference/PITFALLS.md](reference/PITFALLS.md) | you are building anything similar. Twelve defects with symptom, root cause, what detected it, and the fix — plus nine cheap checks. |
| [reference/DECISIONS.md](reference/DECISIONS.md) | you want the reversals and the evidence that forced them: a deletion feature abandoned on measurement, a graph hypothesis refuted, a ranking signal replaced. |
| [reference/VERIFICATION.md](reference/VERIFICATION.md) | you need to trust machine-read output nobody has read: count reconciliation, multi-signal scoring, calibrating against a human, adversarial refutation. Ends in a checklist. |
| [reference/AGENTS.md](reference/AGENTS.md) | the Librarian and Tutor design, stated after the corrections — including which parts the project's own evidence invalidated. |
| [reference/CLASSIFY-PATHS.md](reference/CLASSIFY-PATHS.md) | you are choosing between the API and the agent path for cataloguing page marks. |

Numbers throughout are measured against one real corpus (88 books, 4,425 highlights, 798
photographed pages) and traceable to the pipeline's own artifacts. Where a figure was
invalidated it is marked void rather than deleted; where something is unbuilt it says so.

## Status labels

Used once, in the README's status table, and referenced everywhere else:

| label | means |
|---|---|
| **Shipped** | in this repository today; the quickstart or a test exercises it |
| **Proven, landing** | running in the author's instance; the public port is in flight and flips to Shipped in the release it lands |
| **Designed** | specified, with the evidence for the design; not built |
