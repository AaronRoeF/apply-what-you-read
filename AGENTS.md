# For the agent

Read `README.md` for what this project is. This file is your working brief: what to ask before you
propose anything, the exact sequence, and the mistakes that will otherwise cost your reader a
session.

## What a good plan looks like

Six to ten steps, each with an **observable end state the reader can check themselves**, in the
order below, with the five answers written into it so the next session need not ask again. Name
what will not work for them and why — no photographs means no page channel, no writing directory
means hypotheticals only — rather than discovering it halfway. Then stop and let them read it.
Do not start building until they say so.

The finish line is concrete: they run one command and a lesson prints, drawn from *their* books,
citing a passage they can open. Anything that does not move toward that is not on the plan.

## Ask these five things first

Four of the five have no default you can guess, and every one changes the plan.

1. **Where are the marks?** A Kindle plugged in has `documents/My Clippings.txt`. The Kindle app
   mails an *Export Notes* HTML file per book. Readwise exports CSV. Apple Notes holds many
   people's book notes, including photographed pages and Pencil handwriting. Ask them to look
   rather than remember — people are routinely wrong about this. **The device file carries no
   colour**; the HTML and CSV do. If colour matters to them, that decides the format.
2. **Are there photographed pages?** Pages of paper books marked by hand. On macOS, local OCR
   works with no key and no network. Elsewhere the pipeline still runs but page text must come
   from somewhere else — say so now, not at step five.
3. **Where do they write?** Any directory of their own prose. This is `READER_SURFACES`. Without
   it, every lesson is a hypothetical and the "what you never used" report says everything was
   never used — true and useless. If they have none, say what they lose and proceed.
4. **Where should a lesson arrive?** Terminal, a file, or a phone push. **Start at the terminal
   for a week whatever they answer.** A channel someone learns to ignore is worse than one they
   never set up.
5. **Does their vault path contain a comma?** Not an idle question. The agents' permission rules
   are comma-separated with no escape, so a vault named `Books (2024), notes` breaks them. All
   three runners refuse such a path and say why. Spaces and parentheses are fine — Obsidian's own
   default path has both, and it is not a problem.

## Two things to clear before anything runs, on macOS

- **Full Disk Access**, if they use the Apple Notes on-ramp. Reading the Notes database is gated
  by macOS, and a refusal there looks like a missing file. It is granted in System Settings →
  Privacy & Security → Full Disk Access, for the terminal or the app running you. **This is a
  GUI action you cannot perform: stop, hand it back, and wait.**
- **A Python 3.11 or newer somewhere on the machine.** macOS ships 3.9. `quickstart.sh` finds a
  newer one and builds `.venv/` itself; the first run installs two packages, so it needs network
  once.

## The sequence

Copy this, change the three paths, and it is the plan's spine. Each stage is worthless without the
one before it, so do not reorder.

```bash
# 0. Prove it on the fixture that ships with the repo, before touching their library.
bash tests/run.sh                      # cheapest possible check that this machine is sane
bash quickstart.sh                     # ~1 minute, no agent, no account
bash quickstart.sh --with-claude       # adds distill + one lesson; minutes, and costs tokens

# 1. Clear the fixture's output, or its book ends up in their vault.
source .venv/bin/activate
rm -rf out/
export RG_OUT="$PWD/out"
export VAULT="/path/to/their/vault"            # no comma in it
export READER_SURFACES="/path/to/their/writing" # colon-separated for several

# 2. Their marks. Pick the ONE format they actually have.
python -m capture.kindle clippings "/Volumes/Kindle/documents/My Clippings.txt" --out "$RG_OUT/kindle-highlights.json"
#   or: python -m capture.kindle html <Export Notes>.html --out "$RG_OUT/kindle-highlights.json"
#   or: python -m capture.kindle readwise <export>.csv    --out "$RG_OUT/kindle-highlights.json"
#   several sources in one call are merged and de-duplicated: `clippings <file> html <file>`
#   --diagnose works on the clippings format ONLY — one line per record and a tally of drops
#   --previous <last run's json> diffs the counts against the previous run, on every format

# 3. Photographed pages, if any. Apple Notes folder, or a folder of images per book.
#    NO --library on this first pass: it names the vault's books/ directory, which step 4 has not
#    built yet, and a library that is not there cannot recognise a typed note as being about a
#    book. Step 6 runs it again with --library, once there is a shelf to match against.
python capture/notes/apple_notes.py --folder "Book Notes" --dry-run
python capture/notes/apple_notes.py --folder "Book Notes" --pages "$RG_OUT/pages"
python capture/pages/manifest.py --pages "$RG_OUT/pages" --out "$RG_OUT/manifest.json"
python capture/pages/ocr.py --dir "$RG_OUT/pages" --out "$RG_OUT/ocr.jsonl" --engine vision   # stub off macOS
python corpus/build_bookcorpus.py      # REQUIRED whenever there are pages — see the warning below

# 4. One corpus, then one node per book.
python corpus/merge_corpus.py
python vault/build_nodes.py --vault "$VAULT" --corpus "$RG_OUT/merged"

# 5. Now there is a shelf: re-export the notes so typed notes file under their books, not as
#    loose wisdom, and rebuild. Compare the two reports — the difference is the point of this step.
python capture/notes/apple_notes.py --folder "Book Notes" --library "$VAULT/books" --pages "$RG_OUT/pages"
python corpus/build_bookcorpus.py && python corpus/merge_corpus.py
python vault/build_nodes.py --vault "$VAULT" --corpus "$RG_OUT/merged"

# 6. Distil three or four books they know well. Slugs are kebab-case, without the extension:
#    ls "$RG_OUT/merged" | sed 's/\.json$//'
bash agents/distill/distill-one.sh <slug>

# 7. What they never used. Seconds, no model.
python agents/librarian/candidates.py

# 8. A lesson, by hand, several times across a week before scheduling anything.
bash agents/tutor/run.sh --channel stdout
#   later: --channel file needs TUTOR_FILE; --channel ntfy needs TUTOR_NTFY_URL (and optionally
#   TUTOR_NTFY_TOKEN). agents/tutor/cron.example and launchd.example.plist ship with paths to edit.

# 9. Once distillations exist: the applied index, a proposer and a skeptic that refuses by default.
bash agents/praxis/praxis-one.sh
```

**`--out` is required on the two `capture/pages/` scripts and they do not read `RG_OUT`.** Pass it
explicitly, as above. `VAULT`, `RG_OUT` and `READER_SURFACES` are read from the environment
everywhere else.

**Skipping `corpus/build_bookcorpus.py` silently zeroes the photographed-pages channel.** The merge globs
a directory that does not exist yet, which returns nothing without erroring. That is the exact
failure this project was built around, reproduced by skipping one line.

**After step 2, stop and reconcile the counts** before going on. Does the number of books and
highlights match what they expect? The plausibility report prints the sorted count vector first,
on every format, which is the check that once caught an extractor returning a quarter of the data
while reporting success. `--diagnose` accounts for every dropped record by reason but works on the
clippings format only; `--previous` diffs against the last run on any format. The merge drops any
book with no highlights and fewer than three pages. A disagreement is the finding, not a rounding
error.

## Decisions already made — do not re-litigate

The evidence is in the docs, and reopening these usually ends in the same place.

- **There is no cross-book knowledge graph, and building one is not an improvement.** It was
  built, then attacked by adversarial verifiers across 28 candidate relationships: 27 refutations
  stand, zero verified. `docs/08-LIBRARIAN.md`. If your reader asks for one, show them that page.
- **A candidate from the matcher is a question, not a finding** — roughly five of twenty-one were
  real. Never present candidates as discoveries.
- **The fidelity tag on a distillation is load-bearing.** It says how much of the book the agent
  actually saw. Do not remove it to tidy the output.
- **The Tutor composes; the runner decides.** The model writes two files and stops; every rule is
  checked in code. Do not "simplify" that by letting the model send.
- **Nothing here uploads a library anywhere.** Keep it that way.

## Mistakes that cost a session

- **Do not build the venv yourself.** `python3` on macOS is 3.9 and the refusal that follows is
  confusing. Let `quickstart.sh` find an interpreter.
- **A refusal is the answer, not an obstacle.** Every stage refuses rather than exiting cleanly on
  empty input, deliberately. When you see one, the input is wrong; do not work around it.
- **`quickstart.sh --with-claude` can legitimately end without a lesson.** With one fixture book
  and no writing of the reader's own, the Tutor's floor rejects everything and says so. That is a
  pass. Do not debug it.
- **Photographed pages and e-reader highlights are not the same sample.** A zero in one channel
  never means the reader did not engage. `docs/reference/PITFALLS.md` Family 1 is the case where
  that assumption produced a confident wrong answer about a chapter marked twenty-two times.
- **The Tutor's ledger does not exist until a lesson has been delivered**, so an installation that
  has never worked has nowhere to write its failure rows. Redirect the output somewhere durable
  until they have seen a lesson arrive.
- **Read `docs/reference/KNOWN-GAPS.md` before you promise anything.** It states, in measured
  terms, what the guards do not cover. Do not tell your reader a guarantee this project does not
  make.
