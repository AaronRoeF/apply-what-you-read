# apply-what-you-read

You mark things worth keeping and then never see them again. This turns those marks into one
short lesson a day: a passage you marked, what its author was actually arguing, one concrete thing
to do about it this week, and a citation you can open in ten seconds to check it. It runs on your
own machine against your own material, and it also tells you what you marked and then never used.

Books are where this started, not where it stops. Anything with a source worth citing works the
same way — highlights, quotes, marginalia in a paper book, a talk you took notes on. The pipeline
does not care what the thing was; it cares that you can point at where the words came from.

That is the whole of it. The rest of this page is why it is worth having.

**Name three ideas from the books you read last year that changed how you work.**

Most people who read a great deal cannot, and it is not a memory problem. You already did the
hard part: you noticed the passage was important and you marked it. Then the book closed and the
mark stopped existing.

Here is one attempt to measure it. One real library: 88 books and 5,211 marked passages —
highlights from an e-reader plus photographed pages — searched word-for-word against 2,235 files
the reader had written since. Every figure in this document, and where it came from, is in
[reference/CORPUS](docs/reference/CORPUS.md).

| | |
|---|---|
| marks whose words appear nowhere in their own writing | **5,189** |
| marks whose words appear somewhere | **22** (21 worth a second look, 1 too common to mean anything) |
| of those 21, ideas that had genuinely travelled, read by hand | **about 5** |

Take the instrument's limits seriously, because they cut both ways. Searching for exact phrases
cannot see an idea you absorbed and put in your own words, or one that changed a decision you
never wrote down — so the true figure is kinder than 5,189. It also cannot tell a real reuse from
a coincidence of the language, which is why 21 becomes about five once a person reads them. The
project's own docs say this at more length in [08-LIBRARIAN](docs/08-LIBRARIAN.md), including the
tightening that did not work.

What survives the caveats is still stark. The most-marked book in that library carries 595 marked
passages and not one of them turns up anywhere. The library is a serious one, marked carefully over
years, by someone who reads more than most people you know.

**That table is not research somebody did about reading. It is output.** The matcher that
produced it ships in this repository — `agents/librarian/candidates.py` — and it runs against
your library, not that one. Point it at your own highlights and your own writing and it will
hand you your own number, with the same caveats attached and the same honesty about what exact
phrase matching cannot see.

Most people guess they are not applying what they read. Almost nobody has a figure. You can have
one before lunch, and it is the most useful uncomfortable thing in here.

## What this is, honestly, before you read further

This is not a packaged product and it is not trying to become one. It is a working project, built
for one reader's shelf, published because several of its parts are worth borrowing — or stealing
outright — whether or not you ever run the whole thing.

The parts I would steal, if I were you:

**A skeptic that refuses by default.** Praxis is a proposer and then a critic whose job is to say
no. Every tool in this category generates confident, plausible output; almost none of them ship
something whose success condition is rejection. See [06-PRAXIS](docs/06-PRAXIS.md).

**A citation contract that actually resolves.** Every lesson points at the exact span it came from,
so you can call its bluff in ten seconds. A resolving pointer is not the same as a supported claim,
and the difference is enforced in code rather than promised in a prompt.

**A feature documented because it was refused.** The cross-book Librarian is specified, argued, and
deliberately unbuilt — the premise came out refuted 27 to 1, and
[08-LIBRARIAN](docs/08-LIBRARIAN.md) carries the score against it. The tightening that did not work
is written up too.

**Local OCR of things that were never digital.** Pen marks, brackets, marginalia, a filled-in
worksheet, a book you only ever read on paper — Apple Vision on your own machine, no network, no
API key.

**What I actually want back is feedback.** Not stars, not adoption. Whether the skeptic refuses the
right things, whether the citation floor holds on a library that is not mine, whether the Librarian
number means anything on someone else's shelf. Open an issue and tell me where it is wrong — that
is the contribution this needs most.

## Tomorrow morning, one marked passage comes back to you

Tomorrow morning, one passage you marked arrives — with what its author was actually arguing,
one concrete thing to do about it this week, and a citation you can open in ten seconds to check
that the whole thing is real.

```
APPLY WHAT YOU READ LESSON

HELD: "it is in thy power to retire into thyself, and to be at rest" — Meditations, loc 269, 🩷.
Marcus is arguing that the retreat people look for in the countryside is available at any moment,
and that going looking for it elsewhere is itself the avoidance.

WHY HELD: Marked two years ago, never spent since.

APPLY: Suppose you take ten minutes before the first meeting tomorrow, door shut, no inbox.

(citation: Meditations loc 269 🩷)
```

Not a summary. Not a flashcard. One idea you already decided was worth keeping, handed back at a
moment when you can use it, in a channel you already open.

**It also ranks your library by what you appear never to have used.** The same search, inverted.
On the reference library the top of that list held four books with over 300 marks each and no
verbatim reuse anywhere at all. Read it as a list of places to look, not a verdict — the instrument is
literal, and you will find at least one book on it whose ideas you use every week without ever
quoting them.

## Three worked examples, so you can see the shape

Every name, calendar entry and situation below is invented. The books are real and the citations
resolve; the lives they land in do not exist. That is also how the repository's own fixture works —
a public-domain book, so the whole pipeline can be watched end to end without anyone's library.

**One. The calendar says what tomorrow is. Your marks say what to bring to it.**

Tomorrow, 09:00 — *Quarterly review with Priya Shah*. Recurring, eleven months running.

```
APPLY WHAT YOU READ LESSON

HELD: "it is in thy power to retire into thyself, and to be at rest" — Meditations, loc 269, 🩷.
Marcus is arguing that the retreat people look for in the countryside is available at any moment,
and that going looking for it elsewhere is itself the avoidance.

WHY HELD: Marked two years ago, never spent since.

APPLY: Suppose you take ten minutes before the quarterly review tomorrow, door shut, no inbox —
and decide what you actually want out of it before anyone else fills the hour for you.

(citation: Meditations loc 269 🩷)
```

The lesson did not know about the meeting. The *timing* did. One idea you already decided was
worth keeping, handed back on the morning it is usable.

**Two. Conventional wisdom is cheap. A passage you marked yourself is not.**

Next week, 14:00 — *Acme Robotics — first call with their new VP of Engineering*.

Everyone knows "listen before you change things." It is advice, it is free, and it changes nothing.
What is different is a passage **you** marked, in your own copy, at a moment when you thought it
mattered — Michael Watkins on the first ninety days, on negotiating expectations early rather than
inheriting someone else's. You highlighted it. You have not looked at it since.

```
APPLY WHAT YOU READ LESSON

HELD: The First 90 Days, loc 531 🟡 — on establishing what success looks like with your
counterpart before the work starts, rather than discovering the mismatch at the review.

WHY HELD: Marked when you were the one being onboarded. Never applied from the other side.

APPLY: Suppose you spend the first ten minutes of the Acme call asking what a good first
quarter looks like to them, and write the answer down where you will both see it again.

(citation: The First 90 Days loc 531 🟡)
```

**Three. The most important output is the one where it refuses.**

Thursday, 11:00 — *Board prep*.

An obvious move here is to reach for a marked passage about decision-making under uncertainty and
staple it to the meeting. Praxis will not do it. The proposer offers the match; the skeptic asks
what it would actually change about Thursday, and a passage that produces no different action gets
**rejected**, with the reason recorded:

```
PRAXIS — proposal rejected

CANDIDATE: Thinking, Fast and Slow, loc 1,204 — on base rates.
PROPOSED FOR: Thursday board prep.
SKEPTIC: Refused. The passage is about estimating an unknown probability. Nothing in the
proposal names a number that would change, or a decision that would go the other way.
Generic relevance is not application.
```

A tool that connects any book to any meeting is a horoscope. **The refusal is the feature** — it
is what makes the lessons that do arrive worth reading, and it is the part most worth stealing
whatever else you take from here.

## What it costs to try

It runs end to end on a public-domain book that ships with the repository, so you can watch the
whole pipeline work before you point it at your own library:

```bash
git clone https://github.com/AaronRoeF/apply-what-you-read && cd apply-what-you-read
bash quickstart.sh --with-claude
```

Seven steps, ending in a lesson printed to your terminal — or, on one fixture book with none of
your own writing to draw on, a clean refusal explaining why nothing cleared the bar. Both are a
pass; the refusal is the rule working.

| | `bash quickstart.sh` | `bash quickstart.sh --with-claude` |
|---|---|---|
| how long | about 5 seconds | about 9 minutes, measured |
| account | none | a [Claude Code](https://claude.com/claude-code) login |
| network | one download of two Python packages, once | that, plus this one book's text to Anthropic's API |
| ends with | one book as a markdown file you can open | that, plus a distillation and one cited lesson |

Nothing uploads your library, then or ever — [05-DISTILL](docs/05-DISTILL.md) lists exactly what
leaves the machine.

**Then your own highlights, and here the honest number is hours, not minutes.** Getting marks out
of an e-reader is easy if you can plug the device in and copy one file. It is tedious if you read
in a phone app, where the export arrives as one email per book. It costs a subscription if you go
through a third-party service. [02-KINDLE](docs/02-KINDLE.md) walks all three; read it before you
plan an evening around this.

**Or hand the whole thing to your agent.** Clone this, open it in Claude Code or any coding agent,
and say:

> Read AGENTS.md and build me a plan for my own library.

It will ask you five questions — where your highlights live, whether you have photographed pages,
where you write, where a lesson should arrive, and whether your vault path has a comma in it,
which breaks the agents' permission rules — and hand back an ordered plan with what will not work
for you and why. `AGENTS.md` is written for the agent rather than for
you: the order of operations, the decisions already settled with their evidence, and the mistakes
that would otherwise cost you a session. Read the plan before you let it start.

## How it works — and why every stage shows its source

![Three channels of marks — e-reader highlights, photographed pages read by local OCR, and a notes folder — merge into one plain-markdown corpus per book, which builds one vault node per book. Three readers use it: Praxis lists what you marked and never used, Tutor sends one cited lesson a day, and Librarian (designed, not built) checks whether a marked idea ever left a receipt. Everything happens on your own machine.](assets/pipeline.svg)

Your marks come out of the places they already live, get joined into one corpus of plain markdown,
and every later stage reads that corpus and cites what it used. No stage infers what you meant.

```
capture  →  normalize  →  merge  →  vault  →  distill  →  Praxis  →  Tutor  →  Librarian
```

Your marks arrive through three channels, merged into one corpus:

| channel | what it captures | how |
|---|---|---|
| **e-reader highlights** | exact span text, colour, page/location, typed notes | `My Clippings.txt` from the device, the app's *Export Notes* HTML, a Readwise CSV — or, for providers with no export, a reference crawler of your own notebook web page (the page where your provider shows you your highlights, v0.3) |
| **photographed pages** | pen marks, brackets, marginalia, filled-in worksheets, any book never read on a screen | local OCR (Apple Vision via PyObjC) — no network, no API key; a stub engine elsewhere |
| **an Apple Notes folder** (v0.2) | everything you keep in one Notes folder: typed text, photographed pages, and Apple Pencil handwriting | an exporter reads the Notes database read-only and carries the text Apple already recognised — its own OCR of each photo and the stroke recogniser's text for handwriting, which beats image OCR on the same page — into the photographed-pages channel; a watcher keeps the folder flowing |

Neither channel is a superset of the other, and that has caused more trouble here than anything
else. A pass built on photographs alone concluded a reader "never engaged" with a chapter
they had in fact marked twenty-two times in the other channel. See
[docs/reference/PITFALLS.md](docs/reference/PITFALLS.md); that failure has four siblings.

The merged corpus becomes **one markdown node per book** with uniform frontmatter — an
[Obsidian](https://obsidian.md) vault if you use one, a folder if you don't — so the whole
library is one directory any agent can grep. Each book is **distilled** to the ~20% that
carries it (Thomas Dev Brown's method), with your own marks mapped onto it and a check of which
marked ideas ever left a receipt in your own writing. From there the loop closes: **Praxis**,
an index of the ideas you actually used; the **Tutor**, one cited lesson at a time to a channel
you already open; the **Librarian**, which looks for relationships and is built to refuse
most of what it finds.

## Two things this got wrong, and what they cost

Before the features, the failures. These two shaped everything above.

**A verification pass that returns nothing is a result.** The original thesis was that the
payoff would be a graph of connections *between* books. Twenty-eight candidate edges were
generated by four independent lenses (agents each looking for one kind of relationship) and
each attacked by three adversarial verifiers (agents whose only job is to refute the claim
against the raw text; a refutation that stands is a "kill"). Twenty-seven kills stand. One was
overturned on re-adjudication — two of the three skeptics had read a stale derived node
instead of the raw corpus — and that edge is a candidate again, not a finding: overturning a
kill does not make the edge true. Zero verified cross-book edges. The refutation machinery worked exactly as designed; the premise did not. That finding
is in [docs/reference/DECISIONS.md](docs/reference/DECISIONS.md), and it saved building the
wrong agent.

**Rarity is not significance when rarity is explained by friction.** Typed notes are about 1%
of all marks in the reference corpus, and an early analysis ranked them highest on that basis.
They are 1% because typing on an e-reader is annoying. The replacement signal is
*corroboration* — did a mark change anything outside the book — which is observable rather than
interpretive. Hand-adjudicated across twenty-eight books, it returned 4 corroborated, 11 partial, and 13 with
no receipt anywhere else.

## What actually works today, and what is only designed

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

## The first hour, and the first week

In an hour: your own library, parsed. Every book you have marked becomes one markdown file with
its highlights, its colours and its photographed pages counted side by side, and you can finally
see the shape of what you have been collecting. Most people are surprised twice — by how much is
there, and by which books turn out to be empty.

In a week: the books that matter distilled to the fifth that carries them, your own marks mapped
onto that, and a lesson a day. By the end of it the ledger has outcomes in it and you know which
lessons landed.

The node the quickstart produces (abridged — eight of its sixteen keys):

```yaml
name: "Meditations"
type: book
kindle_highlights: 35
typed_notes: 5
pages_captured: 5
highlight_colors: null      # null: no page catalogued (marks recorded by an agent) yet — never confused with []
distilled: false
related: []
```

Then your own Kindle, then a distillation whose first line says exactly how much of the book
it saw. [docs/00-QUICKSTART.md](docs/00-QUICKSTART.md) walks it, with the real output pasted
after each step.

## The part that decides whether this survives

A daily channel you learn to ignore is worse than one you never set up, so the loop is built to
notice that and stop. Every lesson gets a row in a ledger and a check-due date two weeks out. A
lesson landed if your own writing picked its idea up, or if you opened the file it cited. You are
never asked whether it was useful — that answer is unreliable and the asking is itself a cost.

**Seven lessons in a row that land nowhere turn it off.** Not quieter, not less often: off, with
the reason written into the ledger, until you switch it back on yourself.

Anything that arrives on a schedule eventually becomes wallpaper, and a system that keeps sending
into silence has stopped being a tutor and become a notification. [07-TUTOR](docs/07-TUTOR.md) has the rest, including what
the design does *not* guarantee.

## What you need before you start, stated plainly

- Python 3.11+ somewhere on the machine. `quickstart.sh` finds the newest 3.11+ interpreter on
  your PATH and builds `.venv/` with it — you do not make the venv yourself. macOS ships 3.9,
  which is too old; `brew install python@3.13` (or python.org) first. The Kindle path and
  everything through the vault are standard library.
- macOS for real OCR of photographed pages (Apple Vision; `pip install -r requirements-mac.txt`).
  Everything else runs on Linux; CI does.
- [Claude Code](https://claude.com/claude-code) for distill and the agents. The pipeline through
  the vault does not need it.
- No API key is required for any shipped path. Distill and the agents use your Claude Code
  login; what they send to Anthropic's API is listed in [05-DISTILL](docs/05-DISTILL.md).

## What it will never do with your library

- **The repository ships code, not corpus.** `out/` is git-ignored by directory. No book text,
  no highlight text, and no personal annotation ever enters version control — the only book
  text here is a public-domain excerpt with its provenance stated on the file and enforced by
  a test.
- **Extraction runs only against files you already have, or a session you authenticated
  yourself.** The tooling never handles credentials.
- **Only your own annotations are retrieved** — the selections you made and the notes you typed.
- **Redistribution is out of scope.** The corpus is single-user and local.
- **Terms of service vary by provider** and are your responsibility to check.

## What this is not

Not a summarizer (distill is the 20%, tagged with how much of the book it saw — not the table
of contents). Not flashcards or spaced repetition. Not a cross-book knowledge graph (see above).
Not a hosted service; no accounts, no telemetry. Not a tool for other people's libraries. Not a company product, and not on its way to
becoming one — this is one person's system, published so its parts can be taken and its mistakes
can be pointed at.

## Where to go next, depending on what you want

| doc | read it if |
|---|---|
| [00-QUICKSTART](docs/00-QUICKSTART.md) | you have five minutes and a terminal — start here |
| [07-TUTOR](docs/07-TUTOR.md) | you want to see what actually arrives, and what stops it becoming wallpaper |
| [06-PRAXIS](docs/06-PRAXIS.md) | you want the list of what you have never used |
| [01-HOW-IT-WORKS](docs/01-HOW-IT-WORKS.md) | you want the stage-by-stage shape before the code |
| [02-KINDLE](docs/02-KINDLE.md) | you are getting highlights out of a Kindle — three formats, then the crawler technique |
| [03-PHOTOS-AND-NOTES](docs/03-PHOTOS-AND-NOTES.md) | you read on paper or mark with a pen |
| [04-VAULT](docs/04-VAULT.md) | one node per book: the contract and the rules |
| [05-DISTILL](docs/05-DISTILL.md) | the 20%, your marks, and the fidelity tag |
| [08-LIBRARIAN](docs/08-LIBRARIAN.md) | the graph that was refuted 27–1, and what survived |
| [FAQ](docs/FAQ.md) | "I don't use a Kindle" and the other first questions |
| [reference/PITFALLS](docs/reference/PITFALLS.md) | **start here if you are building anything similar.** Twelve defects; almost none threw. |
| [reference/DECISIONS](docs/reference/DECISIONS.md) | the reversals and the evidence that forced them |
| [reference/VERIFICATION](docs/reference/VERIFICATION.md) | trusting machine-read output nobody has read |
| [reference/CORPUS](docs/reference/CORPUS.md) | every number here, with the command that produced it — read this before believing any of them |
| [reference/KNOWN-GAPS](docs/reference/KNOWN-GAPS.md) | what it does not do, or does not do reliably — including where a guard is a floor rather than a proof |
| [reference/AGENTS](docs/reference/AGENT-DESIGNS.md) | the Librarian and the Tutor, designed after the corrections |

## Where this sits

The same shape, applied to different material. Each stands alone.

| | |
|---|---|
| **[exo](https://github.com/AaronRoeF/exo)** | The environment this grew up inside — skills, hooks, slash commands and a plain-text knowledge base that compounds across sessions. The vault here is the same idea, narrowed to books. |
| **[exo-mesh](https://github.com/AaronRoeF/exo-mesh)** | The same local-first join applied to people instead of books: your mail, calendar, iMessage and contacts resolved into one record per person, on your own disk. |
| **[claude-code-patterns](https://github.com/AaronRoeF/claude-code-patterns)** | The patterns behind both — including the knowledge-base pattern the vault here is built on. |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: `bash tests/run.sh` passes,
`bash tests/publish-checks.sh --root .` reports zero errors, every number cites the artifact it was measured
from, and nothing that belongs in `out/` is ever committed.

## License

MIT — see [LICENSE](LICENSE). The fixture text is public domain (Project Gutenberg #2680; see
`fixtures/meditations/SOURCE.md`).

## Credits

The distill method is Thomas Dev Brown's, from *How To Read A Book A Day* (2015). OCR is
Apple's Vision framework via PyObjC. The fixture is Marcus Aurelius by way of Project
Gutenberg. The agents run on [Claude Code](https://claude.com/claude-code). The vault is
optionally [Obsidian](https://obsidian.md); [obsidian-mcp](https://github.com/AaronRoeF/obsidian-mcp)
and [apple-mcp](https://github.com/AaronRoeF/apple-mcp) are the sibling servers this grew up next
to, and [claude-code-patterns](https://github.com/AaronRoeF/claude-code-patterns) is where the
knowledge-base pattern behind the vault is written up.

Built by Aaron Fulkerson for one reader's shelf, and documented so it can be fixed for others.
