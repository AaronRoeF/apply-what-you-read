# 05 — Distill: the book, reduced to the part you'll use

Method credit: Thomas Dev Brown, *How To Read A Book A Day: The Ultimate Guide to Quickly
Retain and Absorb Information* (2015). The contribution here is the enforced pipeline and the
fidelity discipline; the method is his.

## The claim

Most summaries recreate the table of contents. Brown's method rejects that: a book's argument
rides on a vital ~20%, and the rest is illustration, repetition, and padding. Take the 20%,
understand it well enough to teach it, apply it — and you have the book's value in an hour.

Five moves, in order. The order matters: skeleton before cut, cut before simplify, and only
ask "how do I use this" once you actually understand it.

| | move | what it does |
|---|---|---|
| 1 | **Frame** | Get the best available source and **tag the fidelity**. File-first. |
| 2 | **Skeleton** | Thesis, structure, intro and conclusion — the author's *intended* takeaways. |
| 3 | **The 20%** | 3–6 ideas the argument stands on. The drop test: remove an idea; if the argument still stands, it was illustration. |
| 4 | **Plain** | Each idea in the words you'd use at dinner. Comprehension, not transcription. |
| 5 | **Teach + Apply** | An explain-to-a-friend paragraph, one self-test question, and 3–5 actions you could take this week. |

## The fidelity tag is the load-bearing rule

The first line of the body — right after the frontmatter and the title — is the fidelity tag,
one of:

- `[from the full text]` — a provided file or a rich corpus record was distilled
- `[from partial text: <what was seen>]` — your marks, not the book; the agent states what it
  saw, e.g. `[from partial text: 35 highlights + 5 photographed pages]`
- `[from public sources]` — description, contents, interviews, summaries used as leads

Every claim about a book the agent has not read in full is inference until verified against
the text. The tag is a promise about how much to trust what follows. It exists because the
failure mode of book summaries is presenting inference as if the book had been read — this
skill was born from exactly that: a branded strategy surfaced in reviews with no verifiable
expansion, and the honest move was to leave it out, not invent it. `[unverified]` marks a
named framework that could not be confirmed. The tag is never upgraded to flatter the output.

## What makes this more than a summary: your marks

With a book node from this pipeline, the distillation is run against the merged corpus
record — every highlight, every photographed page — and maps them onto the book's 20%:

- **Where you converged** — the core ideas you marked, and how heavily.
- **What you marked that the book doesn't foreground** — your angle.
- **Still available to you** — core ideas absent from your marks, framed as what the book still
  has to offer. Hedged for sample size; never a deficiency audit.
- **Corroboration** — for each idea that seems to matter, did it change anything *outside*
  the book? The agent searches your own writing (`READER_SURFACES`) for distinctive multi-word
  phrases and reports, with `file:line`, what it found or that it found nothing.

That last section is the one that changed how the whole project thinks about signal, and it
comes with three ground rules that are in the prompt because each was learned the hard way
(`agents/distill/DISTILL_PROMPT.md`):

1. **Rarity is not significance.** Typed notes are about 1% of marks because typing on an
   e-reader is annoying, not because those moments were profound. A margin note is a reaction,
   not a commitment. Colour clusters by reading session; a declared colour key
   (`04-VAULT.md`) outranks any inference.
2. **Corroboration is the signal.** A mark matters if it left a receipt outside the book, and
   that is observable. The search must use phrases of three or more distinctive words — an
   early attempt that matched single common words hit 782 files and proved nothing. No
   distinctive phrase, no claim.
3. **Never infer a gap from missing data.** `catalogued: false` means nobody looked. One
   "never engaged with this chapter" finding was refuted by twenty-two marks in the other channel.

## Three ways to run it

| how | when |
|---|---|
| `distill <book>` in a Claude Code session opened here (`skills/distill/distill.md`) | one book, you in the loop; `save it` writes the file |
| `VAULT=… bash agents/distill/distill-one.sh <slug> --context reader-context.md` | one book, headless; exits non-zero if the agent finishes without writing |
| the Workflow `agents/distill/distill-library.workflow.js` | every book, one agent each, over a frozen manifest slice with a hash check first |

All three write `<vault>/distill/distill-<slug>.md`; the next `vault/build_nodes.py` transcludes
it into the node. `agents/distill/README.md` has the library procedure. Claude Code discovers
the interactive skill through `.claude/skills/distill/SKILL.md` in the repository (a pointer at
the canonical text), so open the session with the repository as its working directory. The
interactive skill writes nothing until you say `save it`.

## Configuration, and what leaves your machine

| variable | meaning | default |
|---|---|---|
| `VAULT` | the vault the distillation is written into | none — required |
| `RG_OUT` | where the merged corpus lives | `./out` |
| `READER_SURFACES` | colon-separated directories holding *your own writing* — journal, project notes, decisions — that the corroboration search greps | empty: every idea is uncorroborated by construction, and the run says so once |
| `READER_CONTEXT` | a short file about who you are this week; the fixture's is `fixtures/meditations/reader-context.md` | none |

Distill runs through the `claude` CLI, which talks to Anthropic's API under your own account —
the same as any Claude Code session. What goes over the wire is what the agent reads: the
prompt, the book's merged record (`out/merged/<slug>.json` and `.md` — your highlights and
page text for that book), the reader-context file (inlined verbatim), and any file the agent
opens while searching `READER_SURFACES`. Nothing else in the vault is sent unless the agent
reads it. The pipeline through the vault sends nothing anywhere.

The headless runner scopes the agent's tools: `Read` only under this repository, `RG_OUT`,
`VAULT` and each `READER_SURFACES` directory; `Edit` only under `VAULT/distill/`, which is
the whole of the write grant because an `Edit` path rule covers every file-editing tool,
creation included, and a path-scoped `Write` rule does not exist; `Grep`,
`Glob`, `Bash(grep:*)` and `Bash(ls:*)`. It cannot read outside those roots or write anywhere
else, and your own Claude Code settings are not loaded for the run, so a permissive personal
config cannot widen that list. Keep `READER_SURFACES` to directories you would show a colleague. The runner kills the
agent after `DISTILL_TIMEOUT_SECS` (default 900) and fails loudly if the agent exits clean
without writing. One book costs one agent conversation of a few tens of thousands of tokens;
the exact figure depends on the corpus record and your account's model.

`corroborated: true | partial | false` lives in the distillation's frontmatter and its
Corroboration section; the node shows only `distilled: true` and transcludes the body.

## The output

```
# <Book Title> — <Author>
*[fidelity tag]* · 35 highlights · 5 photographed pages · corroborated: partial

**The 20% — what carries the book**      1–6 ideas, grounded in your marks where possible
**In plain English**                     one short paragraph
**Where your marks land**
**What you marked that the book doesn't foreground**
**Still available to you**
**Corroboration**                        phrases searched, file:line hits, or "none found"
**Teach-back**                           3–4 sentences + one self-test question
**Apply now**                            3–5 concrete actions — THE PAYLOAD
**Fidelity note**                        what was read vs inferred; what would strengthen this
```

`corroborated: true | partial | false` is not a grade. An uncorroborated book is a book whose
ideas are still available to you — which is the whole point of the next two documents.

## Anti-patterns the skill refuses

The chapter-recap (a table of contents with sentences); fifteen "key" ideas (a re-outline);
generic apply verbs — *reflect*, *internalize*, *be mindful* — which are a tell that nothing
usable was extracted; a teach-back question you could answer from the index; and, for fiction,
pretending the method applies — a novel's value often *is* the full read, and the skill says so.
