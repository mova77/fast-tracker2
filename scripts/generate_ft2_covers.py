#!/usr/bin/env python3
"""
Generate 10 FastTracker II sample-disk covers:
  320×200, 16-colour indexed PNG-8, exact text overlays.

Pure procedural pixel art (no AI) so labels/stats stay legible.
Output: samples/covers/ft2-disk/01.png … 10.png
"""
from __future__ import annotations

import math
import random
import struct
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "samples" / "covers" / "ft2-disk"
W, H = 320, 200
RELEASE = "2026-07-27"

# ---------------------------------------------------------------------------
# 5×7 pixel font (A-Z 0-9 and a few symbols) — uppercase only
# ---------------------------------------------------------------------------
# Each glyph: 5 columns × 7 rows, bit rows top→bottom as 5-bit ints (MSB left)
_FONT_RAW = {
    " ": [0, 0, 0, 0, 0, 0, 0],
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    "D": [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0E],
    "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "J": [0x01, 0x01, 0x01, 0x01, 0x11, 0x11, 0x0E],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    "N": [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E],
    "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    "X": [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    "Y": [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
    "3": [0x1F, 0x01, 0x02, 0x06, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    "-": [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
    ".": [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C],
    ":": [0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00],
    "/": [0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10],
    "%": [0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13],
    "+": [0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00],
    "*": [0x00, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0x00],
    "(": [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
    ")": [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    "[": [0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E],
    "]": [0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E],
    "!": [0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04],
    "?": [0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04],
    ",": [0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08],
    "'": [0x0C, 0x0C, 0x08, 0x00, 0x00, 0x00, 0x00],
    "#": [0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A],
    "=": [0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00],
    ">": [0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08],
    "<": [0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02],
    "_": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F],
    "|": [0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "&": [0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D],
    "@": [0x0E, 0x11, 0x17, 0x15, 0x17, 0x10, 0x0E],
}


def draw_text(px, x: int, y: int, text: str, color: tuple[int, int, int], scale: int = 1) -> int:
    """Draw uppercase pixel text; return width in pixels."""
    cx = x
    for ch in text.upper():
        rows = _FONT_RAW.get(ch, _FONT_RAW["?"])
        for ry, bits in enumerate(rows):
            for rx in range(5):
                if bits & (0x10 >> rx):
                    for sy in range(scale):
                        for sx in range(scale):
                            xx, yy = cx + rx * scale + sx, y + ry * scale + sy
                            if 0 <= xx < W and 0 <= yy < H:
                                px[xx, yy] = color
        cx += 6 * scale
    return cx - x


def text_width(text: str, scale: int = 1) -> int:
    return len(text) * 6 * scale


def fill_rect(px, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            px[x, y] = color


def hline(px, x0, x1, y, color):
    for x in range(max(0, x0), min(W, x1)):
        if 0 <= y < H:
            px[x, y] = color


def vline(px, x, y0, y1, color):
    for y in range(max(0, y0), min(H, y1)):
        if 0 <= x < W:
            px[x, y] = color


def rect_border(px, x0, y0, x1, y1, color):
    hline(px, x0, x1, y0, color)
    hline(px, x0, x1, y1 - 1, color)
    vline(px, x0, y0, y1, color)
    vline(px, x1 - 1, y0, y1, color)


def copper_bar(px, y0, y1, colors):
    n = len(colors)
    for y in range(y0, y1):
        c = colors[(y - y0) % n]
        hline(px, 0, W, y, c)


def starfield(px, n, rng, color=(80, 80, 120)):
    for _ in range(n):
        x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
        px[x, y] = color


def checker(px, y0, y1, size, c0, c1, perspective=False):
    for y in range(y0, y1):
        for x in range(W):
            if perspective:
                # fake floor: wider cells near bottom
                row = (y - y0) // max(1, size // 2 + (y - y0) // 20)
                col = x // max(1, size + (y - y0) // 15)
            else:
                row, col = y // size, x // size
            px[x, y] = c0 if (row + col) % 2 == 0 else c1


# ---------------------------------------------------------------------------
# Volume data (real pack stats)
# ---------------------------------------------------------------------------

VOLS = {
    1: {
        "title": "FT2 VOL.1 CORE",
        "rate": "8363 HZ",
        "samples": 68,
        "kib": 857,
        "fill": 97,
        "types": ["DRUMS", "SYNTH", "PADS", "ACOUSTIC"],
        "tag": "CORE INSTRUMENTS",
    },
    2: {
        "title": "FT2 VOL.2 EXPAND",
        "rate": "8363 HZ",
        "samples": 66,
        "kib": 848,
        "fill": 96,
        "types": ["DRUM VAR", "ADV SYNTH", "FX", "BREAKS", "UTIL", "WORLD"],
        "tag": "EXPANSION DISK",
    },
    3: {
        "title": "FT2 VOL.3 SYNTH",
        "rate": "16726 HZ",
        "samples": 48,
        "kib": 813,
        "fill": 92,
        "types": ["WAVES", "BASS", "LEADS", "PADS", "KEYS/FM"],
        "tag": "ALL-SYNTH 2X C4",
    },
    4: {
        "title": "FT2 VOL.4 CLUB",
        "rate": "16726 HZ",
        "samples": 47,
        "kib": 851,
        "fill": 97,
        "types": ["CLUB DRM", "DIRTY BASS", "STABS", "BUILDS", "GROOVES"],
        "tag": "ELECTRO REMIX KIT",
    },
}


def stats_lines(v: int) -> list[str]:
    d = VOLS[v]
    return [
        f"SAMPLES: {d['samples']}",
        f"SIZE: {d['kib']} KIB",
        f"FILL: {d['fill']}% DD",
        f"RATE: {d['rate']}",
        f"DATE: {RELEASE}",
    ]


def draw_info_panel(px, x0, y0, vol: int, fg, bg, border, types_fg=None):
    """Standard info box with types + stats."""
    d = VOLS[vol]
    types_fg = types_fg or fg
    # background
    fill_rect(px, x0, y0, x0 + 150, y0 + 118, bg)
    rect_border(px, x0, y0, x0 + 150, y0 + 118, border)
    draw_text(px, x0 + 4, y0 + 3, d["title"], fg, 1)
    hline(px, x0 + 2, x0 + 148, y0 + 12, border)
    draw_text(px, x0 + 4, y0 + 16, "TYPES:", types_fg, 1)
    yy = y0 + 26
    for t in d["types"]:
        draw_text(px, x0 + 8, yy, f"* {t}", types_fg, 1)
        yy += 9
    hline(px, x0 + 2, x0 + 148, yy + 1, border)
    yy += 5
    for line in stats_lines(vol):
        draw_text(px, x0 + 4, yy, line, fg, 1)
        yy += 9


def save_png8(img: Image.Image, path: Path) -> int:
    img = img.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True, compress_level=9)
    return path.stat().st_size


# ---------------------------------------------------------------------------
# 10 cover designs
# ---------------------------------------------------------------------------

def cover_01_floppy_void(vol: int = 1) -> Image.Image:
    """Starfield + floppy badge + FT2 panel."""
    img = Image.new("RGB", (W, H), (8, 0, 24))
    px = img.load()
    rng = random.Random(1)
    starfield(px, 120, rng, (100, 80, 160))
    starfield(px, 40, rng, (200, 200, 255))
    # floppy body
    fill_rect(px, 18, 40, 120, 160, (40, 40, 50))
    rect_border(px, 18, 40, 120, 160, (180, 180, 200))
    fill_rect(px, 30, 52, 108, 100, (20, 20, 30))
    fill_rect(px, 48, 110, 90, 148, (60, 60, 80))
    fill_rect(px, 70, 125, 85, 140, (15, 15, 20))
    draw_text(px, 28, 58, "FT2", (0, 255, 200), 2)
    draw_text(px, 28, 78, f"VOL {vol}", (255, 200, 0), 1)
    draw_text(px, 4, 4, "FASTTRACKER II", (0, 255, 180), 1)
    draw_text(px, 4, 14, "SAMPLE DISK ARCHIVE", (180, 120, 255), 1)
    draw_info_panel(px, 140, 30, vol, (0, 255, 180), (10, 0, 30), (0, 200, 160))
    copper_bar(px, 188, 200, [(80 + i * 10, 0, 120 + i * 5) for i in range(12)])
    draw_text(px, 8, 190, f"REL {RELEASE}", (255, 255, 100), 1)
    return img


def cover_02_scope_loader(vol: int = 1) -> Image.Image:
    """Tracker scope loader screen."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    px = img.load()
    # grid
    for y in range(H):
        for x in range(W):
            if x % 8 == 0 or y % 8 == 0:
                px[x, y] = (0, 28, 0)
    cols = [(0, 220, 255), (255, 220, 0), (80, 255, 80), (255, 80, 220)]
    labels = ["DRM", "BAS", "PAD", "LED"]
    pw, ph = 68, 55
    x0, y0 = 12, 38
    rng = random.Random(2)
    for i, col in enumerate(cols):
        px0 = x0 + i * (pw + 8)
        rect_border(px, px0, y0, px0 + pw, y0 + ph, col)
        draw_text(px, px0 + 4, y0 + 2, f"CH{i+1}:{labels[i]}", col, 1)
        mid = y0 + ph // 2 + 6
        for x in range(1, pw - 1):
            t = x / pw
            amp = int(14 * math.sin(t * (12 + i * 4) + i) * (0.4 + 0.6 * abs(math.sin(t * 5))))
            if i == 3:
                amp = int(12 * (rng.random() - 0.5))
            y = max(y0 + 12, min(y0 + ph - 2, mid - amp))
            for yy in range(min(y, mid), max(y, mid) + 1):
                px[px0 + x, yy] = col
    draw_text(px, 8, 4, "FASTTRACKER II  //  LOADER", (180, 255, 80), 1)
    draw_text(px, 8, 14, VOLS[vol]["title"], (255, 255, 0), 1)
    draw_text(px, 8, 24, VOLS[vol]["tag"], (0, 200, 255), 1)
    # bottom stats strip
    fill_rect(px, 0, 110, W, 188, (0, 0, 0))
    copper_bar(px, 100, 110, [(120 + i * 8, 60 + i * 4, 0) for i in range(10)])
    types = " + ".join(VOLS[vol]["types"])
    draw_text(px, 8, 118, f"TYPES: {types[:44]}", (0, 255, 160), 1)
    if len(types) > 44:
        draw_text(px, 8, 128, types[44:88], (0, 255, 160), 1)
        sy = 140
    else:
        sy = 130
    for i, line in enumerate(stats_lines(vol)):
        draw_text(px, 8, sy + i * 10, line, (200, 255, 100), 1)
    draw_text(px, 200, 170, "PRESS FIRE", (255, 80, 80), 1)
    draw_text(px, 8, 190, f"FT2 SAMPLE DISK  |  {RELEASE}", (100, 200, 100), 1)
    return img


def cover_03_plasma_panel(vol: int = 3) -> Image.Image:
    """Plasma-ish background + overlay."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            v = (
                math.sin(x / 18.0)
                + math.sin(y / 14.0)
                + math.sin((x + y) / 22.0)
                + math.sin(math.sqrt(x * x + y * y) / 16.0)
            )
            t = (v + 4) / 8
            r = int(40 + 180 * abs(math.sin(t * math.pi)))
            g = int(20 + 80 * abs(math.sin(t * math.pi + 1)))
            b = int(80 + 150 * abs(math.cos(t * math.pi)))
            px[x, y] = (r, g, b)
    fill_rect(px, 8, 8, 312, 28, (0, 0, 0))
    draw_text(px, 12, 12, f"FASTTRACKER II  {VOLS[vol]['title']}", (255, 255, 0), 1)
    draw_info_panel(px, 160, 40, vol, (255, 255, 200), (0, 0, 0), (255, 100, 200), (0, 255, 255))
    draw_text(px, 12, 180, VOLS[vol]["tag"], (255, 255, 255), 1)
    draw_text(px, 12, 190, f"RELEASE {RELEASE}", (255, 220, 100), 1)
    return img


def cover_04_wireframe(vol: int = 2) -> Image.Image:
    """Checker floor + skyline + panel."""
    img = Image.new("RGB", (W, H), (10, 0, 40))
    px = img.load()
    rng = random.Random(4)
    starfield(px, 60, rng, (120, 100, 200))
    # skyline
    for i in range(18):
        bx = 5 + i * 18
        bh = 30 + (i * 17 + 11) % 50
        c = [(0, 255, 255), (255, 0, 255), (255, 255, 0)][i % 3]
        rect_border(px, bx, 90 - bh, bx + 14, 90, c)
        for wy in range(90 - bh + 4, 88, 6):
            for wx in range(bx + 2, bx + 12, 4):
                if 0 <= wx < W and 0 <= wy < H:
                    px[wx, wy] = c
    checker(px, 90, 170, 12, (40, 0, 80), (200, 200, 0), perspective=True)
    fill_rect(px, 0, 0, W, 18, (0, 0, 0))
    draw_text(px, 4, 5, f"FT2  {VOLS[vol]['title']}  SAMPLE DISK", (255, 255, 0), 1)
    draw_info_panel(px, 8, 50, vol, (0, 255, 255), (0, 0, 20), (255, 0, 255))
    draw_text(px, 170, 180, f"REL {RELEASE}", (255, 255, 100), 1)
    draw_text(px, 170, 190, "FASTTRACKER II", (0, 255, 180), 1)
    return img


def cover_05_chip_phosphor(vol: int = 3) -> Image.Image:
    """Green phosphor skull-ish circuit + stats."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    px = img.load()
    rng = random.Random(5)
    # circuit grid
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            if rng.random() < 0.08:
                px[x, y] = (0, 60, 0)
    # faux skull oval
    for y in range(30, 120):
        for x in range(30, 130):
            dx, dy = (x - 80) / 40, (y - 70) / 45
            if dx * dx + dy * dy < 1:
                px[x, y] = (0, 40 + int(40 * (1 - dx * dx - dy * dy)), 0)
    # eyes
    fill_rect(px, 55, 55, 70, 68, (0, 0, 0))
    fill_rect(px, 90, 55, 105, 68, (0, 0, 0))
    fill_rect(px, 70, 85, 90, 100, (0, 0, 0))
    # waveforms as teeth
    for i in range(8):
        x = 55 + i * 6
        for y in range(105, 115):
            px[x, y] = (0, 200, 0)
    draw_text(px, 8, 4, "FASTTRACKER II", (0, 255, 80), 1)
    draw_text(px, 8, 14, VOLS[vol]["title"], (180, 255, 100), 1)
    draw_info_panel(px, 150, 30, vol, (0, 255, 100), (0, 10, 0), (0, 180, 60))
    draw_text(px, 8, 180, VOLS[vol]["tag"], (0, 200, 80), 1)
    draw_text(px, 8, 190, f"RELEASE {RELEASE}", (100, 255, 100), 1)
    return img


def cover_06_roto_frame(vol: int = 2) -> Image.Image:
    """Rotozoomer-ish checkers + cracktro frame."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    px = img.load()
    cx, cy = W // 2, H // 2
    for y in range(H):
        for x in range(W):
            dx, dy = x - cx, y - cy
            ang = math.atan2(dy, dx) + 0.4
            dist = math.sqrt(dx * dx + dy * dy) / 12
            u = int(dist * math.cos(ang) * 3)
            v = int(dist * math.sin(ang) * 3)
            c = (40, 40, 200) if (u + v) % 2 == 0 else (200, 40, 40)
            if (u // 2 + v // 2) % 2:
                c = (220, 200, 40) if c[0] > 100 else (20, 20, 100)
            px[x, y] = c
    # frame
    rect_border(px, 2, 2, W - 2, H - 2, (255, 0, 255))
    rect_border(px, 4, 4, W - 4, H - 4, (0, 255, 255))
    fill_rect(px, 20, 20, 300, 40, (0, 0, 0))
    draw_text(px, 28, 26, f"FT2 CRACKTRO DISK  {VOLS[vol]['title']}", (255, 255, 0), 1)
    fill_rect(px, 40, 50, 280, 165, (0, 0, 0))
    rect_border(px, 40, 50, 280, 165, (255, 100, 255))
    draw_text(px, 48, 56, "SAMPLE TYPES:", (0, 255, 255), 1)
    yy = 68
    for t in VOLS[vol]["types"]:
        draw_text(px, 56, yy, f"> {t}", (255, 255, 255), 1)
        yy += 10
    for i, line in enumerate(stats_lines(vol)):
        draw_text(px, 48, 125 + i * 9, line, (255, 255, 100), 1)
    draw_text(px, 60, 180, f"FASTTRACKER II  |  {RELEASE}", (0, 255, 180), 1)
    return img


def cover_07_vector_balls(vol: int = 3) -> Image.Image:
    """Checker floor + vector balls + panel."""
    img = Image.new("RGB", (W, H), (0, 0, 20))
    px = img.load()
    checker(px, 110, H, 16, (30, 30, 30), (200, 200, 200))
    # balls
    balls = [(80, 90, 22, (255, 80, 200)), (160, 70, 28, (80, 200, 255)),
             (230, 95, 18, (255, 220, 40)), (120, 100, 14, (100, 255, 100))]
    for bx, by, r, col in balls:
        for y in range(by - r, by + r):
            for x in range(bx - r, bx + r):
                if 0 <= x < W and 0 <= y < H:
                    dx, dy = x - bx, y - by
                    if dx * dx + dy * dy <= r * r:
                        # simple shade
                        shade = 0.5 + 0.5 * ((dx + dy) / (2 * r))
                        shade = max(0.25, min(1.0, shade))
                        px[x, y] = tuple(int(c * shade) for c in col)
        # shadow
        for y in range(by + r - 2, by + r + 6):
            for x in range(bx - r // 2, bx + r // 2):
                if 0 <= x < W and 110 <= y < H:
                    px[x, y] = (20, 20, 20)
    fill_rect(px, 0, 0, W, 32, (0, 0, 0))
    draw_text(px, 6, 4, "FASTTRACKER II SAMPLE DISK", (255, 255, 0), 1)
    draw_text(px, 6, 16, VOLS[vol]["title"] + "  //  " + VOLS[vol]["tag"], (0, 255, 255), 1)
    fill_rect(px, 4, 140, 200, 196, (0, 0, 0))
    rect_border(px, 4, 140, 200, 196, (255, 0, 255))
    draw_text(px, 8, 144, "TYPES: " + ",".join(VOLS[vol]["types"][:3]), (255, 200, 255), 1)
    yy = 156
    for line in stats_lines(vol):
        draw_text(px, 8, yy, line, (200, 255, 100), 1)
        yy += 9
    return img


def cover_08_spaceport(vol: int = 1) -> Image.Image:
    """Loader / spaceport theme."""
    img = Image.new("RGB", (W, H), (15, 0, 40))
    px = img.load()
    rng = random.Random(8)
    starfield(px, 100, rng, (120, 100, 180))
    # station
    fill_rect(px, 200, 50, 290, 120, (60, 40, 100))
    rect_border(px, 200, 50, 290, 120, (0, 255, 255))
    fill_rect(px, 210, 60, 230, 75, (255, 200, 0))
    fill_rect(px, 240, 80, 270, 100, (0, 200, 255))
    draw_text(px, 212, 105, "DOCK", (255, 255, 0), 1)
    # ship triangle
    for y in range(70, 110):
        wspan = (y - 70) // 2
        for x in range(60 - wspan, 60 + wspan):
            if 0 <= x < W:
                px[x, y] = (20, 20, 30)
        if 0 <= 60 < W:
            px[60, y] = (0, 255, 255)
    draw_text(px, 8, 4, "FT2 SPACEPORT LOADER", (255, 160, 40), 1)
    draw_text(px, 8, 14, VOLS[vol]["title"], (0, 255, 255), 1)
    # progress
    draw_text(px, 40, 120, "LOADING SAMPLES...", (0, 255, 180), 1)
    fill_rect(px, 40, 132, 200, 142, (40, 40, 40))
    fill_rect(px, 40, 132, 40 + int(160 * VOLS[vol]["fill"] / 100), 142, (0, 255, 100))
    rect_border(px, 40, 132, 200, 142, (255, 255, 255))
    draw_text(px, 210, 134, f"{VOLS[vol]['fill']}%", (255, 255, 0), 1)
    fill_rect(px, 8, 150, 310, 196, (0, 0, 20))
    rect_border(px, 8, 150, 310, 196, (255, 100, 0))
    draw_text(px, 12, 154, "TYPES: " + " / ".join(VOLS[vol]["types"]), (255, 200, 100), 1)
    draw_text(px, 12, 166, f"SAMPLES {VOLS[vol]['samples']}  SIZE {VOLS[vol]['kib']}KIB  "
              f"RATE {VOLS[vol]['rate']}", (200, 255, 200), 1)
    draw_text(px, 12, 178, f"FASTTRACKER II  |  RELEASE {RELEASE}", (255, 255, 100), 1)
    draw_text(px, 12, 188, VOLS[vol]["tag"], (0, 200, 255), 1)
    return img


def cover_09_dancefloor(vol: int = 4) -> Image.Image:
    """Club dancefloor top-down."""
    img = Image.new("RGB", (W, H), (20, 0, 40))
    px = img.load()
    # floor tiles
    colors = [
        (255, 0, 128), (0, 255, 255), (128, 0, 255), (255, 255, 0),
        (0, 255, 128), (255, 80, 0), (80, 80, 255), (255, 0, 255),
    ]
    ox, oy, ts = 70, 40, 14
    for row in range(8):
        for col in range(8):
            c = colors[(row + col) % len(colors)]
            fill_rect(px, ox + col * ts, oy + row * ts,
                      ox + col * ts + ts - 1, oy + row * ts + ts - 1, c)
    # speakers
    for sx in (20, 270):
        fill_rect(px, sx, 50, sx + 30, 140, (40, 40, 40))
        rect_border(px, sx, 50, sx + 30, 140, (255, 200, 0))
        fill_rect(px, sx + 6, 60, sx + 24, 78, (200, 200, 50))
        fill_rect(px, sx + 6, 90, sx + 24, 120, (200, 200, 50))
    # dancers dots
    rng = random.Random(9)
    for _ in range(12):
        x = rng.randint(ox, ox + 8 * ts)
        y = rng.randint(oy, oy + 8 * ts)
        fill_rect(px, x, y, x + 3, y + 5, colors[rng.randint(0, 7)])
    fill_rect(px, 0, 0, W, 28, (0, 0, 0))
    draw_text(px, 6, 4, f"FT2  {VOLS[vol]['title']}", (255, 0, 200), 1)
    draw_text(px, 6, 14, "CLUB REMIX SAMPLE DISK", (0, 255, 255), 1)
    fill_rect(px, 0, 155, W, H, (0, 0, 0))
    draw_text(px, 6, 158, "TYPES: " + " ".join(VOLS[vol]["types"]), (255, 255, 100), 1)
    draw_text(px, 6, 170, f"N={VOLS[vol]['samples']}  {VOLS[vol]['kib']}KIB  "
              f"{VOLS[vol]['fill']}%DD  {VOLS[vol]['rate']}", (0, 255, 160), 1)
    draw_text(px, 6, 182, f"FASTTRACKER II  RELEASE {RELEASE}", (255, 200, 255), 1)
    draw_text(px, 6, 192, VOLS[vol]["tag"], (255, 80, 180), 1)
    return img


def cover_10_cathedral(vol: int = 2) -> Image.Image:
    """Cathedral / MOD scroll aisle."""
    img = Image.new("RGB", (W, H), (15, 0, 30))
    px = img.load()
    # arches perspective
    for i in range(6):
        y = 20 + i * 12
        x0 = 40 + i * 8
        x1 = W - 40 - i * 8
        rect_border(px, x0, y, x1, y + 10, (80, 40, 120))
    # stained glass
    glass = [(200, 50, 200), (50, 200, 200), (200, 200, 50), (50, 100, 200)]
    for i, g in enumerate(glass):
        gx = 50 + i * 55
        fill_rect(px, gx, 35, gx + 40, 80, g)
        rect_border(px, gx, 35, gx + 40, 80, (255, 255, 100))
        # mini skull
        fill_rect(px, gx + 12, 48, gx + 28, 62, (40, 0, 40))
    # floor scroller path
    for y in range(100, 180):
        for x in range(100, 220):
            px[x, y] = (30, 0, 50) if ((x + y) // 4) % 2 == 0 else (50, 20, 70)
    draw_text(px, 105, 130, "FT2 SAMPLE", (0, 255, 100), 1)
    draw_text(px, 105, 140, "ARCHIVE...", (0, 255, 100), 1)
    fill_rect(px, 0, 0, W, 18, (0, 0, 0))
    draw_text(px, 4, 5, f"FASTTRACKER II  {VOLS[vol]['title']}", (180, 255, 80), 1)
    fill_rect(px, 0, 170, W, H, (0, 0, 0))
    draw_text(px, 4, 174, "TYPES: " + "/".join(VOLS[vol]["types"][:4]), (200, 150, 255), 1)
    draw_text(px, 4, 184, f"SAMP {VOLS[vol]['samples']}  {VOLS[vol]['kib']}K  "
              f"{VOLS[vol]['fill']}%  {VOLS[vol]['rate']}  REL {RELEASE}", (255, 255, 100), 1)
    draw_text(px, 4, 193, VOLS[vol]["tag"], (0, 200, 255), 1)
    return img


COVERS = [
    ("01-floppy-void-vol1", lambda: cover_01_floppy_void(1)),
    ("02-scope-loader-vol1", lambda: cover_02_scope_loader(1)),
    ("03-plasma-vol3", lambda: cover_03_plasma_panel(3)),
    ("04-wireframe-vol2", lambda: cover_04_wireframe(2)),
    ("05-chip-phosphor-vol3", lambda: cover_05_chip_phosphor(3)),
    ("06-roto-frame-vol2", lambda: cover_06_roto_frame(2)),
    ("07-vector-balls-vol3", lambda: cover_07_vector_balls(3)),
    ("08-spaceport-vol1", lambda: cover_08_spaceport(1)),
    ("09-dancefloor-vol4", lambda: cover_09_dancefloor(4)),
    ("10-cathedral-vol2", lambda: cover_10_cathedral(2)),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Generating 10 FT2 covers → {OUT.relative_to(REPO)}/")
    print(f"  {W}×{H}, 16-colour PNG-8, release {RELEASE}")
    total = 0
    for name, fn in COVERS:
        img = fn()
        path = OUT / f"{name}.png"
        n = save_png8(img, path)
        total += n
        print(f"  {path.name:40s} {n/1024:5.1f} KiB")
    print(f"Total: {total/1024:.1f} KiB")

    # Manifest
    lines = [
        "# FT2 Disk Covers (procedural)",
        "",
        f"320×200 · 16-colour PNG-8 · release **{RELEASE}**",
        "",
        "Generated by `scripts/generate_ft2_covers.py` — exact text/stats (no AI).",
        "",
        "| # | File | Volume theme |",
        "|---|------|--------------|",
    ]
    themes = [
        "1 Floppy void — Vol.1 core",
        "2 Scope loader — Vol.1",
        "3 Plasma — Vol.3 synth",
        "4 Wireframe city — Vol.2",
        "5 Chip phosphor — Vol.3",
        "6 Rotozoomer frame — Vol.2",
        "7 Vector balls — Vol.3",
        "8 Spaceport loader — Vol.1",
        "9 Raster dancefloor — Vol.4 club",
        "10 MOD cathedral — Vol.2",
    ]
    for i, ((name, _), theme) in enumerate(zip(COVERS, themes), 1):
        lines.append(f"| {i} | `{name}.png` | {theme} |")
    lines += [
        "",
        "## Overlay contents",
        "",
        "Each cover includes:",
        "- **FastTracker II / FT2** branding",
        "- **Vol 1–4** title + tagline",
        "- **Sample types** (category list)",
        f"- **Stats**: sample count, KiB, % of 880 KiB DD, sample rate",
        f"- **Release date**: {RELEASE}",
        "",
        "## Regenerate",
        "",
        "```bash",
        "python3 scripts/generate_ft2_covers.py",
        "```",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Manifest: {OUT.relative_to(REPO)}/README.md")


if __name__ == "__main__":
    main()
