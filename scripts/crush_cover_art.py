#!/usr/bin/env python3
"""
Crush cover art for Amiga-disk sample volumes.

Goal: keep demoscene look, fit a few dozen KB (hard cap 100 KiB).

Strategy (classic demoscene constraints):
  - Resolution: 320×200 (Amiga lowres PAL/NTSC-ish) — not 4K pixels
  - Colour: indexed 16 or 32 colours (4–5 bits effective via palette)
  - Format: PNG-8 (indexed). Practical on modern OS, tiny, lossless palette.
    IFF/ILBM is more "pure Amiga" but awkward to view; TGA is bulkier.
  - Dither: optional Floyd–Steinberg for smoother gradients on 16-col

  "4K intro" in demoscene = 4096-byte executable, NOT 3840×2160 video.
  These covers are *inspired* by that size budget.

Usage:
  python3 scripts/crush_cover_art.py
  python3 scripts/crush_cover_art.py --colors 16 --size 320x200
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
PROPOSALS = REPO / "samples" / "covers" / "proposals"
OUT = REPO / "samples" / "covers" / "amiga"

# Keep list — originals stay in proposals/
KEEP = [
    "01-floppy-of-the-void.jpg",
    "02-scope-grid.jpg",
    "07-vector-ball-swarm.jpg",
    "08-spaceport-loader.jpg",
    "09-raster-dancefloor.jpg",
    "10-mod-scroll-cathedral.jpg",
]


def parse_size(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def crush(
    src: Path,
    dst: Path,
    size: tuple[int, int],
    colors: int,
    dither: bool,
) -> int:
    im = Image.open(src).convert("RGB")
    # Nearest-neighbor keeps hard pixel edges when downscaling AI art
    im = im.resize(size, Image.Resampling.NEAREST)
    # Adaptive palette quantize
    method = Image.Quantize.MEDIANCUT
    dith = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    im = im.quantize(colors=colors, method=method, dither=dith)
    dst.parent.mkdir(parents=True, exist_ok=True)
    # compress_level 9 + optimize for smallest PNG-8
    im.save(dst, format="PNG", optimize=True, compress_level=9)
    return dst.stat().st_size


def write_loader_4k_style(dst: Path, size: tuple[int, int] = (320, 200)) -> int:
    """
    Procedural 'scope grid' loader screen — pure pixels, no photo source.
    Feels like a tiny intro / disk loader; usually only a few KB.
    """
    w, h = size
    # Build RGB then quantize to 16
    img = Image.new("RGB", (w, h), (0, 0, 0))
    px = img.load()

    # Palette-ish colours
    BG = (0, 0, 0)
    GRID = (0, 40, 0)
    COPPER = [(40 + i * 8, 20 + i * 4, 0) for i in range(16)]
    CH = [
        (0, 220, 255),   # cyan
        (255, 220, 0),   # yellow
        (80, 255, 80),   # green
        (255, 80, 220),  # magenta
    ]

    # Grid
    for y in range(h):
        for x in range(w):
            if x % 8 == 0 or y % 8 == 0:
                px[x, y] = GRID

    # Four scope panels
    panel_w, panel_h = 70, 70
    gap = 6
    total_w = 4 * panel_w + 3 * gap
    x0 = (w - total_w) // 2
    y0 = 36
    import math
    import random
    rng = random.Random(42)

    for i, col in enumerate(CH):
        px0 = x0 + i * (panel_w + gap)
        # border
        for t in range(panel_w):
            px[px0 + t, y0] = col
            px[px0 + t, y0 + panel_h - 1] = col
        for t in range(panel_h):
            px[px0, y0 + t] = col
            px[px0 + panel_w - 1, y0 + t] = col
        # fake waveform
        mid = y0 + panel_h // 2
        for x in range(1, panel_w - 1):
            t = x / panel_w
            if i == 0:
                amp = int(22 * math.sin(t * 18) * math.exp(-abs(t - 0.5) * 2))
            elif i == 1:
                amp = int(18 * math.sin(t * 30) * (0.5 + 0.5 * math.sin(t * 7)))
            elif i == 2:
                amp = int(8 * (1 if (int(t * 16) % 2 == 0) else -1) * (1 - abs(t - 0.5)))
            else:
                amp = int(20 * (rng.random() - 0.5) * (1 - abs(t - 0.5) * 1.5))
            y = max(y0 + 1, min(y0 + panel_h - 2, mid - amp))
            # vertical fill to mid (scope style)
            lo, hi = sorted((y, mid))
            for yy in range(lo, hi + 1):
                px[px0 + x, yy] = col

    # Copper bars bottom
    bar_y0 = h - 40
    for y in range(bar_y0, h - 12):
        c = COPPER[(y - bar_y0) % len(COPPER)]
        for x in range(w):
            px[x, y] = c

    # Title bar pixels (block letters approximate via bars)
    for y in range(8, 24):
        for x in range(40, w - 40):
            if (x + y) % 3 == 0:
                px[x, y] = (180, 255, 80)

    # Quantize 16
    img = img.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, format="PNG", optimize=True, compress_level=9)
    return dst.stat().st_size


def main() -> None:
    ap = argparse.ArgumentParser(description="Crush cover art for Amiga DD budgets")
    ap.add_argument("--size", default="320x200", help="WxH (default 320x200 Amiga lores)")
    ap.add_argument("--colors", type=int, default=16, choices=[8, 16, 32, 64],
                    help="Palette size (default 16)")
    ap.add_argument("--dither", action="store_true", help="Floyd–Steinberg dither")
    ap.add_argument("--max-kb", type=int, default=100, help="Warn if over this many KiB")
    args = ap.parse_args()
    size = parse_size(args.size)

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Target: {size[0]}×{size[1]}, {args.colors} colours, PNG-8, dither={args.dither}")
    print(f"Source proposals kept intact under {PROPOSALS.relative_to(REPO)}")
    print()

    rows = []
    for name in KEEP:
        src = PROPOSALS / name
        if not src.exists():
            print(f"  SKIP missing {name}")
            continue
        stem = Path(name).stem
        dst = OUT / f"{stem}.png"
        nbytes = crush(src, dst, size, args.colors, args.dither)
        kib = nbytes / 1024
        flag = " OK" if kib <= args.max_kb else " OVER"
        print(f"  {dst.name:40s} {kib:6.1f} KiB{flag}")
        rows.append((dst.name, kib))

    # Procedural loader (4k-intro budget aesthetic)
    loader = OUT / "02-scope-grid-loader4k.png"
    n = write_loader_4k_style(loader, size)
    print(f"  {loader.name:40s} {n/1024:6.1f} KiB  (procedural loader)")
    rows.append((loader.name, n / 1024))

    total = sum(k for _, k in rows)
    print()
    print(f"Total selected covers: {total:.1f} KiB "
          f"({100 * total * 1024 / (880 * 1024):.1f}% of one 880 KiB floppy)")
    print(f"Output: {OUT.relative_to(REPO)}/")
    print()
    print("Why PNG-8 not JPEG/TGA/IFF:")
    print("  • JPEG: bad for flat pixel art (mosquito noise), still larger at this size")
    print("  • TGA: simple but rarely smaller; no native palette savings on disk")
    print("  • IFF ILBM: authentic Amiga, poor browser/OS preview — optional later")
    print("  • PNG-8: indexed palette + deflate = tiny + universal viewers")


if __name__ == "__main__":
    main()
