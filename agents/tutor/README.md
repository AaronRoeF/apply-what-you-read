# tutor — one cited lesson at a time, to a channel you already open

The pipeline ends here. A vault full of distilled books is a library; this is the part that makes
it an education, by putting one passage in front of you, with a citation you can check in ten
seconds and one thing to do about it.

```bash
VAULT=~/vault agents/tutor/run.sh                       # prints a lesson
VAULT=~/vault agents/tutor/run.sh --channel file        # TUTOR_FILE=~/daily/today.md
VAULT=~/vault agents/tutor/run.sh --channel ntfy        # TUTOR_NTFY_URL=https://ntfy.sh/your-topic
```

## The model composes; the runner decides

The agent writes two files — the message and a small `meta.json` — and stops. It sends nothing,
records nothing. The runner then checks, in code, everything the prompt asked for:

| rule | why it is code and not just prose |
|---|---|
| a citation exists | a lesson you cannot check in ten seconds is a fortune cookie |
| exactly one application kind: `current`, `past`, `hypothetical` | the kind decides how it is scored later |
| `current` and `past` name a file that **exists** | the guard against a fabricated memory |
| `hypothetical` carries no evidence and opens "Say " or "Suppose " | so it can never read as something you did |
| the message fits the channel | most push services truncate silently |

A rule that is only asked for in a prompt is a rule that is eventually not followed. This split is
what makes the loop testable: the whole thing runs against a stub that composes a bad lesson on
purpose, and every refusal above has a test.

**Nothing is recorded until a delivery succeeds.** A failed send writes a loud row in the ledger
and exits non-zero. It never touches the journal, because a lesson that was never delivered must
not read afterwards as a lesson that was taught.

## The ledger, and the switch that turns it off

Every lesson gets a row: date, item, citation, a check-due date fourteen days out, two outcome
columns, and the application kind.

```bash
python agents/tutor/adjudicate.py --vault ~/vault --surfaces ~/writing --apply
```

Adjudication is **passive, and never asks you anything**. A lesson landed if your own writing
cites its idea within the window. You are never asked "was this useful?" — that answer is
unreliable and the asking is itself a cost. A second signal, whether you opened the cited file, is
designed and not built. A lesson that cannot be scored is `unmeasured` and does not count toward
the switch: "I cannot tell" is not "it failed".

**Seven consecutive lessons that land nowhere turn the loop off.** Not quieter, not less often:
off, with the reason written into the ledger, until you set `status: on` yourself. A daily channel
that gets skimmed is a channel where this dies quietly, and dying quietly is the failure worth
engineering against. `edit` is scored only on `current` rows: a hypothetical lesson cannot produce
a downstream edit, and scoring it that way would manufacture the silence that eventually kills a
loop that was working.

## Focus

Put a `tutor-focus.md` in your vault and the Tutor will draw at least N lessons a day from one
book, applied to one project, through a frame you write. Everything else stays free-ranging. The
same file holds standing instructions and your feedback on individual lessons; the Tutor reads it
at the top of every run and never writes to it.

## Channels

`stdout` (the default — no account, no key, no network), `file` (append to a daily note or an
inbox folder), `ntfy` (a phone push). A channel is one small script that takes the message and a
title; adding one is a fifteen-line file, and no credential ever enters the model's tool surface,
because the model never sends anything.

## Scheduling

`cron.example` and `launchd.example.plist` run it three times a day. Start with `stdout` and read
the journal for a week before you point it at your phone.
