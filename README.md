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

So I measured it on mine. 88 books. 5,211 passages marked over years. Then I searched every one of
those 5,211, word for word, against the 2,235 files I'd written since — notes, plans, documents,
anything.

**5,189 of them don't appear in that writing anywhere.** Twenty-two turned up. I read those
twenty-two by eye, and about five were a real reuse rather than two sentences happening to share
ordinary words.

The search is literal, so it's wrong in both directions. It can't see an idea you absorbed and put
in your own words, or one that changed a decision you never wrote down, which means the true number
is kinder than 5,189. It also can't tell reuse from coincidence, which is why twenty-two came down
to five. Sources, and the tightening that didn't work:
[reference/CORPUS](docs/reference/CORPUS.md), [08-LIBRARIAN](docs/08-LIBRARIAN.md).

The caveats don't rescue it. My most-marked book carries 595 marked passages, and not one of them
turns up anywhere.

**Those numbers aren't research somebody did about reading. They're output.** The matcher that produced them
ships here, in `agents/librarian/candidates.py`, and it runs against your library instead of mine.
Most people suspect they aren't applying what they read. Almost nobody has a number. You can have
yours before lunch.

> **Pointing an agent at this?** Send it to **[AGENTS.md](AGENTS.md)** instead of here. That file
> is a working brief: the five things to ask you first, the exact ten-step sequence, the decisions
> already settled, and the mistakes that otherwise cost a session. It runs the project; this page
> explains why the project exists.

## IMPORTANT NOTE ON GOVERNANCE AND SECURITY

I'm leaving out big parts of my implementation because I'm not interested in disclosing all the specifics of my security and governance setup. You can see parts of what I'm doing here: agentrust-io.com if you're interested. And generally assume this is a project I'm sharing, not a product. I hope you get value. Enjoy! 

---

## What this is, before you read further

It's not a packaged product and it isn't trying to become one. It's a working project, built for
my own shelf, published because a few of its parts are worth borrowing — or stealing outright —
whether or not you ever run the whole thing.

The parts I'd steal, if I were you:

**A skeptic that refuses by default.** Praxis proposes, then a critic tries to kill the proposal.
Every tool in this category generates confident, plausible output. Almost none of them ship
something whose job is to say no. [06-PRAXIS](docs/06-PRAXIS.md).

**A citation contract that resolves.** Every lesson points at the exact span it came from, so you
can call its bluff in ten seconds. A pointer that resolves isn't the same as a claim that's
supported, and the difference is enforced in code, not promised in a prompt.

**A feature documented because I refused to build it.** The cross-book Librarian is specified,
argued, and deliberately unbuilt. The premise came out refuted 27 to 1, and
[08-LIBRARIAN](docs/08-LIBRARIAN.md) publishes the score against it. So is the tightening that
didn't work.

**Local OCR of things that were never digital.** Pen marks, brackets, marginalia, a filled-in
worksheet, a book you only ever read on paper. Apple Vision on your own machine — no network, no
API key.

What I want back is feedback, not stars. Whether the skeptic refuses the right things. Whether the
citation floor holds on a library that isn't mine. Whether the Librarian number means anything on
someone else's shelf. Open an issue and tell me where it's wrong.

## Three worked examples, so you can see the shape

The books are off my shelf. The lives aren't. Every name, meeting and situation below is made up,
and the locations are illustrative rather than transcribed — the running system emits the verbatim
span with its real location and colour, and you can watch it do that against the public-domain book
that ships here.

**One — the feedback you were about to give, inverted.**

Tomorrow, 10:30 — *1:1 with Jordan Rivera*. You have been putting off a hard conversation for three
weeks.

```
APPLY WHAT YOU READ LESSON

HELD: Radical Candor — Kim Scott, on soliciting criticism before you hand any out: the fastest
way to make feedback survivable is to be visibly bad at receiving it first, in public, from the
person you are about to give it to.

WHY HELD: Marked when you were preparing a different hard conversation. Never spent.

APPLY: Suppose you open tomorrow by asking Jordan for one thing you are doing that makes their
job harder — and then say nothing at all until they actually answer.

(citation: Radical Candor, 🟡)
```

The lesson didn't know the conversation was hard. It knew you'd marked that passage and never
spent it, and that a 1:1 was the next place it could land.

**Two — the deal that looks fine because only one person is in the room.**

Thursday, 15:00 — *Acme Robotics — renewal forecast call*. Eleven months of meetings, always the
same one attendee.

```
APPLY WHAT YOU READ LESSON

HELD: The Qualified Sales Leader — John McMahon, on champions: a champion who cannot get you to
the person who signs is not a champion, however much they like you.

WHY HELD: Marked two quarters ago. The note you left on it said "check this against the pipeline."
You did not.

APPLY: Suppose that before Thursday you write down who signs at Acme, and if the honest answer is
"I don't know", that is the call — not the renewal.

(citation: The Qualified Sales Leader, 🟡)
```

**Three — the most important output is the one where it refuses.**

Friday, 11:00 — *Board prep*.

The obvious move is to grab something marked about decision-making and staple it to the meeting.
Praxis won't. The proposer offers the match, the skeptic asks what it would change about Friday,
and a passage that changes nothing gets **rejected**, with the reason written down:

```
PRAXIS — proposal rejected

CANDIDATE: Thinking, Fast and Slow — Daniel Kahneman, on base rates.
PROPOSED FOR: Friday board prep.
SKEPTIC: Refused. The passage is about estimating an unknown probability. Nothing in the
proposal names a number that would change, or a decision that would go the other way.
Generic relevance is not application.
```

A tool that can connect any book to any meeting is a horoscope. **The refusal is the feature.**
It's what makes the lessons that do arrive worth opening, and it's the part most worth stealing
whatever else you take.

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

Marks arrive through three channels and are merged into one corpus: **e-reader highlights**
(`My Clippings.txt`, an *Export Notes* HTML file, or a Readwise CSV), **photographed pages** read by
local OCR — pen marks, brackets, marginalia, anything never read on a screen — and **an Apple Notes
folder**, which carries typed text, photos and Apple Pencil handwriting through Apple's own
recognisers. Formats, flags and the crawler for providers with no export are in
[02-KINDLE](docs/02-KINDLE.md) and [03-PHOTOS-AND-NOTES](docs/03-PHOTOS-AND-NOTES.md).

Neither channel is a superset of the other, and that has caused more trouble here than anything
else. A pass built on photographs alone concluded a reader "never engaged" with a chapter
they had in fact marked twenty-two times in the other channel. See
[docs/reference/PITFALLS.md](docs/reference/PITFALLS.md); that failure has four siblings.

The merged corpus becomes **one markdown node per book** with uniform frontmatter — an
[Obsidian](https://obsidian.md) vault if you use one, a folder if you don't — so the whole library
is one directory any agent can grep. Each book is **distilled** to the ~20% that carries it
(Thomas Dev Brown's method), with your own marks mapped onto it.

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

Two labels, defined once and used everywhere: **Shipped** — in this repository today, exercised
by the quickstart or a test. **Designed** — specified, with the evidence for the design, and not
built. Of 11 capabilities, 9 are shipped and 2 are designed. The full
table, row by row with its path, is in [reference/STATUS](docs/reference/STATUS.md).

One of the designed entries is there on purpose. The cross-book Librarian — the judge that would
decide whether two books are really saying the same thing — is **deliberately unbuilt**: the premise
came out refuted 27 to 1 when it was tested, and [08-LIBRARIAN](docs/08-LIBRARIAN.md) carries the
score against it rather than quietly dropping the idea.

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
