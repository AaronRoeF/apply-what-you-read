# Capability status — what is shipped, what is only designed

**Why this file exists:** the README says how many capabilities are shipped and how many are
designed. This is the row-by-row table behind that count, with the path for each one, so a claim in
the README can always be traced to a file you can open.

Labels are defined here and referenced everywhere else. **Shipped** — in this repository
today; the quickstart or a test exercises it. **Designed** — specified, with the evidence for the design; not built.

| capability | status | where |
|---|---|---|
| Kindle: `My Clippings.txt`, Export Notes HTML, Readwise CSV → one record | Shipped | `capture/kindle/`, [02-KINDLE](docs/02-KINDLE.md) |
| Plausibility report (the sorted count vector, every run) | Shipped | `capture/kindle/plausibility.py` |
| Photographed pages: folder-per-book manifest, OCR seam (Apple Vision / stub), catalogue prompt | Shipped (OCR: macOS) | `capture/pages/`, [03-PHOTOS-AND-NOTES](docs/03-PHOTOS-AND-NOTES.md) |
| Corpus: membership in one place, two channels merged, the sampling-bias warning in every file | Shipped | `corpus/` |
| Vault: one node per book, nine enforced rules, each tested | Shipped | `vault/build_nodes.py`, [04-VAULT](docs/04-VAULT.md) |
| Distill: skill, headless runner, frozen-manifest workflow, three ground rules | Shipped | `skills/distill/`, `agents/distill/`, [05-DISTILL](docs/05-DISTILL.md) |
| Fixture: public-domain book, every input format, provenance enforced by test | Shipped | `fixtures/meditations/` |
| Apple Notes folder → pipeline: typed text, photos with Apple's own OCR, Pencil handwriting via the recogniser, four note kinds, and a watcher that exports only what changed | Shipped (macOS) | `capture/notes/`, [03-PHOTOS-AND-NOTES](docs/03-PHOTOS-AND-NOTES.md) |
| Praxis: the applied index — a proposer, then a skeptic that refuses by default | Shipped | `agents/praxis/`, [06-PRAXIS](docs/06-PRAXIS.md) |
| Tutor: one cited lesson per run — compose-only, a floor checked in code, three channels, a ledger, and a loud kill switch | Shipped | `agents/tutor/`, [07-TUTOR](docs/07-TUTOR.md) |
| Reference crawler for a notebook web view, with the silent-zero regression tests | Designed (v0.3) | arrives as `capture/kindle/notebook_crawl.py`; technique in [02-KINDLE](docs/02-KINDLE.md) |
| Librarian: the corroboration matcher — which marked ideas left a receipt, and which never did | Shipped | `agents/librarian/candidates.py`, [its README](agents/librarian/README.md) |
| Librarian: judge and refute-by-default for the cross-book case | Designed, deliberately unbuilt | the premise is refuted 27–1; [08-LIBRARIAN](docs/08-LIBRARIAN.md) |
| Cross-book knowledge graph | Refuted 27–1 — not on the roadmap | [docs/reference/DECISIONS.md](docs/reference/DECISIONS.md) |

Labels mean exactly what they say. **Shipped** — in this repository today, exercised by the
quickstart or a test. **Designed** — specified, with the evidence for the design, and not built.
Nothing sits in between, and nothing is described here that is not in one of those two states.
