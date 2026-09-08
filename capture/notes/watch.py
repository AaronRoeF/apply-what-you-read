#!/usr/bin/env python3
"""capture/notes/watch.py — keep a Notes folder flowing, without re-doing the whole thing.

A note you write tonight should be in the vault by morning, and a run that changes nothing should
change nothing. This compares each note's modification date and content hash against a small state
file and exports only what moved.

  python capture/notes/watch.py --folder Praxis --library ~/vault/books
  python capture/notes/watch.py --folder Praxis --run          # export, then run the stages

Three rules it exists to keep:

  * NOTHING IS DELETED. A note you remove from Apple Notes does not remove anything downstream;
    it is recorded as `gone` in the state file and its exported files stay. Deletion in one place
    must never cascade into a store the reader thinks of as an archive.
  * UNCHANGED MEANS UNTOUCHED. Files are only rewritten when their note changed, so mtimes stay
    meaningful and a nightly run is free.
  * SILENT WHEN QUIET, LOUD WHEN BROKEN. No output when nothing moved; a non-zero exit and a
    message when the database, the folder or the media are not what they were.

Env: RG_NOTES_FOLDER, RG_NOTES_DB, RG_OUT (the state file lives at RG_OUT/notes-state.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from capture.notes import apple_notes as AN                    # noqa: E402


def fingerprint(note: dict) -> str:
    """What "changed" means for one note: its title, its body, and every attachment's identity and
    recognised text. Apple rewrites modification dates in bulk on sync, so the hash decides and the
    date is only a cheap pre-filter."""
    h = hashlib.sha256()
    h.update((note["title"] or "").encode("utf-8"))
    h.update((note["body"] or "").encode("utf-8"))
    for a in note["attachments"]:
        h.update(f"{a['id']}|{a['uti']}|{len(a['ocr'])}|{len(a['handwriting'])}".encode("utf-8"))
    return h.hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    rg_out = pathlib.Path(os.environ.get("RG_OUT") or (HERE.parents[1] / "out"))
    ap.add_argument("--folder", action="append", default=[])
    ap.add_argument("--db", default=os.environ.get("RG_NOTES_DB", AN.DEFAULT_DB))
    ap.add_argument("--accounts", default=AN.ACCOUNTS)
    ap.add_argument("--pages", default=str(rg_out / "pages"))
    ap.add_argument("--notes", default=str(rg_out / "praxis-notes"))
    ap.add_argument("--library", action="append", default=[])
    ap.add_argument("--map", default="")
    ap.add_argument("--state", default=str(rg_out / "notes-state.json"))
    ap.add_argument("--run", action="store_true", help="after exporting, run the pipeline stages")
    ap.add_argument("--force", action="store_true", help="ignore the state file and export everything")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    folders = a.folder or [os.environ.get("RG_NOTES_FOLDER", "Praxis")]
    db = pathlib.Path(a.db).expanduser()
    if not db.exists():
        print(f"watch: no Notes database at {db}", file=sys.stderr)
        return 2
    state_path = pathlib.Path(a.state).expanduser()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {"notes": {}}
    known = {} if a.force else dict(state.get("notes", {}))

    mapping = {}
    if a.map:
        for line in pathlib.Path(a.map).expanduser().read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "\t" in line:
                k, v = line.split("\t", 1)
                mapping[k.strip()] = v.strip()

    with tempfile.TemporaryDirectory(prefix="rg-watch-") as tmp:
        con = AN.open_readonly(db, pathlib.Path(tmp))
        notes, missing = [], []
        for f in folders:
            try:
                notes += AN.fetch_folder(con, f)
            except LookupError:
                missing.append(f)
        if missing:
            print(f"watch: REFUSED — no folder named {', '.join(repr(m) for m in missing)}", file=sys.stderr)
            return 3
        seen = {n["id"]: fingerprint(n) for n in notes}
        changed = [n for n in notes if known.get(n["id"], {}).get("fp") != seen[n["id"]]]
        gone = [nid for nid in known if nid not in seen and not known[nid].get("gone")]

        result = {"folders": folders, "notes": len(notes), "changed": len(changed), "gone": len(gone)}
        if changed:
            library = AN.load_library([pathlib.Path(p).expanduser() for p in a.library])
            out = AN.export(changed, pathlib.Path(a.pages).expanduser(),
                            pathlib.Path(a.notes).expanduser(),
                            pathlib.Path(a.accounts).expanduser(), False, mapping, library)
            result["stats"] = out["stats"]

    now = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    for n in notes:
        state.setdefault("notes", {})[n["id"]] = {"fp": seen[n["id"]], "title": n["title"], "seen": now}
    for nid in gone:
        # A note removed from Apple Notes never removes anything here. It is recorded, not erased.
        state["notes"][nid]["gone"] = now
    state["last_run"] = now
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")

    if a.run and changed:
        root = HERE.parents[1]
        for cmd in (["capture/pages/manifest.py", "--pages", a.pages, "--out", str(rg_out / "manifest.json")],
                    ["corpus/build_bookcorpus.py"], ["corpus/merge_corpus.py"]):
            r = subprocess.run([sys.executable, str(root / cmd[0]), *cmd[1:]], cwd=root)
            if r.returncode != 0:
                print(f"watch: stage {cmd[0]} exited {r.returncode}", file=sys.stderr)
                return 4

    if a.json:
        print(json.dumps(result, indent=1))
    elif changed or gone:
        print(f"watch: {len(changed)} note(s) changed, {len(gone)} gone (recorded, never deleted) "
              f"of {len(notes)} in {','.join(folders)}")
        for n in changed[:10]:
            print(f"  changed  {n['title'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
