# agents/distill — the book, reduced to the part you'll use

Three ways to run the same method (Thomas Dev Brown's *How To Read A Book A Day*, enforced
as five moves with a fidelity tag on line one):

| how | when | what runs |
|---|---|---|
| **interactive** — `distill <book>` in Claude Code | one book, you in the loop | `skills/distill/distill.md` |
| **headless** — `VAULT=… agents/distill/distill-one.sh <slug>` | one book, no conversation | `DISTILL_PROMPT.md` via `claude -p` |
| **the library** — Workflow `distill-library.workflow.js` | every book, one agent each | the same prompt, over a frozen manifest slice |

All three write `$VAULT/distill/distill-<slug>.md`, which `vault/build_nodes.py` transcludes
into the book's node on the next rebuild. The builder never writes into that file.

## The prompt's three ground rules

They are in `DISTILL_PROMPT.md` and they are not style. Each was learned on a real corpus:

1. **Rarity is not significance.** Typed notes are ~1% of marks because typing on an
   e-reader is annoying. A margin note is a reaction, not a commitment. Colour clusters by
   reading session; a declared colour key in `$VAULT/READER.md` outranks any inference.
2. **Corroboration is the signal.** A mark matters if it changed something outside the
   book, and that is observable: grep the reader's own writing (`$READER_SURFACES`) for
   distinctive multi-word phrases. Single common words matched 782 files once.
3. **Never infer a gap from missing data.** `catalogued: false` means nobody looked. Absence
   in one channel is not absence of interest — one "never engaged" finding was refuted by
   twenty-two marks in the other channel.

## Running the library

```bash
python corpus/merge_corpus.py                       # writes out/merged/_manifest.json
shasum -a 256 out/merged/_manifest.json             # freeze: this hash goes into args
python - <<'EOF'
import json; rows = json.load(open("out/merged/_manifest.json"))
print(json.dumps([{"slug": r["slug"], "book": r["book"]} for r in rows[0:20]]))   # a slice
EOF
```

Then, in Claude Code, run the Workflow with `args = { manifest, sha256, books: <slice>, vault,
out, reader_context, reader_surfaces }`. Every agent re-hashes the manifest before working and
aborts on mismatch. To correct the input mid-run, stop, fix, re-freeze, and pass the **new**
hash — never edit the manifest an agent is reading. Re-running with identical args resumes:
finished agents are cached.

Without a Workflow runner, loop the headless script (with the quickstart's venv active:
`source .venv/bin/activate`):

```bash
for slug in $(python -c 'import json;print(" ".join(r["slug"] for r in json.load(open("out/merged/_manifest.json"))))'); do
  VAULT=/path/to/vault agents/distill/distill-one.sh "$slug" --context reader-context.md || echo "FAILED $slug"
done
```

`distill-one.sh` exits non-zero if the agent finishes without writing the file. A clean exit
with no output is the failure that check exists for.

## What "corroborated" means

`corroborated: true` — at least one marked idea left a receipt in the reader's own writing,
cited file:line. `partial` — some did. `false` — none did, or `$READER_SURFACES` was empty.
None of these is a grade. An uncorroborated book is a book whose ideas are still available.
