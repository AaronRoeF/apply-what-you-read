# The lesson contract

One record per idea you have actually used. This is the shape everything else agrees on: the
qualifier proposes records, the adjudicator rejects most of them, the Tutor draws from what
survives, and `praxis.md` is a rendering of the file — never the other way round.

Every example in this repository uses the public-domain fixture, and that is a rule rather than a
convenience: a worked example is the most-read text in any project, and one built from a real
record publishes whatever that record was about.

```json
{
  "id": "px:8f2a91c4",
  "claim": "Take the ten minutes before the first meeting rather than looking for a quieter week.",
  "citation": "Meditations loc 269 🩷",
  "argument": "Marcus argues the retreat people seek elsewhere is available at any moment, and that seeking it elsewhere is itself the avoidance.",
  "application": {
    "kind": "current",
    "evidence": ["journal/2026-03-11.md:8"],
    "what": "Named it 'the retiring' and did it before the morning call twice this week."
  },
  "adjudication": {"verdict": "applied", "by": "skeptic", "checked": "2026-03-12",
                   "note": "Both quotes verified on disk at the cited lines."}
}
```

## The fields, and why each one is required

| field | rule |
|---|---|
| `claim` | one sentence, in your own words, that could be acted on. Not a summary of the book. |
| `citation` | work + location, or `file:line`. **No citation, no record.** |
| `argument` | what the author is actually arguing there, so the claim is not a misreading |
| `application.kind` | exactly one of `current`, `past`, `hypothetical` |
| `application.evidence` | file paths, with line numbers where possible. **Empty only for `hypothetical`** |
| `adjudication.verdict` | `applied`, `rejected` or `unverified` — set by the skeptic, never the proposer |

## Two rules that are not obvious

**A `hypothetical` is a real record.** Without your own writing to check against, every idea is
uncorroborated by construction, and a store that only accepts corroborated records would be empty
for a new reader and would look like a broken tool rather than an honest one. Hypotheticals are
labelled, never counted as use, and never scored on downstream edits.

**The proposer never adjudicates.** The agent that finds candidates is optimistic by design: it is
looking. A second pass, whose only job is to refuse, re-reads every citation on disk and rejects
anything it cannot verify at the line given. On the reference library the two passes disagreed
often enough that collapsing them into one would have doubled the store and halved its meaning.
