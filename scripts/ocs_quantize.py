#!/usr/bin/env python3
"""
Convert images to Amiga OCS-like targets:
  320×256, 32 colours, PNG-8
  Palette channels snapped to 4-bit (12-bit Amiga colour space).

Usage:
  python3 scripts/ocs_quantize.py input.jpg ... --out samples/covers/ocs-frazetta
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

OCS_W, OCS_H = 320, 256


def snap_12bit(img: Image.Image) -> Image.Image:
    """Snap RGB to Amiga 12-bit (4 bits per channel)."""
    img = img.convert("RGB")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            # 4-bit: 0,17,34,...,255
            r = (r >> 4) * 17
            g = (g >> 4) * 17
            b = (b >> 4) * 17
            px[x, y] = (r, g, b)
    return img


def to_ocs(src: Path, dst: Path, colors: int = 32, dither: bool = True) -> int:
    im = Image.open(src).convert("RGB")
    # Fit into 320x256 preserving aspect with letterbox black (OCS screen)
    im.thumbnail((OCS_W, OCS_H), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (OCS_W, OCS_H), (0, 0, 0))
    ox = (OCS_W - im.size[0]) // 2
    oy = (OCS_H - im.size[1]) // 2
    canvas.paste(im, (ox, oy))
    canvas = snap_12bit(canvas)
    dith = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    q = canvas.quantize(colors=colors, method=Image.Quantize.MAXCOVERAGE, dither=dith)
    # Re-snap palette entries to 12-bit Amiga colour space
    pal = q.getpalette() or []
    new_pal = []
    for i in range(0, min(len(pal), 768), 3):
        if i + 2 >= len(pal):
            break
        r, g, b = pal[i], pal[i + 1], pal[i + 2]
        new_pal.extend([(r >> 4) * 17, (g >> 4) * 17, (b >> 4) * 17])
    while len(new_pal) < 768:
        new_pal.append(0)
    q.putpalette(new_pal[:768])
    dst.parent.mkdir(parents=True, exist_ok=True)
    q.save(dst, format="PNG", optimize=True, compress_level=9)
    return dst.stat().st_size


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--colors", type=int, default=32)
    ap.add_argument("--names", nargs="*", help="Output basenames without extension")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(args.inputs):
        name = args.names[i] if args.names and i < len(args.names) else f"{i+1:02d}-{src.stem}"
        dst = args.out / f"{name}.png"
        n = to_ocs(src, dst, args.colors)
        print(f"  {dst.name:40s} {n/1024:5.1f} KiB  from {src.name}")


if __name__ == "__main__":
    main()
