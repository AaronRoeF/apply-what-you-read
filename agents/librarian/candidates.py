#!/usr/bin/env python3
"""agents/librarian/candidates.py — did a marked idea ever leave a receipt in your own writing?

This is the corroboration matcher. For every highlight in the corpus it asks one narrow,
checkable question: does a distinctive phrase from this passage appear anywhere in the reader's
own writing? Three answers, and the third is the one worth having:

  candidate   the phrase appears in a file the reader wrote — with file, line and the quote
  noise       the phrase appears so widely that its presence proves nothing
  unapplied   the phrase appears nowhere — an idea marked and never spent

`unapplied` is the point, and it is the robust half. It is the education you paid for and did not
use, and it is only computable because both the marks and the reader's own writing are in one
place. On the reference library it was 5,189 of 5,211 marks.

`candidate` IS NOT A FINDING, and the word was chosen after measuring. On the reference library
this stage produced 21 candidates; read by hand, about five were a real idea travelling from a
book into the reader's work — a named practice from a management book turning up in an operating
document, a framework's own term of art reused in a plan — and the rest were phrases of the
English language that happen to appear in both
places ("a leap of faith", "does the heavy lifting", "vp of engineering"). Every match was true.
Most meant nothing. No mechanical filter fixed this: tightening for distinctiveness removed four
of twenty-five and left the coincidences, because those phrases are genuinely rare *inside this
library* while being common in English. So the honest boundary of a phrase matcher is recall:
it finds every place a mark could have been used, cheaply and without a model, and a judge
decides which ones are real. Treat a candidate as a question, never as evidence.

WHY PHRASES AND NOT TOPICS. A topic model would say "these are both about focus" and be
unfalsifiable. A four-word phrase either appears in a file or it does not, and the receipt is a
line number a human can open. Every rule below exists because a looser version produced a
confident wrong answer:

  * NEVER one or two words. "the system", "first principles" match everything; a two-word match
    is not evidence, it is a coincidence with good manners.
  * At least two non-stop tokens per phrase, so "of the same as" can never be a candidate.
  * DISTINCTIVENESS, which is the rule the first honest run forced. Every phrase must contain a
    token appearing in at most RARE_MAX_DF of the books. Without it the matcher returned "a leap
    of faith", "does the heavy lifting", "willingness to take risks" and "vp of engineering" as
    receipts — each match real, each meaningless. Those are phrases of the English language, not
    of a book, and a phrase that could have come from anywhere is evidence of nothing.
  * The stoplist is not just function words. Any token appearing in more than STOP_DF of the
    corpus files is stopped TOO — the vocabulary of one reader's library is not neutral, and a
    word like "leader" in a shelf of management books carries no distinguishing power.
  * A noise floor. If a phrase turns up in more than max(25, 2%) of the reader's files, it is a
    figure of speech, not a receipt. The unbuilt first version of this had no floor, and its
    ancestor matched a phrase in 782 files and called all 782 evidence.
  * Self-exclusion, twice. By path: the corpus, the book nodes, the distillations and this
    tool's own output are never searched, because a book node quoting its own highlight would
    corroborate everything. By behaviour: any file that matches more than MIRROR_PHRASES
    distinct phrases is a MIRROR of the corpus — a review of the scans, a quote dump, an
    import log — and its hits are discarded with a loud line. Measured on the reference
    corpus: one such file supplied 60 of the first 102 receipts, and every one of them was the
    book quoting itself. Path rules cannot find these; the file sat in a project directory with
    an ordinary name. A phrase in too many files is noise; a file with too many phrases is a
    mirror. The two floors are the same idea seen from each side.

Usage:
  READER_SURFACES=/abs/dir1:/abs/dir2 python -m agents.librarian.candidates
  python agents/librarian/candidates.py --surfaces DIR[:DIR...] [--corpus DIR] [--out FILE]
      [--json] [--limit N] [--phrases-per-highlight 3] [--report-unapplied 20]

Output: one JSON object per highlight on `--out` (default RG_OUT/candidates.jsonl), plus a
report on stdout that leads with the sorted count vector — the shape of the result before its
interpretation, so a silently empty run cannot look like a clean one.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import sys

# n-gram sizes. A short highlight (< SHORT_TOKENS) may use 3, because a 12-word aphorism has few
# 4-grams and refusing it would silently exclude the most quotable passages in the corpus.
NGRAM = 4
NGRAM_SHORT = 3
SHORT_TOKENS = 8
PHRASES_PER_HIGHLIGHT = 3
STOP_DF = 0.20          # a token in > 20% of corpus files is stopped, whatever it is
NOISE_MIN = 25          # a phrase in more than max(25, 2% of surface files) is noise
NOISE_FRACTION = 0.02
MIRROR_PHRASES = 10     # a file matching more than this many distinct corpus phrases MIRRORS the
                        # corpus rather than applying it — see mirrors() below
MIN_CONTENT_TOKENS = 2  # a candidate phrase needs at least this many non-stop tokens
RARE_MAX_DF = 0.10      # a phrase must hold a token appearing in <= 10% of the books, or it is
                        # a phrase of the language rather than of the book — see below
STOP_MIN_BOOKS = 5      # below this many books a document-frequency stoplist stops everything

FUNCTION_WORDS = """a about above after again against all am an and any are as at be because been
before being below between both but by can cannot could did do does doing down during each few
for from further had has have having he her here hers herself him himself his how i if in into is
it its itself just me more most my myself no nor not now of off on once only or other ought our
ours ourselves out over own same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up very was we were what
when where which while who whom why will with would you your yours yourself yourselves thou thy
thee thine art hath doth shall may must one two three thing things way ways make makes made take
takes taken get gets got go goes going come comes came see sees seen know knows known think
thinks thought say says said like also even still much many every another any some new good great
best better first last long time times day days man men people work works world life live lives""".split()

WORD_RE = re.compile(r"[a-z0-9']+")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)


def norm_tokens(text: str) -> list[str]:
    """Lowercase word tokens. Punctuation, quotes and line breaks vanish, so a phrase split
    across two lines in the reader's file still matches the same phrase in the book."""
    return WORD_RE.findall(text.lower())


def ngrams(tokens: list[str], n: int) -> list[tuple[int, str]]:
    """(start index, phrase) for every n-gram."""
    return [(i, " ".join(tokens[i:i + n])) for i in range(len(tokens) - n + 1)]


def load_corpus(corpus: pathlib.Path) -> list[dict]:
    """Every highlight in the merged corpus, with its book. Photographed-page text is included
    when the page carries recognised text — a marked page is a mark."""
    out = []
    for f in sorted(corpus.glob("*.json")):
        if f.name.startswith("_"):
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        book = rec.get("book") or f.stem
        for h in rec.get("kindle_highlights") or []:
            t = (h.get("text") or "").strip()
            if t:
                out.append({"book": book, "slug": f.stem, "id": h.get("id") or "", "text": t,
                            "color": h.get("color"), "location": h.get("location"), "kind": "highlight"})
        for p in rec.get("photo_pages") or []:
            t = (p.get("ocr_text") or p.get("text") or "").strip()
            if t:
                out.append({"book": book, "slug": f.stem, "id": p.get("id") or p.get("image") or "",
                            "text": t, "color": None, "location": p.get("page"), "kind": "page"})
    return out


def corpus_stoplist(marks: list[dict], threshold: float = STOP_DF) -> set[str]:
    """Function words PLUS any token appearing in more than `threshold` of the books.

    This is the rule that a general stoplist cannot supply: one reader's library has its own
    neutral vocabulary, and the tokens that carry no signal are different for a shelf of
    management books than for a shelf of novels. Measured on the reference corpus, this stops
    words a hand-written list never would."""
    per_book: dict[str, set[str]] = collections.defaultdict(set)
    for m in marks:
        per_book[m["slug"]].update(norm_tokens(m["text"]))
    n_books = len(per_book)
    df = collections.Counter()
    for toks in per_book.values():
        df.update(toks)
    # A document-frequency stoplist needs documents. On a one-book corpus every token appears in
    # 100% of the books, so the naive rule stops the entire vocabulary and the tool silently
    # returns nothing — the shape of a clean run. Below STOP_MIN_BOOKS, derive nothing.
    if n_books < STOP_MIN_BOOKS:
        return set(FUNCTION_WORDS)
    derived = {t for t, c in df.items() if c / n_books > threshold and c >= 2}
    return set(FUNCTION_WORDS) | derived


def phrase_rarity(marks: list[dict]) -> collections.Counter:
    """How many books each token appears in — used to prefer the rarest phrase of a highlight."""
    per_book: dict[str, set[str]] = collections.defaultdict(set)
    for m in marks:
        per_book[m["slug"]].update(norm_tokens(m["text"]))
    df = collections.Counter()
    for toks in per_book.values():
        df.update(toks)
    return df


def candidate_phrases(text: str, stop: set[str], df: collections.Counter,
                      per_highlight: int = PHRASES_PER_HIGHLIGHT, n_books: int = 1) -> list[str]:
    """Up to `per_highlight` distinctive phrases from one mark, rarest first.

    A phrase qualifies only if it holds MIN_CONTENT_TOKENS tokens that are not stopped. Phrases
    are then ranked by the rarity of their rarest content token, so a highlight contributes its
    most distinctive spans rather than its first ones, and overlapping spans are dropped."""
    toks = norm_tokens(text)
    if len(toks) < NGRAM_SHORT:
        return []
    n = NGRAM_SHORT if len(toks) < SHORT_TOKENS else NGRAM
    # Distinctiveness: on a library large enough to measure it, a phrase must carry a token that
    # is rare ACROSS the library. Below STOP_MIN_BOOKS there is nothing to measure against.
    rare_cap = max(1, int(n_books * RARE_MAX_DF)) if n_books >= STOP_MIN_BOOKS else None
    scored = []
    for i, phrase in ngrams(toks, n):
        content = [t for t in phrase.split() if t not in stop]
        if len(content) < MIN_CONTENT_TOKENS:
            continue
        rarest = min(df.get(t, 1) for t in content)
        if rare_cap is not None and rarest > rare_cap:
            continue
        scored.append((rarest, i, phrase))
    scored.sort(key=lambda x: (x[0], x[1]))
    chosen: list[str] = []
    taken: list[int] = []
    for _, i, phrase in scored:
        if any(abs(i - j) < n for j in taken):     # no two chosen phrases may overlap
            continue
        chosen.append(phrase)
        taken.append(i)
        if len(chosen) >= per_highlight:
            break
    return chosen


def surface_files(dirs: list[pathlib.Path], exclude: list[pathlib.Path]) -> list[pathlib.Path]:
    """Every markdown file under the reader's surfaces, minus everything derived FROM the corpus.

    Self-exclusion is not a nicety: a book node quotes its own highlights, so leaving `books/`
    or a distillation in the search set would corroborate the entire library against itself."""
    ex = [e.resolve() for e in exclude]
    out = []
    for d in dirs:
        if not d.exists():
            # Same class: a mistyped surfaces path would report every mark unapplied, which is
            # indistinguishable from the true result and far more likely to be believed.
            print(f"candidates: READER_SURFACES names {d}, which does not exist — nothing there "
                  f"can corroborate anything, and the result below will say so misleadingly.",
                  file=sys.stderr)
            continue
        for p in sorted(d.rglob("*.md")):
            rp = p.resolve()
            if any(str(rp).startswith(str(e) + os.sep) or rp == e for e in ex):
                continue
            parts = set(rp.parts)
            if parts & {"books", "_orphaned", "praxis", "out", ".git", "node_modules"}:
                continue
            if p.name.startswith("distill-") or p.name.startswith("_"):
                continue
            out.append(p)
    return out


def search(phrases: set[str], files: list[pathlib.Path], sizes: set[int]) -> dict[str, list[tuple[str, int, str]]]:
    """Stream every surface file once, recording which candidate phrases occur where.

    Two passes over the data would be the obvious shape (index the files, then query). It is the
    wrong one here: the candidate set is thousands of phrases and the surfaces are millions of
    tokens, so we hold the small set in memory and stream the large one. Line numbers come from a
    token→line map, so a receipt points at the line a human should open."""
    hits: dict[str, list[tuple[str, int, str]]] = collections.defaultdict(list)
    for p in files:
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        body = FRONTMATTER_RE.sub("", raw)
        lines = body.split("\n")
        toks: list[str] = []
        tok_line: list[int] = []
        for ln, line in enumerate(lines, 1):
            for t in norm_tokens(line):
                toks.append(t)
                tok_line.append(ln)
        for n in sizes:
            for i, phrase in ngrams(toks, n):
                if phrase in phrases:
                    ln = tok_line[i]
                    hits[phrase].append((str(p), ln, lines[ln - 1].strip()[:200]))
    return hits


def mirrors(hits: dict[str, list[tuple[str, int, str]]], cap: int = MIRROR_PHRASES) -> set[str]:
    """Files that quote the corpus instead of applying it.

    A reader who used an idea mentions it once or twice. A file holding dozens of distinct
    phrases from the library is not evidence of use — it is the library, copied. Returning these
    as receipts is the single most convincing wrong answer this tool can produce, because each
    receipt is individually true."""
    per_file: dict[str, set[str]] = collections.defaultdict(set)
    for phrase, hs in hits.items():
        for f, _, _ in hs:
            per_file[f].add(phrase)
    return {f for f, ph in per_file.items() if len(ph) > cap}


def adjudicate(marks: list[dict], phrases_by_mark: dict[int, list[str]],
               hits: dict[str, list[tuple[str, int, str]]], n_files: int,
               mirror_files: set[str] | None = None) -> list[dict]:
    """candidate / noise / unapplied, with the receipt when there is one."""
    floor = max(NOISE_MIN, int(n_files * NOISE_FRACTION))
    mirror_files = mirror_files or set()
    out = []
    for idx, m in enumerate(marks):
        phrases = phrases_by_mark.get(idx, [])
        receipts, noisy = [], []
        for ph in phrases:
            h = [x for x in hits.get(ph, []) if x[0] not in mirror_files]
            if not h:
                continue
            files = {x[0] for x in h}
            if len(files) > floor:
                noisy.append({"phrase": ph, "files": len(files)})
            else:
                for f, ln, quote in h[:3]:
                    receipts.append({"phrase": ph, "file": f, "line": ln, "quote": quote})
        status = "candidate" if receipts else ("noise" if noisy else "unapplied")
        out.append({**m, "phrases": phrases, "status": status, "receipts": receipts,
                    "noise": noisy, "noise_floor": floor})
    return out


def report(rows: list[dict], n_files: int, unapplied_n: int = 20) -> str:
    """The sorted count vector first — the shape before the story. A run that matched nothing
    and a run that was never given any surfaces produce different vectors, and that difference
    is the whole reason this prints before anything else."""
    by_status = collections.Counter(r["status"] for r in rows)
    per_book = collections.Counter(r["book"] for r in rows)
    corro_by_book = collections.Counter(r["book"] for r in rows if r["status"] == "candidate")
    counts = sorted(per_book.values())
    lines = [
        f"candidates: marks={len(rows)} surfaces={n_files} "
        f"candidates={by_status['candidate']} noise={by_status['noise']} unapplied={by_status['unapplied']}",
        f"  sorted marks-per-book = {counts}",
        "  a candidate is a question for a judge, not a finding — most are coincidences of the language",
    ]
    if not rows:
        lines.append("  REFUSED READING: zero marks — the corpus is empty or unreadable, which is not a result")
        return "\n".join(lines)
    if n_files == 0:
        lines.append("  WARNING: zero surface files — every mark is unapplied BY CONSTRUCTION, not by evidence")
    ranked = sorted(per_book.items(), key=lambda kv: (-(kv[1] - corro_by_book[kv[0]]), kv[0]))
    lines.append(f"  books with the most unspent marks (top {min(unapplied_n, len(ranked))}):")
    for book, n in ranked[:unapplied_n]:
        c = corro_by_book[book]
        lines.append(f"    {n - c:4d} unspent of {n:4d}   {book[:60]}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    rg_out = pathlib.Path(os.environ.get("RG_OUT") or (pathlib.Path(__file__).resolve().parents[2] / "out"))
    ap.add_argument("--corpus", default=str(rg_out / "merged"), help="the merged corpus directory")
    ap.add_argument("--surfaces", default=os.environ.get("READER_SURFACES", ""),
                    help="colon-separated directories of the reader's OWN writing")
    ap.add_argument("--out", default=str(rg_out / "candidates.jsonl"))
    ap.add_argument("--phrases-per-highlight", type=int, default=PHRASES_PER_HIGHLIGHT)
    ap.add_argument("--limit", type=int, default=0, help="stop after N marks (a smoke run)")
    ap.add_argument("--report-unapplied", type=int, default=20)
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    a = ap.parse_args(argv)

    corpus = pathlib.Path(a.corpus).expanduser()
    if not corpus.is_dir():
        print(f"candidates: no corpus at {corpus} — run corpus/merge_corpus.py first", file=sys.stderr)
        return 2
    marks = load_corpus(corpus)
    if not marks:
        print(f"candidates: REFUSED — {corpus} holds no marks. An empty corpus and a corpus with "
              f"nothing found are the same number here; that must be an error, never a clean exit.",
              file=sys.stderr)
        return 3
    if a.limit:
        marks = marks[:a.limit]

    stop = corpus_stoplist(marks)
    df = phrase_rarity(marks)
    n_books = len({m["slug"] for m in marks})
    phrases_by_mark, all_phrases, sizes = {}, set(), set()
    for i, m in enumerate(marks):
        ph = candidate_phrases(m["text"], stop, df, a.phrases_per_highlight, n_books)
        if ph:
            phrases_by_mark[i] = ph
            all_phrases.update(ph)
            sizes.update(len(p.split()) for p in ph)

    dirs = [pathlib.Path(d).expanduser() for d in a.surfaces.split(":") if d.strip()]
    files = surface_files(dirs, exclude=[corpus, pathlib.Path(a.out).parent])
    hits = search(all_phrases, files, sizes) if all_phrases and files else {}
    mirror_files = mirrors(hits)
    rows = adjudicate(marks, phrases_by_mark, hits, len(files), mirror_files)

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    if a.json:
        by_status = collections.Counter(r["status"] for r in rows)
        print(json.dumps({"marks": len(rows), "surfaces": len(files), "phrases": len(all_phrases),
                          **{k: by_status[k] for k in ("candidate", "noise", "unapplied")},
                          "out": str(out)}, indent=1))
    else:
        print(report(rows, len(files), a.report_unapplied))
        for f in sorted(mirror_files):
            print(f"  MIRROR (not a receipt): {f} quotes the corpus rather than applying it")
        print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
