"""capture/kindle/cli.py — `python -m capture.kindle`: one or more exports in, kindle-highlights.json out.

    python -m capture.kindle clippings "path/My Clippings.txt" --out out/kindle-highlights.json
    python -m capture.kindle html notebook.html [more.html ...] --out out/kindle-highlights.json
    python -m capture.kindle readwise highlights.csv --out out/kindle-highlights.json
    python -m capture.kindle clippings a.txt readwise b.csv --out ...   # several sources, merged

Sources merge by book (asin, synthetic when absent) and dedupe annotations by id, so the same
highlight seen in two exports lands once. The plausibility report prints at the end of every
run; pass --previous to diff against the last output. Exit 1 on an empty parse of real input.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from . import clippings, notebook_html, plausibility, readwise_csv
from .schema import EmptyParseError, merge_books, to_kindle_json, write_kindle_json

KINDS = ("clippings", "html", "readwise")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m capture.kindle", description=__doc__.split("\n")[0])
    ap.add_argument("items", nargs="+", help="kind then path(s): clippings|html|readwise <file> [...]")
    ap.add_argument("--out", default=os.environ.get("RG_OUT", "out") + "/kindle-highlights.json")
    ap.add_argument("--previous", help="a previous kindle-highlights.json to diff counts against")
    ap.add_argument("--diagnose", action="store_true", help="clippings: print one line per record")
    args = ap.parse_args(argv)

    groups, kind = [], None
    for item in args.items:
        if item in KINDS:
            kind = item
            continue
        if kind is None:
            ap.error(f"say which kind '{item}' is: one of {KINDS}")
        try:
            if kind == "clippings":
                groups.append(clippings.parse_clippings_file(item, diagnose=args.diagnose))
            elif kind == "html":
                groups.append([notebook_html.parse_notebook_html_file(item)])
            else:
                groups.append(readwise_csv.parse_readwise_csv_file(item))
        except EmptyParseError as e:
            print(f"EMPTY PARSE ({kind} {item}): {e}", file=sys.stderr)
            return 1
        print(f"parsed {kind:9s} {item}: {sum(len(b.annotations) for b in groups[-1])} annotations in {len(groups[-1])} book(s)")
    books = merge_books(*groups)
    sources = "+".join(sorted({k for k in args.items if k in KINDS}))
    doc = to_kindle_json(books, source=sources)
    write_kindle_json(args.out, doc)
    print(f"wrote {args.out}: {doc['books_with_highlights']} book(s), {doc['total_annotations']} annotations")
    prev = json.loads(pathlib.Path(args.previous).read_text(encoding="utf-8")) if args.previous else None
    plausibility.check(doc, previous=prev)
    return 0
