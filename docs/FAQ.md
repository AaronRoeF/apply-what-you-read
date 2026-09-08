# FAQ

**I don't use a Kindle.** The photographed-pages channel is for you: `03-PHOTOS-AND-NOTES.md`.
Any book, paper or screen, one folder of photos per book. If your reader exports highlights in
some other format, the record it has to hit is one small dataclass
(`capture/kindle/schema.py`) and a parser is about a hundred lines; the three that ship are
the templates.

**Linux?** Everything runs except Apple Vision OCR — CI runs the suite and the quickstart on
Ubuntu. For photographed pages use the stub engine with text you already have, or implement
the Tesseract seam (`capture/pages/ocr.py`).

**Windows?** The Python stages run. The bash scripts (`quickstart.sh`, `tests/run.sh`, the
distill runner) need WSL or Git Bash, and the Kindle recipe's `/Volumes/Kindle/...` path is
the macOS mount — yours will be a drive letter. Untested; a report is welcome.

**Does it upload my highlights anywhere?** The pipeline through the vault: no. Nothing in it
opens a network connection; the Kindle parsers read files you already have, and `out/` and your
vault are git-ignored by directory. Distill and the agents: yes, by design — they run through
the Claude Code CLI, which sends what the agent reads to Anthropic's API under your own account.
For one distillation that is the prompt, that book's merged record (its highlights and page
text), your reader-context file verbatim, and whatever the agent opens while searching
`READER_SURFACES`. `05-DISTILL.md` lists it exactly. The reference crawler (v0.3) drives your
own logged-in browser and never sees a credential.

**What is `READER_SURFACES`?** A colon-separated list of directories that hold your own
writing — a journal, project notes, decisions. The distill agent greps them for distinctive
phrases from your highlights to find receipts: places an idea was actually used. Leave it
unset and every idea is reported as uncorroborated, honestly. Only point it at directories you
would show a colleague; the agent reads whatever it finds there.

**Is this a summarizer?** No. A summary recreates the table of contents. Distill takes the ~20%
that carries a book, tags how much of the book it actually saw, and maps *your* marks onto it
— including which marked ideas left a receipt in your own writing. `05-DISTILL.md`.

**Why did the corroboration section find nothing?** Either `READER_SURFACES` was empty (say so
in the run; it is by construction then) or the ideas genuinely left no receipt in your writing.
The second is a finding, not a failure: those ideas are still available to you, and that is what
Praxis and the Tutor (v0.2) are for.

**Can I use it without Obsidian?** Yes. The vault is a folder of markdown files. Obsidian gives
you backlinks and graph view on top; nothing depends on it. `04-VAULT.md`.

**Can I use it without Claude Code?** The pipeline through the vault, yes — it is Python and
bash. Distill, Praxis, the Tutor and the Librarian are prompts plus small runners built around
the `claude` CLI. Another agent runtime could run the prompts; the runners assume `claude -p`.

**Is scraping my own Kindle notebook allowed?** Read your provider's terms; they vary and they
are your responsibility. The reference crawler (v0.3) is designed so that the question is as
small as it can be: it runs only inside a browser session you logged into yourself, it never
handles a password, cookie, or token, it retrieves only annotations you made, and it never
redistributes anything. The three file-format parsers involve no such question at all.

**What about copyrighted text in my vault?** Your highlights are your selections from books you
own, kept on your own disk for your own use. This repository ships none of them — the only book
text in it is a public-domain excerpt with its provenance stated on the file
(`fixtures/meditations/SOURCE.md`) and a test that enforces it. Do not commit `out/` or your
vault to a public repository.

**The clippings parser dropped some highlights. Why?** Three reasons, all on purpose and all
reported by `--diagnose`: exact duplicates (the device re-synced), superseded shorter versions
(you re-selected a longer span later; the longer one wins), and bookmarks (no text). If a
highlight is genuinely missing, run `python -m capture.kindle clippings … --diagnose` and look
for `UNPARSED` — then open an issue with that line; the record grammar has variants the fixture
may not cover.

**My clippings file has the same book under two slightly different titles.** Kindle writes the
title as the file has it, and editions differ. Books group by exact title + author; merge the
two nodes by hand for now, or normalise the titles in the file. A title-alias table is a
reasonable contribution.

**Why is `kindle_colors` empty?** `My Clippings.txt` carries no colour. The app's Export Notes
HTML and a Readwise CSV do; parse one of those (or both — sources merge and dedupe).

**How big can this get?** The reference corpus is 88 books, 4,425 highlights and 798
photographed pages; every stage is a linear pass over files and the whole rebuild takes
seconds without OCR. OCR is the slow part: Apple Vision runs at a few images per second.

**Something returned nothing and looked fine.** That is the failure class this project is most
careful about, and the reason for the plausibility line, the empty-parse errors, the stub
engine's refusal to fake a success, and the runner that fails when the agent exits clean
without writing. If you find another silent zero, `reference/PITFALLS.md` is where it belongs —
open an issue with the sorted-counts line.

**I keep my book notes in Apple Notes, with photos and Pencil handwriting. Does that work?**
On macOS: an exporter reads one Notes folder from a read-only copy of the database and
carries the text Apple already recognised — its own OCR of each photo and the handwriting
recogniser's text for Pencil pages — into the photographed-pages channel, with a watcher that
keeps the folder flowing. Start with `--dry-run`, which writes nothing and names every note. See
[03-PHOTOS-AND-NOTES](03-PHOTOS-AND-NOTES.md), last section. Off macOS, export the photos to a
folder per book and follow the rest of that document.
