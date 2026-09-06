"""capture/kindle/plausibility.py — the independent check on an extractor's own output.

Any extractor whose failure mode is an empty result needs a check that does not trust the
extractor's exit code. The sorted per-book count vector is that check: it is a print statement,
and it is the only reason the two silent-zero crawler bugs were ever found
(docs/02-KINDLE.md). Read it every run.

Flags (printed, never fatal — they are for the reader to read):
  PAGE_CAP_SUSPECTED   >= 3 books with counts clustered just under a round number
                       (the 92–97 signature of a page cap wearing a costume)
  ZERO_VS_NULL         books present with zero annotations — "looked, found nothing" is
                       distinct from "never looked"; both are listed so neither hides
  RECRAWL_DIFF         per-book deltas against a previous run (nondeterministic truncation
                       shows up as two runs that disagree)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field


@dataclass
class Report:
    counts: dict[str, int]
    flags: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    def print(self, out=None):
        out = out or sys.stdout
        for l in self.lines:
            print(l, file=out)


def _counts(doc: dict) -> dict[str, int]:
    return {b["title"]: int(b.get("n", len(b.get("annotations", [])))) for b in doc.get("books", [])}


def check(doc: dict, previous: dict | None = None, out=None) -> Report:
    counts = _counts(doc)
    rep = Report(counts)
    vec = sorted(counts.values())
    rep.lines.append(f"plausibility: books={len(counts)} annotations={sum(vec)} sorted counts = {vec}")

    buckets: dict[int, list[int]] = {}
    for c in vec:
        for base in (25, 50, 100, 200, 500, 1000):
            m = ((c // base) + 1) * base
            if 1 <= m - c <= 8:   # the measured signature was a 92–97 band under 100
                buckets.setdefault(m, []).append(c)
                break
    for m, cs in sorted(buckets.items()):
        if len(cs) >= 3:
            rep.flags.append("PAGE_CAP_SUSPECTED")
            rep.lines.append(f"  PAGE_CAP_SUSPECTED: {len(cs)} books at {cs} sit just under {m} — unrelated books do "
                             f"not agree on a count; verify the continuation-token selector on a SECOND page")
    zeros = [t for t, c in counts.items() if c == 0]
    if zeros:
        rep.flags.append("ZERO_VS_NULL")
        rep.lines.append(f"  ZERO_VS_NULL: {len(zeros)} book(s) with zero annotations (looked, found nothing): "
                         f"{zeros[:5]}{' …' if len(zeros) > 5 else ''}")
    if previous is not None:
        prev = _counts(previous)
        deltas = {t: (prev.get(t), counts.get(t)) for t in set(prev) | set(counts) if prev.get(t) != counts.get(t)}
        if deltas:
            rep.flags.append("RECRAWL_DIFF")
            rep.lines.append(f"  RECRAWL_DIFF: {len(deltas)} book(s) changed vs previous run: "
                             + ", ".join(f"{t!r} {a}->{b}" for t, (a, b) in sorted(deltas.items())[:8]))
        else:
            rep.lines.append("  re-run identical to previous run")
    if not rep.flags:
        rep.lines.append("  no plausibility flags")
    rep.print(out)
    return rep
