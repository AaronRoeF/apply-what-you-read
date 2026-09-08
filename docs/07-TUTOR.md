# 07 — The Tutor: one cited lesson at a time

This is the end of the pipeline and the reason for the rest of it. Everything before this produced
a substrate; this puts one passage in front of you, with a citation you can check in ten seconds
and one thing to do about it.

```bash
VAULT=~/vault bash agents/tutor/run.sh
```

That prints a lesson. No account, no key, no network. It is also the last step of `quickstart.sh`.

```
APPLY WHAT YOU READ LESSON

HELD: "It is in thy power to retire into thyself, and to be at rest" — Meditations, loc 269, 🟡.
Marcus is arguing that the retreat people look for in the countryside is available anywhere, at
any moment, and that seeking it elsewhere is itself the avoidance.

WHY HELD: Marked two years ago, never spent since.

APPLY: Suppose you take ten minutes before the first meeting tomorrow, door shut, no inbox.

(citation: Meditations loc 269 🩷)
```

## The floor: what a lesson must have

Two conditions, both required, or nothing is sent.

**A citation.** Work and location, or `file:line`. A lesson you cannot check in ten seconds is a
fortune cookie with a footnote.

**An application, of exactly one kind.**

| kind | what it is | evidence |
|---|---|---|
| `current` | something live in your work now | a file the agent read this run |
| `past` | something in your own history | a file the agent read this run |
| `hypothetical` | a scenario constructed so the lesson lands | none, and it says so |

Evidence means evidence: a `current` or `past` path must be a real file inside your vault or your
own writing, and the lesson must reproduce a fragment of it. Existence alone is not evidence — a
lesson once passed an earlier version of this check by naming a system file that happened to be
on disk.

A hypothetical opens with "Say " or "Suppose ". That is not a stylistic preference. **The most
damaging thing a system like this can produce is an invented scenario written in the register of
your own history** — a fabricated memory, delivered with a citation, in a channel you trust.

**What is actually guaranteed, and what is not.** The runner checks form, and form is decidable:
a hypothetical must carry a marked APPLY line, and outside quoted spans no line but that one may
address you; a `current` or `past` application must name real files inside your vault or your own
writing, and the message must reproduce a fragment of one of them. Each of those is enforced in
code and has a test.

What is *not* guaranteed is that a lesson never asserts something you did. That claim is semantic,
and no lexical rule decides it — English drops the subject, so "Tuesday, ten minutes in the car
before the nine o'clock" asserts a memory without ever saying "you". An earlier draft of this
document promised that a hypothetical "can never be read as something you did". Adversarial review
falsified that promise three times running, against three different implementations, and the
sentence has been removed rather than defended. Treat the guard as a floor that catches the
careless shapes, not as a proof.

The mitigation you can rely on is the citation: every lesson names where it came from, and a claim
about your own history must quote the file it claims to come from. If a lesson tells you something
you do not recognise, open its citation. That is the check the design actually earns.

## The model composes; the runner decides

The agent writes two files and stops. It sends nothing and records nothing. The runner then checks,
in code, everything above, plus the message's size against the channel's limit.

A rule that is only asked for in a prompt is a rule that is eventually not followed. This split is
also what makes the loop testable: the whole thing runs against a stub that composes a bad lesson
on purpose, and every refusal has a test.

**Nothing is recorded until a delivery succeeds.** A failed send writes a loud row in the ledger and
exits non-zero. It never touches the journal, because a lesson that was never delivered must not
read afterwards as a lesson that was taught.

## Where it arrives

| channel | needs |
|---|---|
| `stdout` (default) | nothing |
| `file` | `TUTOR_FILE` — a daily note, an inbox folder, anything that watches a path |
| `ntfy` | `TUTOR_NTFY_URL` — a phone push |

A channel is a fifteen-line script that takes a message and a title. Adding one is easy, and no
credential ever enters the model's tool surface, because the model never sends anything.

Start with `stdout` redirected to a file, and read a week of lessons before you point it at your
phone. A channel you learn to ignore is worse than one you never set up.

## The ledger, and the switch that turns it off

Every lesson gets a row: the date, the item, the citation, a check-due date fourteen days out, two
outcome columns and the application kind.

```bash
python agents/tutor/adjudicate.py --vault ~/vault --surfaces ~/writing --apply
```

Adjudication is passive and **never asks you anything**. A lesson landed if your own writing cites
its idea within the window. You are never asked "was that useful?", because that answer is
unreliable and the asking is itself a cost. A second signal — whether you opened the file it cited
— is designed and not built; the column stays empty rather than pretending.

**A lesson this cannot score is `unmeasured`, not silent.** A past or hypothetical application
cannot produce a downstream edit, and with no writing directory there is nothing to search at all.
Those do not advance the streak. An earlier version counted them as silence, which turned the
switch below into a timer: a reader with nothing written down accumulated seven silences and lost
the loop in the third week whatever it had been worth to them.

**Seven consecutive lessons that land nowhere turn the loop off.** Not quieter, not less often:
off, with the reason written into the ledger, until you set `status: on` yourself.

A daily channel that gets skimmed is a channel where this dies quietly, and dying quietly is the
failure worth engineering against. A system that keeps sending into silence has stopped being a
tutor and become a notification.

Note that `edit` is scored only on `current` rows. A hypothetical lesson cannot produce a
downstream edit, so scoring it that way would manufacture silence — and manufactured silence would
eventually switch off a loop that was working.

## Focus: pointing it at one book

Put a `tutor-focus.md` in your vault:

```yaml
---
status: on
book: meditations
context: mornings
frame: "the hour before anyone needs me"
min_per_day: 1
started: 2026-03-01
ends: 2026-05-30
---
## Shape
- Anchor on what this week actually looks like, not on the book's own order.
## Feedback
```

At least one lesson a day then comes from that book, applied to that context, through that frame.
The rest stay free-ranging. `Shape` holds standing instructions the Tutor obeys; `Feedback` is where
your reactions to individual lessons go, and a thumbs-down means a passage is never nudged again.

The Tutor reads this file at the top of every run and never writes to it. It is yours.

## On a schedule

`agents/tutor/cron.example` and `agents/tutor/launchd.example.plist` run it three times a day, with
a weekly adjudication. Both ship with `RunAtLoad` off and paths you must change, because a job that
fires the moment you install it teaches you what it does by surprising you, which is the wrong
order.

## Next

[08-LIBRARIAN](08-LIBRARIAN.md) — what you marked and never used, and why the cross-book graph is
not on the roadmap.
