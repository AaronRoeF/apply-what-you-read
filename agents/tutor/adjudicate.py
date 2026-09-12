#!/usr/bin/env python3
"""agents/tutor/adjudicate.py — score the ledger, and turn the loop off when it stops landing.

A lesson-a-day system has one failure mode that matters: it becomes wallpaper. You keep receiving,
you stop reading, and nothing says so. This closes that, on two rules:

  * ONE PASSIVE CHANNEL, NEVER A QUESTION. A lesson counts as landed if the reader's own writing
    cites its idea or its citation within the check-due window. The reader is never asked "did
    this help?" — the answer is unreliable and the asking is itself a cost. A second channel,
    whether the cited file was opened, is designed and NOT built; the ledger keeps its column
    empty rather than pretending.
  * UNMEASURED IS NOT SILENT. A lesson this cannot score — a past or hypothetical application,
    or any lesson when no writing directory was given — resolves to `unmeasured` and does not
    advance the streak. Treating "I cannot tell" as "it failed" turned the switch below into a
    timer that fired in week three regardless of what the loop was worth.
  * SEVEN CONSECUTIVE SILENT LESSONS TURN THE LOOP OFF, LOUDLY. Not quieter, not less often: off,
    with the reason written into the ledger, until the reader turns it back on. A channel that
    gets skimmed is a channel where this dies quietly, and dying quietly is the thing to prevent.

`edit` is scored only on rows whose kind is `current`. A past or hypothetical lesson cannot
produce a downstream edit, so scoring it that way would manufacture silence; on those rows `edit`
is `n/a` and `opened` alone decides.

  python agents/tutor/adjudicate.py --vault ~/vault [--surfaces DIR:DIR] [--apply]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re
import sys

ROW_RE = re.compile(r"^\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\|(?P<rest>.*)\|\s*$")
KILL_AFTER = 7


def parse_rows(text: str) -> list[dict]:
    rows = []
    for i, line in enumerate(text.splitlines()):
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        rows.append({"line": i, "raw": line, "date": cells[0], "item": cells[1], "citation": cells[2],
                     "due": cells[3], "edit": cells[4], "opened": cells[5], "outcome": cells[6],
                     "kind": cells[7]})
    return rows


# WHAT THIS PIPELINE WROTE, AND THEREFORE WHAT CANNOT CORROBORATE THE READER. Kept as one
# constant because the three components that need it had drifted to three different answers:
# run.sh refused derived files, candidates.py refused them, and this adjudicator refused nothing,
# so pointing READER_SURFACES at the vault let tutor-journal.md — which holds every lesson
# verbatim — score every lesson, and the kill switch could never fire. A test asserts run.sh
# still agrees with this list.
PIPELINE_DIRS = {"books", "distill", "praxis", "out", "_orphaned"}
PIPELINE_FILES = {"tutor-journal.md", "tutor-ledger.md"}


def is_pipeline_output(p: pathlib.Path, root: pathlib.Path) -> bool:
    """Is this file something the pipeline produced, rather than something the reader wrote?
    Judged RELATIVE to the reader's own root, so a vault living under ~/books/ or ~/out/ is not
    mistaken for the pipeline's own directories."""
    try:
        rel = p.resolve().relative_to(root.expanduser().resolve())
    except (ValueError, OSError):
        return False
    return (bool(set(rel.parts[:-1]) & PIPELINE_DIRS)
            or p.name.startswith("distill-") or p.name in PIPELINE_FILES)


def cites(row: dict, surfaces: list[pathlib.Path], since: dt.date) -> str:
    """Did the reader's own writing pick this up? A citation string or a distinctive fragment of
    the item, appearing in a file modified after the lesson was sent."""
    needles = [n.strip().lower() for n in re.split(r"[·|]", row["citation"]) if len(n.strip()) > 8]
    frag = row["item"].split(":", 1)[-1].strip().lower()
    if len(frag) > 20:
        needles.append(frag[:60])
    if not needles:
        return ""
    for d in surfaces:
        if not d.exists():
            continue
        for p in d.rglob("*.md"):
            if is_pipeline_output(p, d):
                continue
            try:
                if dt.date.fromtimestamp(p.stat().st_mtime) < since:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            for n in needles:
                if n in text:
                    return str(p)
    return ""


def adjudicate(ledger_text: str, surfaces: list[pathlib.Path], today: dt.date) -> dict:
    rows = parse_rows(ledger_text)
    resolved, newly = [], []
    for r in rows:
        if r["outcome"]:
            resolved.append(r)
            continue
        try:
            due = dt.date.fromisoformat(r["due"])
        except ValueError:
            continue
        if due > today:
            continue                       # still open; not yet a silence
        sent = dt.date.fromisoformat(r["date"])
        hit = cites(r, surfaces, sent)
        if hit:
            r["edit"], r["outcome"] = hit, "landed"
        elif r["kind"] == "current" and surfaces:
            r["edit"], r["outcome"] = "", "silent"
        else:
            # UNMEASURED IS NOT SILENT, and conflating them turned the kill switch into a timer.
            # A past or hypothetical lesson cannot produce a downstream edit by construction, and
            # with no surfaces to search there is nothing to find for any kind. Scoring those as
            # silence meant a reader with no writing directory — whose lessons are ALL
            # hypothetical, as the docs tell them — accumulated seven silences and had the loop
            # shut itself off in the third week, whatever it had been worth to them.
            r["edit"], r["outcome"] = "n/a", "unmeasured"
        newly.append(r)
        resolved.append(r)
    tail = [r for r in resolved if r["outcome"] in ("landed", "silent")]
    streak = 0
    for r in reversed(tail):
        if r["outcome"] == "silent":
            streak += 1
        else:
            break
    return {"rows": len(rows), "resolved_now": newly, "silent_streak": streak,
            "kill": streak >= KILL_AFTER,
            "landed": sum(1 for r in tail if r["outcome"] == "landed"),
            "silent": sum(1 for r in tail if r["outcome"] == "silent"),
            "unmeasured": sum(1 for r in newly if r["outcome"] == "unmeasured")}


def rewrite(text: str, result: dict) -> str:
    lines = text.splitlines()
    for r in result["resolved_now"]:
        cells = [r["date"], r["item"], r["citation"], r["due"], r["edit"], r["opened"], r["outcome"], r["kind"]]
        lines[r["line"]] = "| " + " | ".join(cells) + " |"
    out = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    if result["kill"]:
        # The anchored pattern this used to carry did not match `status: on   # back on 2026-09-01`,
        # a line the off_reason text itself invites the reader to write. The run then printed
        # TUTOR LOOP: OFF, wrote the ledger, and left the frontmatter saying on, so the loop kept
        # sending. A kill switch that reports a flip it did not make is the loudest possible lie in
        # the one place this design says must never be quiet. Match the whole line, then PROVE it.
        replacement = (f"status: off\noff_reason: \"{KILL_AFTER} consecutive lessons landed nowhere "
                       f"(adjudicated {dt.date.today().isoformat()}); the loop turns itself off rather "
                       f"than becoming wallpaper. Set status back to on when you want it again.\"")
        out = re.sub(r"^status:\s*on\b[^\n]*$", lambda _m: replacement, out, count=1, flags=re.M)
        if not re.search(r"^status:\s*off\b", out, re.M):
            raise ValueError(
                "the kill condition fired but `status: off` could not be written to the ledger "
                "frontmatter, so THE LOOP IS STILL ON. Set `status: off` by hand.")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault", default=os.environ.get("VAULT", ""))
    ap.add_argument("--surfaces", default=os.environ.get("READER_SURFACES", ""))
    ap.add_argument("--apply", action="store_true", help="write the outcomes back (default: report only)")
    ap.add_argument("--today", default="")
    a = ap.parse_args(argv)
    if not a.vault:
        print("adjudicate: --vault is required", file=sys.stderr)
        return 2
    ledger = pathlib.Path(a.vault).expanduser() / "tutor-ledger.md"
    if not ledger.exists():
        print(f"adjudicate: no ledger at {ledger} — nothing has been sent yet", file=sys.stderr)
        return 2
    text = ledger.read_text(encoding="utf-8")
    surfaces = [pathlib.Path(d).expanduser() for d in a.surfaces.split(":") if d.strip()]
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    res = adjudicate(text, surfaces, today)

    print(f"adjudicate: rows={res['rows']} resolved-now={len(res['resolved_now'])} "
          f"landed={res['landed']} silent={res['silent']} unmeasured={res['unmeasured']} "
          f"silent-streak={res['silent_streak']}")
    if res["unmeasured"] and not res["landed"]:
        print(f"  {res['unmeasured']} lesson(s) could not be scored at all — they were past or "
              f"hypothetical applications, or there was no writing to search. That is 'I cannot "
              f"tell', not 'it failed'. Point --surfaces at your own writing to make this loop "
              f"measurable.")
    for r in res["resolved_now"]:
        print(f"  {r['outcome']:7s} {r['date']}  {r['item'][:60]}")
    if a.apply:
        try:
            new = rewrite(text, res)
        except ValueError as e:
            print(f"adjudicate: REFUSED — {e}", file=sys.stderr)
            return 3
        ledger.write_text(new, encoding="utf-8")

    if res["kill"]:
        # Only claimed after the write actually happened, so the banner cannot describe a state
        # the ledger is not in.
        if a.apply:
            print(f"\n  TUTOR LOOP: OFF — {res['silent_streak']} consecutive lessons landed nowhere.\n"
                  f"  A channel that gets skimmed is a channel where this dies quietly, so it stops\n"
                  f"  instead. Set `status: on` in {ledger} when you want it back.")
        else:
            print(f"\n  TUTOR LOOP: WOULD TURN OFF — {res['silent_streak']} consecutive lessons "
                  f"landed nowhere.\n  Nothing was written; pass --apply to make it so.")
    if a.apply:
        print(f"  wrote {ledger}")
    else:
        print("  (report only — pass --apply to write the outcomes back)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
