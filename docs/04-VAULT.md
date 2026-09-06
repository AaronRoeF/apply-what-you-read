# 04 — The vault: one markdown node per book

## Why markdown in a folder, not a database

Because agents grep. A database needs a client, a schema, and a tool call; a directory of
markdown files needs none of those. Every downstream consumer — an agent, a script, you with
an editor open — reads the same substrate directly, and a `[[wikilink]]` between two files is
a relationship any of them can follow.

The vault can be an [Obsidian](https://obsidian.md) vault, in which case you get backlinks,
graph view, and search for free. It can also be a plain folder. Nothing in this pipeline
requires Obsidian; a few things are nicer with it.

## Layout

```
<vault>/
  books/                 one node per book, generated — never hand-edit the generated part
    meditations.md
    _orphaned/           nodes whose book left the corpus, dated; never deleted
  distill/
    distill-meditations.md   written by the distill skill; transcluded into the node
  praxis/                (v0.2) the applied index — lessons with citations
  READER.md              (optional) your colour key and anything else agents should know
```

Point the builder at it: `python vault/build_nodes.py --vault <vault>` or `export VAULT=<vault>`
(with the quickstart's venv active: `source .venv/bin/activate`). The builder will not guess
where your vault is.

## The node contract

The example below is from a library with coloured highlights and a distillation already
written. The quickstart's fixture node shows `kindle_colors: []` (the clippings file carries
no colour) and `distilled: false` (nothing distilled yet); every key is the same.

```yaml
---
name: "Meditations"
type: book
source: apply-what-you-read
asin: x01e167f36            # synthetic (prefixed x) when the source carried no Amazon id
author: "Marcus Aurelius"
kindle_highlights: 35
typed_notes: 5
kindle_colors: [Yellow:30, Pink:5]
pages_captured: 5
pages_catalogued: 0
pages_annotated: 0
highlight_colors: null      # null = no page catalogued yet; [] = catalogued, none found
marks: null
distilled: true
tags: [book, reading]
related: []                 # reserved for the Librarian
---
```

Then `# Title`, a `## Source` section with the counts, a rule, and either the transcluded
distillation or `*Not yet distilled.*`.

Four fields are yours, not the builder's: `related`, `outcome`, `applied_in`, `status`. Edit
them by hand and they survive every rebuild. Everything else is regenerated from the corpus.
Only `related` is present by default; add the other three to the frontmatter when you have
something to say. They are free-form, but the convention is: `outcome:` one line on what
reading the book changed; `applied_in:` where (a project, a decision, a file); `status:` one of
`reading`, `keep`, `retire`. The Librarian (v0.3) writes `related:` and nothing else.

## The rules the builder enforces

Each is a defect that happened, not a preference. They are all tested (`tests/test_build_nodes.py`).

| rule | what it prevents |
|---|---|
| **Membership is decided in one place.** A book is a node iff it is in the merged corpus with at least one highlight or one page. | Two lists deciding what counts as a book — the bug that silently dropped the three largest sources in the reference corpus. |
| **An empty corpus refuses.** | A missing corpus path producing zero nodes, after which the orphan sweep would move *every* existing node aside. This one was found by reading the code, one line before it would have fired. |
| **Orphans move, never delete.** `books/_orphaned/<name>.<date>.md`. | Losing a node with hand-authored fields because a slug changed. |
| **Hand-authored fields survive.** | Your `related:` links vanishing on the next rebuild. |
| **`null` is not `[]`.** | An unexamined page looking like a clean one. |
| **Write only on change.** | Every rebuild touching every file, so "recently modified" means nothing. |
| **Basename collisions refuse.** A second `<slug>.md` anywhere in the vault → that book is skipped, loudly, exit 1; the rest are written. | `[[slug]]` resolving to the wrong file. Forty-seven such collisions were cleaned up in the reference vault; the `distill-` prefix on distillations exists for the same reason. |
| **The distillation is joined, never written.** | The builder modifying your distillation, or inlining its frontmatter into the node. |
| **An unwritable vault spools.** `$RG_OUT/spool/books/`, exit 3. | Output lost silently. Losing durable output is the failure this whole pipeline exists to prevent. |

## Rebuild order, and why it is not a style preference

```
capture  →  corpus/build_bookcorpus.py  →  corpus/merge_corpus.py  →  vault/build_nodes.py
```

A stale derived artifact does not sit inert; it actively corrupts everything downstream that
trusts it. Always rebuild forward from the stage you changed. `01-HOW-IT-WORKS.md` §6.

## Your colour key

If you know what your highlight colours mean, say so in `<vault>/READER.md`:

```markdown
## Colour key
- Yellow: default
- Pink: the line I would quote
- Blue: procedures and lists
```

A declared key outranks any inference an agent could make from colour frequency. Without one,
agents are told to capture colour and build no semantics on it — on the reference corpus,
non-default colours clustered by reading session at least as often as by meaning.

## If you use Obsidian

- Embeds and links resolve by bare filename across the whole vault. That is why basenames
  must be unique and why distillations carry the `distill-` prefix.
- Keep `out/` outside the vault. Working files are not notes.
- A node's `## Source` section links to the notes-app note a page came from, when there is
  one (`- [[That Note]] — 5 pages captured`). With the folder-per-book input there is nothing
  separate to link to, so the line is plain text: `- 5 photographed pages`.
- [obsidian-mcp](https://github.com/AaronRoeF/obsidian-mcp) lets Claude Code search and read
  the vault directly, which the Tutor (v0.2) uses for its "was this note opened" signal.
