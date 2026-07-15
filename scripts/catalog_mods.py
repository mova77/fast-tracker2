#!/usr/bin/env python3
"""Print MOD/XM header stats for all game modules under mods/."""
import struct
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]
MODS = REPO / "mods"


def parse_mod(p: Path):
    d = p.read_bytes()
    if len(d) < 1084:
        return None
    marker = d[1080:1084].decode("latin-1", errors="replace")
    ch = 4
    if marker == "FLT8":
        ch = 8
    elif marker.endswith("CHN") and marker[0].isdigit():
        ch = int(marker[0])
    elif len(marker) >= 2 and marker[:2].isdigit() and marker[2:4] in ("CH", "CN"):
        ch = int(marker[:2])
    slen = d[950]
    orders = [d[952 + i] for i in range(min(slen, 128))]
    pat = max(orders) + 1 if orders else 0
    title = d[0:20].decode("latin-1", errors="replace").strip().replace("\x00", "")
    return {"fmt": "MOD", "ch": ch, "pat": pat, "len": slen, "size": len(d), "title": title}


def parse_xm(p: Path):
    d = p.read_bytes()
    if len(d) < 80 or d[:17] != b"Extended Module: ":
        return None
    slen, _, ch, pat, _, _, speed, bpm = struct.unpack_from("<8H", d, 60)
    title = d[17:37].decode("latin-1", errors="replace").strip().replace("\x00", "")
    return {"fmt": "XM", "ch": ch, "pat": pat, "len": slen, "size": len(d),
            "bpm": bpm, "speed": speed, "title": title}


def main():
    by_game = defaultdict(list)
    for p in sorted(MODS.rglob("*")):
        if p.suffix.lower() not in (".mod", ".xm"):
            continue
        game = p.relative_to(MODS).parts[0]
        info = parse_xm(p) if p.suffix.lower() == ".xm" else parse_mod(p)
        if info:
            info["file"] = p.name
            by_game[game].append(info)

    print(f"MOD/XM catalog under {MODS}\n")
    for game in sorted(by_game):
        xs = by_game[game]
        print(f"## {game} ({len(xs)} files)")
        print(f"{'File':<36} {'Fmt':<4} {'Ch':>2} {'Pat':>4} {'Len':>4} {'Size':>8}  Title")
        for x in sorted(xs, key=lambda z: z["file"].lower()):
            print(f"{x['file']:<36} {x['fmt']:<4} {x['ch']:>2} {x['pat']:>4} {x['len']:>4} "
                  f"{x['size']//1024:>7}K  {x['title'][:24]}")
        print()


if __name__ == "__main__":
    main()