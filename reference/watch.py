#!/usr/bin/env python3
"""Live animated dashboard for the OCR pass. Purely cosmetic; reads, never writes.

    python3 watch.py --ocr out/ocr.jsonl --total 3545
"""
from __future__ import annotations

import argparse, json, os, sys, time
from pathlib import Path

C = dict(r="\033[0m", d="\033[2m", b="\033[1m", g="\033[38;5;42m", y="\033[38;5;220m",
         o="\033[38;5;208m", p="\033[38;5;141m", c="\033[38;5;51m", gr="\033[38;5;240m")
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
WAVE = "▁▂▃▄▅▆▇█▇▆▅▄▃▂"


def bar(frac, w=34, fill="█", empty="░", color=C["c"]):
    n = int(frac * w)
    return f"{color}{fill * n}{C['gr']}{empty * (w - n)}{C['r']}"


def minibar(v, mx, w=22):
    n = int((v / mx) * w) if mx else 0
    return f"{C['p']}{'▓' * n}{C['gr']}{'░' * (w - n)}{C['r']}"


def read(path):
    txt = nod = junk = chars = 0
    n = 0
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                n += 1
                if not r.get("ok"):
                    junk += 1
                elif r.get("chars", 0) > 0:
                    txt += 1
                    chars += r["chars"]
                else:
                    nod += 1
    except FileNotFoundError:
        pass
    return n, txt, nod, junk, chars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", default="out/ocr.jsonl")
    ap.add_argument("--total", type=int, required=True)
    ap.add_argument("--fps", type=float, default=12)
    a = ap.parse_args()

    t0 = time.time()
    first_n = None
    frame = 0
    try:
        print("\033[?25l", end="")  # hide cursor
        while True:
            n, txt, nod, junk, chars = read(a.ocr)
            if first_n is None:
                first_n, ft = n, time.time()
            frac = min(1.0, n / a.total)
            el = time.time() - t0
            rate = (n - first_n) / max(0.001, time.time() - ft)
            eta = (a.total - n) / rate if rate > 0.01 else 0
            sp = SPIN[frame % len(SPIN)]
            beam = "".join(WAVE[(frame + i) % len(WAVE)] for i in range(14))
            done = n >= a.total

            os.system("clear")
            print()
            print(f"  {C['b']}{C['o']}╔{'═'*58}╗{C['r']}")
            print(f"  {C['b']}{C['o']}║{C['r']}  {C['b']}APPLE NOTES → VAULT{C['r']}{' '*10}{C['d']}phase 3/7 · vision ocr{C['r']}   {C['o']}║{C['r']}")
            print(f"  {C['b']}{C['o']}╚{'═'*58}╝{C['r']}")
            print()
            status = f"{C['g']}✓ complete{C['r']}" if done else f"{C['y']}{sp}{C['r']} {C['d']}scanning{C['r']}"
            print(f"    {status}   {bar(frac)}  {C['b']}{frac*100:5.1f}%{C['r']}   {n:,} / {a.total:,}")
            print()
            print(f"    {C['c']}{beam}{C['r']}   {C['d']}{chars:,} characters recovered{C['r']}")
            print()
            mx = max(txt, nod, junk, 1)
            print(f"    {C['d']}text found  {C['r']}{txt:>6,}  {minibar(txt, mx)}")
            print(f"    {C['d']}no text     {C['r']}{nod:>6,}  {minibar(nod, mx)}")
            print(f"    {C['d']}junk pixels {C['r']}{junk:>6,}  {minibar(junk, mx)}")
            print()
            em, es = divmod(int(el), 60)
            am, asec = divmod(int(eta), 60)
            eta_s = f"{am:02d}:{asec:02d}" if not done else "--:--"
            print(f"    {C['d']}elapsed{C['r']} {em:02d}:{es:02d}    {C['d']}rate{C['r']} {rate:4.1f}/s    {C['d']}eta{C['r']} {eta_s}")
            print()
            print(f"  {C['gr']}{'ctrl-c to exit · this only reads, it never writes'}{C['r']}")
            if done:
                break
            frame += 1
            time.sleep(1 / a.fps)
    except KeyboardInterrupt:
        pass
    finally:
        print("\033[?25h", end="")  # restore cursor


if __name__ == "__main__":
    main()
