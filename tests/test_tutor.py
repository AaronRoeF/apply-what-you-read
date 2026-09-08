"""The Tutor: the model composes, the runner decides.

Every rule the prompt states is checked here against a stub `claude` that writes a lesson on
purpose — a good one, and then each bad one in turn. The point of the compose-only split is that
these are testable at all; a prompt-only rule can only be hoped for.
"""
from __future__ import annotations

import json
import os
import pathlib
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "agents" / "tutor" / "run.sh"

GOOD_MSG = """APPLY WHAT YOU READ LESSON

HELD: "It is in thy power to retire into thyself" — Meditations, loc 269, 🩷. Marcus is arguing
that the retreat people look for in the countryside is available anywhere, at any moment.

WHY HELD: Marked two years ago, never spent since.

APPLY: Suppose you take ten minutes before the first meeting tomorrow, door shut, no inbox.

(citation: Meditations loc 269 🩷)
"""

GOOD_META = {"work": "Meditations", "location": "loc 269", "citation": "Meditations loc 269",
             "application_kind": "hypothetical", "evidence": [],
             "held": "It is in thy power to retire into thyself", "colour": "pink",
             "slug": "meditations"}


def _stub(tmp_path: pathlib.Path, msg: str | None, meta: dict | None, rc: int = 0) -> pathlib.Path:
    """A fake `claude` that writes whatever the test wants the agent to have composed."""
    out = tmp_path / "out" / "tutor"
    body = ["#!/usr/bin/env python3", "import json, os, pathlib, sys",
            f"out = pathlib.Path({str(out)!r}); out.mkdir(parents=True, exist_ok=True)"]
    if msg is not None:
        body.append(f"(out / 'message.txt').write_text({msg!r}, encoding='utf-8')")
    if meta is not None:
        body.append(f"(out / 'meta.json').write_text(json.dumps({meta!r}), encoding='utf-8')")
    body.append(f"sys.exit({rc})")
    p = tmp_path / "claude"
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def _run(tmp_path, stub, *args, env_extra=None):
    env = {**os.environ, "VAULT": str(tmp_path / "vault"), "RG_OUT": str(tmp_path / "out"),
           "CLAUDE_BIN": str(stub), "TUTOR_TIMEOUT_SECS": "30",
           "TUTOR_LOCK": str(tmp_path / "lock"), **(env_extra or {})}
    (tmp_path / "vault").mkdir(exist_ok=True)
    return subprocess.run(["bash", str(RUN), *args], capture_output=True, text=True, env=env)


# ── the happy path ───────────────────────────────────────────────────────────────────────────

def test_a_good_lesson_is_printed_recorded_and_journalled(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r.returncode == 0, r.stderr
    assert "It is in thy power" in r.stdout, "the stdout channel prints the lesson"
    ledger = (tmp_path / "vault" / "tutor-ledger.md").read_text(encoding="utf-8")
    assert ledger.count("|") > 8 and "Meditations" in ledger and "hypothetical" in ledger
    assert ledger.rstrip().endswith("|"), "the row must be a table row"
    journal = (tmp_path / "vault" / "tutor-journal.md").read_text(encoding="utf-8")
    assert "It is in thy power" in journal


def test_the_ledger_row_has_the_eight_columns_the_weekly_review_scores(tmp_path):
    _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    row = [l for l in (tmp_path / "vault" / "tutor-ledger.md").read_text().splitlines()
           if l.startswith("| 2")][-1]
    cells = [c.strip() for c in row.strip("|").split("|")]
    assert len(cells) == 8, cells
    assert cells[-1] == "hypothetical", "the last cell is the application kind and it is load-bearing"


# ── the floor, checked in code ───────────────────────────────────────────────────────────────

def test_a_lesson_without_a_citation_is_refused(tmp_path):
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": ""}))
    assert r.returncode == 1 and "citation" in r.stderr
    assert not (tmp_path / "vault" / "tutor-journal.md").exists(), "a refused lesson is never journalled"


def test_a_past_application_with_no_evidence_is_refused(tmp_path):
    """The most damaging thing this system can produce is an invented scenario in the register of
    the reader's own history. The prompt forbids it; this is the same rule as code."""
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, {**GOOD_META, "application_kind": "past", "evidence": []}))
    assert r.returncode == 1 and "invented scenario" in r.stderr.replace("\n", " ")


def test_a_past_application_whose_evidence_does_not_exist_is_refused(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG,
                             {**GOOD_META, "application_kind": "past", "evidence": ["/nope/missing.md"]}))
    assert r.returncode == 1 and "not a file that exists" in r.stderr


def test_a_current_application_with_real_quoted_evidence_is_accepted(tmp_path):
    ev = tmp_path / "vault" / "project.md"
    ev.parent.mkdir(exist_ok=True)
    ev.write_text("the retiring is on the list for this week\n", encoding="utf-8")
    msg = (GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                            "WHY NOW: The retiring is on the list for this week.")
                   .replace("Suppose you take ten minutes", "Take ten minutes"))
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "application_kind": "current",
                                             "evidence": [str(ev)]}))
    assert r.returncode == 0, r.stderr


def test_an_unlabelled_hypothetical_is_refused(tmp_path):
    msg = GOOD_MSG.replace("Suppose you take", "You took")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and "Suppose" in r.stderr


def test_a_hypothetical_carrying_evidence_is_refused(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, {**GOOD_META, "evidence": ["/tmp/x"]}))
    assert r.returncode == 1 and "no evidence" in r.stderr


def test_a_lesson_over_the_ceiling_is_refused(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG + "x" * 3100, GOOD_META))
    assert r.returncode == 1 and "ceiling" in r.stderr


# ── failure is loud ──────────────────────────────────────────────────────────────────────────

def test_a_clean_exit_with_no_message_is_a_failure_and_says_so_in_the_ledger(tmp_path):
    (tmp_path / "vault").mkdir(exist_ok=True)
    (tmp_path / "vault" / "tutor-ledger.md").write_text("---\nstatus: on\n---\n\n| date |\n", encoding="utf-8")
    r = _run(tmp_path, _stub(tmp_path, None, None))
    assert r.returncode == 1
    assert "send-failed" in (tmp_path / "vault" / "tutor-ledger.md").read_text(encoding="utf-8")


def test_a_missing_claude_binary_is_a_loud_ledger_row(tmp_path):
    (tmp_path / "vault").mkdir(exist_ok=True)
    (tmp_path / "vault" / "tutor-ledger.md").write_text("---\nstatus: on\n---\n\n| date |\n", encoding="utf-8")
    r = _run(tmp_path, tmp_path / "nope", env_extra={"CLAUDE_BIN": str(tmp_path / "nope")})
    assert r.returncode == 1 and "claude" in r.stderr
    assert "send-failed" in (tmp_path / "vault" / "tutor-ledger.md").read_text(encoding="utf-8")


def test_no_lesson_met_the_floor_is_a_clean_quiet_exit(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, "NO LESSON MET THE FLOOR\n", None))
    assert r.returncode == 0 and "no lesson met the floor" in r.stdout
    assert not (tmp_path / "vault" / "tutor-journal.md").exists()


# ── the reader's switches ────────────────────────────────────────────────────────────────────

def test_the_kill_switch_sends_nothing(tmp_path):
    (tmp_path / "vault").mkdir(exist_ok=True)
    (tmp_path / "vault" / "tutor-ledger.md").write_text("---\nstatus: off\n---\n", encoding="utf-8")
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r.returncode == 0 and "TUTOR: OFF" in r.stdout
    assert not (tmp_path / "vault" / "tutor-journal.md").exists()


def test_the_file_channel_appends_where_it_is_told(tmp_path):
    target = tmp_path / "daily" / "today.md"
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META), "--channel", "file",
             env_extra={"TUTOR_FILE": str(target)})
    assert r.returncode == 0, r.stderr
    assert "It is in thy power" in target.read_text(encoding="utf-8")


def test_an_unknown_channel_is_refused_before_anything_runs(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META), "--channel", "carrier-pigeon")
    assert r.returncode == 2 and "no channel" in r.stderr


def test_a_second_run_while_one_holds_the_lock_does_nothing(tmp_path):
    (tmp_path / "lock").mkdir(parents=True)
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r.returncode == 0 and "lock" in r.stdout


# ── adjudication: two passive channels, and the loud off switch ──────────────────────────────

import datetime as _dt  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("adj", ROOT / "agents" / "tutor" / "adjudicate.py")
ADJ = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ADJ)


def _ledger(rows, status="on"):
    head = f"---\nstatus: {status}\n---\n\n# Tutor ledger\n\n| date | item | citation | check-due | edit | opened | outcome | kind |\n|---|---|---|---|---|---|---|---|\n"
    return head + "".join("| " + " | ".join(r) + " |\n" for r in rows)


def test_a_lesson_the_reader_wrote_about_counts_as_landed(tmp_path):
    surf = tmp_path / "notes"; surf.mkdir()
    (surf / "week.md").write_text("Tried the retiring passage from Meditations loc 269 today.\n", encoding="utf-8")
    led = _ledger([["2026-03-01", "Meditations: retire into thyself", "Meditations loc 269",
                    "2026-03-15", "", "", "", "current"]])
    res = ADJ.adjudicate(led, [surf], _dt.date(2026, 3, 20))
    assert res["resolved_now"][0]["outcome"] == "landed"
    assert res["resolved_now"][0]["edit"].endswith("week.md"), "the receipt names the file"


def test_a_lesson_nobody_picked_up_is_silent_not_a_failure(tmp_path):
    surf = tmp_path / "notes"; surf.mkdir()
    (surf / "week.md").write_text("unrelated\n", encoding="utf-8")
    led = _ledger([["2026-03-01", "Meditations: retire", "Meditations loc 269", "2026-03-15", "", "", "", "current"]])
    res = ADJ.adjudicate(led, [surf], _dt.date(2026, 3, 20))
    assert res["resolved_now"][0]["outcome"] == "silent"


def test_a_hypothetical_is_never_scored_on_an_edit_it_could_not_produce(tmp_path):
    """Scoring a hypothetical on downstream edits manufactures silence, and manufactured silence
    would eventually turn off a loop that was working."""
    led = _ledger([["2026-03-01", "Meditations: retire", "Meditations loc 269", "2026-03-15", "", "", "", "hypothetical"]])
    res = ADJ.adjudicate(led, [tmp_path], _dt.date(2026, 3, 20))
    assert res["resolved_now"][0]["edit"] == "n/a"


def test_a_row_not_yet_due_is_left_open(tmp_path):
    led = _ledger([["2026-03-01", "x", "y", "2026-12-31", "", "", "", "current"]])
    res = ADJ.adjudicate(led, [tmp_path], _dt.date(2026, 3, 20))
    assert res["resolved_now"] == []


def test_seven_silent_lessons_turn_the_loop_off_loudly(tmp_path):
    """Silence means the reader HAD writing to search and the idea is not in it. Only a `current`
    lesson against real surfaces can be silent; see the unmeasured tests below."""
    surf = tmp_path / "w"; surf.mkdir(exist_ok=True)
    (surf / "unrelated.md").write_text("nothing to do with any of it\n", encoding="utf-8")
    rows = [[f"2026-03-{i:02d}", f"item {i}", f"Some Work loc {i}00", f"2026-03-{i:02d}", "", "", "", "current"]
            for i in range(1, 8)]
    led = _ledger(rows)
    res = ADJ.adjudicate(led, [surf], _dt.date(2026, 4, 1))
    assert res["silent_streak"] == 7 and res["kill"]
    out = ADJ.rewrite(led, res)
    assert "status: off" in out and "off_reason:" in out and "wallpaper" in out


def test_six_silences_do_not_turn_it_off(tmp_path):
    surf = tmp_path / "w"; surf.mkdir(exist_ok=True)
    (surf / "unrelated.md").write_text("nothing to do with any of it\n", encoding="utf-8")
    rows = [[f"2026-03-{i:02d}", f"item {i}", f"Some Work loc {i}00", f"2026-03-{i:02d}", "", "", "", "current"]
            for i in range(1, 7)]
    res = ADJ.adjudicate(_ledger(rows), [surf], _dt.date(2026, 4, 1))
    assert res["silent_streak"] == 6 and not res["kill"]


def test_one_landing_breaks_the_streak(tmp_path):
    surf = tmp_path / "n"; surf.mkdir()
    (surf / "a.md").write_text("Meditations loc 269 is the one\n", encoding="utf-8")
    rows = [[f"2026-03-{i:02d}", f"item {i}", f"Some Work loc {i}00", f"2026-03-{i:02d}", "", "", "", "current"]
            for i in range(1, 5)]
    rows.append(["2026-03-06", "Meditations: the retiring", "Meditations loc 269", "2026-03-06", "", "", "", "current"])
    rows += [[f"2026-03-{i:02d}", f"item {i}", f"Some Work loc {i}00", f"2026-03-{i:02d}", "", "", "", "current"]
             for i in range(7, 10)]
    res = ADJ.adjudicate(_ledger(rows), [surf], _dt.date(2026, 4, 1))
    assert res["landed"] == 1 and res["silent_streak"] == 3 and not res["kill"]


# ── the fabricated-memory guard, attacked the way review attacked it ─────────────────────────

FAB = "You took ten minutes before the first meeting on Tuesday and it worked."


def test_a_fabricated_memory_under_another_heading_is_refused(tmp_path):
    """Review's first bypass: no APPLY: line at all, the invented history under its own heading.
    The guard used to inspect only an APPLY line that happened to exist."""
    msg = GOOD_MSG.replace("APPLY: Suppose you take ten minutes before the first meeting tomorrow, door shut, no inbox.",
                           f"What you did: {FAB}")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1, r.stdout
    assert "APPLY:" in r.stderr
    assert not (tmp_path / "vault" / "tutor-journal.md").exists()


def test_a_fabricated_memory_inside_why_held_is_refused(tmp_path):
    """Review's second bypass: a compliant APPLY line, with the invented history above it."""
    msg = GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                           f"WHY HELD: {FAB}")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and "addresses the reader" in r.stderr


def test_a_lower_case_apply_label_is_refused(tmp_path):
    """Review's third bypass: `Apply:` is not `APPLY:`, and a case-sensitive guard simply missed it."""
    msg = GOOD_MSG.replace("APPLY: Suppose you", f"Apply: {FAB} And you")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and ("upper case" in r.stderr or "APPLY:" in r.stderr)


def test_the_impersonal_standing_debt_phrasing_passes(tmp_path):
    """The prompt asks for the debt stated impersonally in a hypothetical — "Marked two years ago,
    never spent since" — precisely so the one line that says "you" is the marked one."""
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r.returncode == 0, r.stderr


# ── the ledger is a table the kill switch reads; a cell is one line ──────────────────────────

def test_a_newline_in_a_meta_field_cannot_write_ledger_lines(tmp_path):
    """Review: an injected `status: off` lands inside the kill switch's own read window and
    disables the loop for good."""
    # The citation is compared against the message's own line now, so the injection goes in the
    # fields that are not compared — which is where a real one would go anyway.
    hostile = {**GOOD_META, "work": "Meditations\nstatus: off\n| 2026-01-01 | injected | x | y | | | | current |",
               "held": "retire\n| 2026-01-02 | second | x | y | | | | current |"}
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, hostile))
    assert r.returncode == 0, r.stderr
    ledger = (tmp_path / "vault" / "tutor-ledger.md").read_text(encoding="utf-8")
    rows = [l for l in ledger.splitlines() if l.startswith("| 2")]
    # The hostile text is not erased — it is confined. One cell is one line, so the payload lands
    # inside a cell as literal text and can no longer BE a row or a frontmatter key.
    assert len(rows) == 1, rows
    assert all(len(r.strip("|").split("|")) == 8 for r in rows), rows
    assert not any(l.startswith("status: off") for l in ledger.splitlines()), \
        "the kill switch reads a line start; nothing a lesson composes may begin a line"
    assert "\n| 2026-01-01 |" not in ledger, "no second row may be written by a field"
    r2 = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r2.returncode == 0 and "TUTOR: OFF" not in r2.stdout, "the loop must still be on afterwards"


def test_an_unknown_application_kind_never_reaches_the_ledger(tmp_path):
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, {**GOOD_META, "application_kind": "hypothetical"}))
    assert r.returncode == 0
    row = [l for l in (tmp_path / "vault" / "tutor-ledger.md").read_text().splitlines() if l.startswith("| 2")][-1]
    assert row.strip("|").split("|")[-1].strip() == "hypothetical"


def test_a_quoted_passage_may_address_its_reader(tmp_path):
    """Plenty of books say "you". The rule is about the message's own prose, not about the book's,
    so a quotation that addresses its reader must not be refused — otherwise the guard silently
    excludes most of the modern shelf."""
    msg = GOOD_MSG.replace('"It is in thy power to retire into thyself"',
                           '"You already have the power to retire into yourself"')
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META,
                                             "held": "You already have the power to retire into yourself"}))
    assert r.returncode == 0, r.stderr


def test_a_fabricated_memory_beside_a_quotation_on_the_held_line_is_refused(tmp_path):
    """Review's H1: the first version exempted the HELD line by construction, so the invented
    history simply moved there. Only the QUOTED span is exempt now."""
    msg = GOOD_MSG.replace("🩷. Marcus is arguing", f"🩷. {FAB} Marcus is arguing")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and "addresses the reader" in r.stderr


def test_a_verb_the_old_denylist_never_listed_is_refused(tmp_path):
    """Review's H3: a closed enumeration of verbs cannot cover a language, and the likeliest real
    failure is not adversarial — it is the model reading a calendar file and writing "last Tuesday
    you walked out of the 9am"."""
    msg = GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                           "WHY HELD: Last Tuesday you walked out of the nine o'clock.")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and "addresses the reader" in r.stderr


def test_the_word_never_no_longer_disables_the_check(tmp_path):
    """Review's H2, the worst of the five: one word switched the guard off, and the prompt itself
    taught the model to write that word on exactly that line."""
    msg = GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                           f"WHY HELD: You have never done this, though you took the ten minutes once.")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and "addresses the reader" in r.stderr


def test_free_text_after_the_citation_line_is_still_checked(tmp_path):
    """Review's H4: the citation line was removed before the check, taking anything after it out
    of scope."""
    msg = GOOD_MSG + f"\n{FAB}\n"
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1 and "addresses the reader" in r.stderr


# ── evidence must be evidence ────────────────────────────────────────────────────────────────

def _past(tmp_path, evidence, msg=None):
    m = msg or GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                                "WHY HELD: Marked two years ago; the retiring shows up in the journal.")
    return _run(tmp_path, _stub(tmp_path, m, {**GOOD_META, "application_kind": "past",
                                              "evidence": [str(e) for e in evidence]}),
                env_extra={"READER_SURFACES": str(tmp_path / "writing")})


def test_a_past_application_cannot_ride_on_a_system_file_existing(tmp_path):
    """Review shipped a fabricated memory on /etc/hosts existing. The kind whose entire job is
    asserting the reader's own history was guarded by a stat() call."""
    r = _past(tmp_path, ["/etc/hosts"])
    assert r.returncode == 1
    assert "outside the vault" in r.stderr or "reproduces nothing" in r.stderr


def test_a_past_application_must_quote_the_file_it_claims_to_come_from(tmp_path):
    (tmp_path / "writing").mkdir(exist_ok=True)
    ev = tmp_path / "writing" / "journal.md"
    ev.write_text("Something else entirely happened that week.\n", encoding="utf-8")
    r = _past(tmp_path, [ev])
    assert r.returncode == 1 and "reproduces nothing" in r.stderr


def test_a_past_application_that_quotes_its_evidence_is_accepted(tmp_path):
    (tmp_path / "writing").mkdir(exist_ok=True)
    ev = tmp_path / "writing" / "journal.md"
    ev.write_text("the retiring shows up in the journal again this week\n", encoding="utf-8")
    r = _past(tmp_path, [ev])
    assert r.returncode == 0, r.stderr


def test_a_directory_is_not_evidence(tmp_path):
    (tmp_path / "writing").mkdir(exist_ok=True)
    r = _past(tmp_path, [tmp_path / "writing"])
    assert r.returncode == 1 and "not a file" in r.stderr


# ── the citation is the artifact the reader is told to open ──────────────────────────────────

def _vault_with_books(tmp_path):
    books = tmp_path / "vault" / "books"
    books.mkdir(parents=True, exist_ok=True)
    (books / "meditations.md").write_text('---\nname: "Meditations"\n---\n', encoding="utf-8")
    return books


def test_a_citation_naming_a_work_the_vault_does_not_hold_is_refused(tmp_path):
    """Review: the citation was shape-checked and never resolved, so
    '(citation: The Necronomicon, p. 9999)' shipped — while the docs told the reader that opening
    the citation was the check they could rely on."""
    _vault_with_books(tmp_path)
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: The Necronomicon p 9999)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "The Necronomicon p 9999"}))
    assert r.returncode == 1 and "does not hold" in r.stderr


def test_a_citation_naming_a_book_the_vault_holds_is_accepted(tmp_path):
    _vault_with_books(tmp_path)
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r.returncode == 0, r.stderr


def test_a_file_citation_must_name_a_file_that_exists(tmp_path):
    _vault_with_books(tmp_path)
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: /nope/missing.md:12)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "/nope/missing.md:12"}))
    assert r.returncode == 1 and "does not exist" in r.stderr


def test_a_vault_with_no_books_yet_cannot_be_checked_against_and_says_nothing(tmp_path):
    """A new reader's vault has no books/ directory. The check is skipped rather than failing them
    on their first run — and KNOWN-GAPS records that it is skipped."""
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, GOOD_META))
    assert r.returncode == 0, r.stderr


def test_the_citation_the_reader_opens_is_the_one_that_is_checked(tmp_path):
    """Review's twelfth-cut block: the runner captured the message's citation line and then
    validated the metadata's instead. A lesson delivered a citation naming a book that does not
    exist while the metadata named a real one — the journal recorded the fake, the ledger the
    valid, and the docs told the reader to open the fake."""
    _vault_with_books(tmp_path)
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: The Necronomicon, p. 9999)")
    r = _run(tmp_path, _stub(tmp_path, msg, GOOD_META))
    assert r.returncode == 1, r.stdout
    assert "does not hold" in r.stderr or "do not match" in r.stderr


def test_the_message_and_the_record_must_agree_on_the_citation(tmp_path):
    _vault_with_books(tmp_path)
    r = _run(tmp_path, _stub(tmp_path, GOOD_MSG, {**GOOD_META, "citation": "Meditations loc 272"}))
    assert r.returncode == 1 and "do not match" in r.stderr


def test_a_short_book_title_survives_a_more_precise_citation(tmp_path):
    """Review: gating containment on length refused Dune, Grit, Ego, Flow, Blink and Range — and
    only when the citation was MORE precise. Matching is token-wise now."""
    books = _vault_with_books(tmp_path)
    (books / "dune.md").write_text('---\nname: "Dune"\n---\n', encoding="utf-8")
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: Dune, Book One, p. 200)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "Dune, Book One, p. 200"}))
    assert r.returncode == 0, r.stderr


def test_a_relative_file_citation_resolves_against_the_vault(tmp_path):
    """The form the project's own schema uses. It was refused, because it resolved against whatever
    directory cron happened to leave the runner in."""
    _vault_with_books(tmp_path)
    (tmp_path / "vault" / "projects").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vault" / "projects" / "x.md").write_text("a line\n" * 50, encoding="utf-8")
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: projects/x.md:41)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "projects/x.md:41"}))
    assert r.returncode == 0, r.stderr


def test_a_citation_pointing_outside_the_readers_files_is_refused(tmp_path):
    """The path branch claimed containment and only checked existence, so ~/.zshrc delivered."""
    _vault_with_books(tmp_path)
    outside = tmp_path / "elsewhere.md"
    outside.write_text("not the reader's\n", encoding="utf-8")
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", f"(citation: {outside}:1)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": f"{outside}:1"}),
             env_extra={"READER_SURFACES": str(tmp_path / "writing")})
    assert r.returncode == 1 and "outside the vault" in r.stderr


def test_a_single_shared_word_does_not_resolve_to_the_wrong_book(tmp_path):
    """The short-title fix cost this: one shared token sent "Habits, p. 12" to Atomic Habits and
    "Ego, p. 12" to Ego Is The Enemy. The reader opens a real book and sees the wrong one, which is
    a different failure from nothing opening, but still wrong. One token is a word; two are a title."""
    books = _vault_with_books(tmp_path)
    (books / "atomic-habits.md").write_text('---\nname: "Atomic Habits"\n---\n', encoding="utf-8")
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: Habits, p. 12)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "Habits, p. 12"}))
    assert r.returncode == 1 and "does not hold" in r.stderr


def test_two_shared_words_still_resolve(tmp_path):
    books = _vault_with_books(tmp_path)
    (books / "atomic-habits.md").write_text('---\nname: "Atomic Habits"\n---\n', encoding="utf-8")
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: Atomic Habits, p. 12)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "Atomic Habits, p. 12"}))
    assert r.returncode == 0, r.stderr


def test_a_short_title_still_matches_exactly(tmp_path):
    books = _vault_with_books(tmp_path)
    (books / "dune.md").write_text('---\nname: "Dune"\n---\n', encoding="utf-8")
    for cite in ("Dune p. 200", "Dune, Book One, p. 200"):
        msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", f"(citation: {cite})")
        r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": cite}))
        assert r.returncode == 0, (cite, r.stderr)


def test_a_work_the_reader_has_distilled_but_not_noded_is_accepted(tmp_path):
    """The prompt lets a lesson come from a distillation. Refusing one because no book node exists
    loses a lesson to an accounting detail."""
    d = tmp_path / "vault" / "distill"
    d.mkdir(parents=True, exist_ok=True)
    (d / "distill-the-enchiridion.md").write_text("---\ntype: distillation\n---\n", encoding="utf-8")
    msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", "(citation: The Enchiridion, ch. 5)")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": "The Enchiridion, ch. 5"}))
    assert r.returncode == 0, r.stderr


def test_the_asymmetry_that_makes_both_short_titles_and_wrong_books_work_out(tmp_path):
    """A single shared token matches only when the SHELF's whole title is that word. "Dune, Book
    One" finds Dune; "Habits, p. 12" does not find Atomic Habits."""
    books = _vault_with_books(tmp_path)
    (books / "dune.md").write_text('---\nname: "Dune"\n---\n', encoding="utf-8")
    (books / "atomic-habits.md").write_text('---\nname: "Atomic Habits"\n---\n', encoding="utf-8")
    for cite, expect in [("Dune, Book One, p. 200", 0), ("Dune p. 200", 0),
                         ("Atomic Habits, p. 12", 0), ("Habits, p. 12", 1), ("Atomic, p. 12", 1)]:
        msg = GOOD_MSG.replace("(citation: Meditations loc 269 🩷)", f"(citation: {cite})")
        r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "citation": cite}))
        assert r.returncode == expect, (cite, r.returncode, r.stderr[:200])


# ── unmeasured is not silence, and conflating them made the kill switch a timer ───────────────

def test_a_hypothetical_lesson_can_never_be_counted_as_silence(tmp_path):
    """Panel finding: a `past` or `hypothetical` application cannot produce a downstream edit by
    construction, so scoring it as silence meant the loop shut itself off on a schedule rather
    than on evidence. With no writing directory every lesson is hypothetical, as the docs say."""
    surf = tmp_path / "w"; surf.mkdir()
    (surf / "x.md").write_text("unrelated\n", encoding="utf-8")
    rows = [[f"2026-03-{i:02d}", f"item {i}", "cite", f"2026-03-{i:02d}", "", "", "", "hypothetical"]
            for i in range(1, 12)]
    res = ADJ.adjudicate(_ledger(rows), [surf], _dt.date(2026, 4, 1))
    assert res["unmeasured"] == 11 and res["silent"] == 0
    assert res["silent_streak"] == 0 and not res["kill"], "eleven unscoreable lessons must not kill the loop"
    assert all(r["outcome"] == "unmeasured" and r["edit"] == "n/a" for r in res["resolved_now"])


def test_no_writing_directory_means_unmeasured_not_failed(tmp_path):
    """The reader with nothing written down is exactly the one the old behaviour punished."""
    rows = [[f"2026-03-{i:02d}", f"item {i}", "cite", f"2026-03-{i:02d}", "", "", "", "current"]
            for i in range(1, 10)]
    res = ADJ.adjudicate(_ledger(rows), [], _dt.date(2026, 4, 1))
    assert res["unmeasured"] == 9 and not res["kill"]


def test_the_report_says_i_cannot_tell_rather_than_it_failed(tmp_path, capsys):
    import subprocess, sys as _s
    v = tmp_path / "vault"; v.mkdir()
    rows = [[f"2026-03-{i:02d}", f"item {i}", "cite", f"2026-03-{i:02d}", "", "", "", "hypothetical"]
            for i in range(1, 9)]
    (v / "tutor-ledger.md").write_text(_ledger(rows), encoding="utf-8")
    r = subprocess.run([_s.executable, str(ROOT / "agents" / "tutor" / "adjudicate.py"),
                        "--vault", str(v), "--today", "2026-04-01"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "unmeasured=8" in r.stdout and "cannot tell" in r.stdout
    assert "TUTOR LOOP: OFF" not in r.stdout


def test_the_pipelines_own_output_is_not_evidence_of_the_readers_life(tmp_path):
    """The sharpest panel finding: the first lesson this system ever produced was a `current`
    application evidenced by the distillation the same pipeline had written minutes earlier. It
    passed every check legitimately — the file existed, sat inside the vault, and shared a phrase
    with the message. The Librarian refuses this by name; the Tutor did not."""
    _vault_with_books(tmp_path)
    for rel in ("distill/distill-meditations.md", "books/meditations.md", "tutor-journal.md"):
        f = tmp_path / "vault" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("the retiring shows up here because this pipeline wrote it\n", encoding="utf-8")
        msg = GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                               "WHY NOW: The retiring shows up here because this pipeline wrote it.")
        r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "application_kind": "current",
                                                 "evidence": [str(f)]}))
        assert r.returncode == 1, f"{rel} was accepted as the reader's own writing"
        assert "this pipeline wrote" in r.stderr, r.stderr


def test_the_readers_own_file_inside_the_vault_is_still_evidence(tmp_path):
    """The exclusion is by role, not by location — a journal kept in the vault is still theirs."""
    _vault_with_books(tmp_path)
    f = tmp_path / "vault" / "journal" / "2026-03-11.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("the retiring shows up in the journal again this week\n", encoding="utf-8")
    msg = GOOD_MSG.replace("WHY HELD: Marked two years ago, never spent since.",
                           "WHY NOW: The retiring shows up in the journal again this week.")
    r = _run(tmp_path, _stub(tmp_path, msg, {**GOOD_META, "application_kind": "current",
                                             "evidence": [str(f)]}))
    assert r.returncode == 0, r.stderr
