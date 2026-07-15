#!/usr/bin/env python3
"""
Compose 'Neon Overdrive' — an original XM inspired by the mods/ Amiga game collection
(Lotus 3 racing drive, Turrican heroic arps, Agony atmosphere, 4-channel ProTracker layout).
Drives ft2-clone --mcp via JSON-RPC on stdin.
"""
import base64
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FT2 = REPO / "release/macos/ft2-clone-macos.app/Contents/MacOS/ft2-clone-macos"
OUT_DIR = REPO / "mods" / "Neon Overdrive"
OUT_XM = OUT_DIR / "neon_overdrive.xm"

NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
        "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def pitch(octave: int, name: str) -> int:
    return octave * 12 + NOTE[name] + 1  # FT2 pattern byte


def b64_pcm_int16(samples):
    return base64.b64encode(struct.pack("<" + "h" * len(samples), *samples)).decode()


def gen_kick(n=500):
    out = []
    for i in range(n):
        t = i / 8363.0
        env = math.exp(-t * 40)
        pitch_env = 80 * math.exp(-t * 25)
        s = math.sin(2 * math.pi * (60 + pitch_env) * t) * env
        out.append(int(max(-32767, min(32767, s * 28000))))
    return out


def gen_snare(n=2400):
    import random
    rng = random.Random(42)
    out = []
    for i in range(n):
        t = i / 8363.0
        env = math.exp(-t * 12) * (1 - math.exp(-t * 200))
        noise = (rng.random() * 2 - 1) * env
        tone = math.sin(2 * math.pi * 180 * t) * env * 0.35
        out.append(int(max(-32767, min(32767, (noise + tone) * 22000))))
    return out


def gen_hihat(n=1200):
    import random
    rng = random.Random(99)
    out = []
    for i in range(n):
        t = i / 8363.0
        env = math.exp(-t * 35)
        noise = (rng.random() * 2 - 1) * env
        out.append(int(max(-32767, min(32767, noise * 12000))))
    return out


def gen_bass(n=4096):
    out = []
    for i in range(n):
        phase = (i / n) * 2 * math.pi
        saw = 2 * (phase / (2 * math.pi) % 1) - 1
        sq = 1 if math.sin(phase) > 0 else -1
        s = saw * 0.55 + sq * 0.15
        out.append(int(max(-32767, min(32767, s * 14000))))
    return out


def gen_pad(n=8192):
    out = []
    freqs = [261.63, 329.63, 392.00]  # C minor triad overtones
    for i in range(n):
        t = i / 8363.0
        s = sum(math.sin(2 * math.pi * f * t) for f in freqs) / 3
        s *= 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)
        out.append(int(max(-32767, min(32767, s * 10000))))
    return out


def gen_lead(n=4096):
    out = []
    for i in range(n):
        phase = (i / n) * 4 * math.pi
        s = math.sin(phase) + 0.35 * math.sin(phase * 2)
        out.append(int(max(-32767, min(32767, s * 11000))))
    return out


def rpc(id_, method, params=None):
    msg = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg, separators=(",", ":"))


def tool(id_, name, args):
    return rpc(id_, "tools/call", {"name": name, "arguments": args})


def cell(id_, pattern, row, channel, **kwargs):
    args = {"pattern": pattern, "row": row, "channel": channel}
    args.update(kwargs)
    return tool(id_, "pattern_set_cell", args)


# --- musical material ---
# C minor / Ab major lift (Lotus/Turrican heroic minor)
BASS_SEQ = [
    pitch(2, "C"), pitch(2, "C"), pitch(2, "G"), pitch(2, "G"),
    pitch(2, "A#"), pitch(2, "A#"), pitch(2, "G"), pitch(2, "G"),
    pitch(2, "F"), pitch(2, "F"), pitch(2, "G"), pitch(2, "G"),
    pitch(2, "C"), pitch(2, "C"), pitch(2, "G"), pitch(2, "G"),
]

CHORD_STABS = [
    (pitch(3, "C"), pitch(3, "D#"), pitch(3, "G")),  # Cm
    (pitch(3, "G"), pitch(3, "A#"), pitch(3, "D")),  # Gm
    (pitch(3, "A#"), pitch(3, "D"), pitch(3, "F")),  # Eb
    (pitch(3, "F"), pitch(3, "A"), pitch(3, "C")),   # F
]

LEAD_HOOK = [
    pitch(4, "G"), pitch(4, "A#"), pitch(4, "C"), pitch(4, "D"),
    pitch(4, "D#"), pitch(4, "C"), pitch(4, "A#"), pitch(4, "G"),
    pitch(4, "F"), pitch(4, "G"), pitch(4, "A#"), pitch(4, "C"),
    pitch(4, "D"), pitch(4, "C"), pitch(4, "A#"), pitch(4, "G"),
]

ARPEGGIO = [pitch(4, "C"), pitch(4, "D#"), pitch(4, "G"), pitch(4, "C"),
            pitch(4, "D#"), pitch(4, "G"), pitch(4, "C"), pitch(4, "G")]


def add_speed_markers(msgs, id_start, pattern, rows=64, speed=6):
    rid = id_start
    msgs.append(cell(rid, pattern, 0, 0, effect=0x0F, effect_param=speed))
    rid += 1
    return rid


def fill_drums(msgs, id_start, pattern, intensity="full", rows=64):
    """Ch0 kick/snare, ch1 hihat on instr 3."""
    rid = id_start
    for row in range(rows):
        if row % 16 == 0:
            rid = add_speed_markers(msgs, rid, pattern) if row == 0 else rid
        if intensity == "sparse":
            if row % 16 == 0:
                msgs.append(cell(rid, pattern, row, 0, note=pitch(2, "C"), instrument=1, volume=0x40))
                rid += 1
            continue
        if intensity == "break":
            if row % 32 == 0:
                msgs.append(cell(rid, pattern, row, 0, note=pitch(2, "C"), instrument=1, volume=0x30))
                rid += 1
            continue
        # kick on 0,4,8,12 each 16-row block
        if row % 16 in (0, 4, 8, 12):
            msgs.append(cell(rid, pattern, row, 0, note=pitch(2, "C"), instrument=1, volume=0x50))
            rid += 1
        if row % 16 in (4, 12):
            msgs.append(cell(rid, pattern, row, 0, note=pitch(2, "D"), instrument=2, volume=0x45))
            rid += 1
        if row % 8 == 4:
            msgs.append(cell(rid, pattern, row, 1, note=pitch(3, "F#"), instrument=3, volume=0x28))
            rid += 1
    return rid


def fill_bass(msgs, id_start, pattern, rows=64, active=True):
    rid = id_start
    if not active:
        return rid
    for row in range(0, rows, 4):
        n = BASS_SEQ[(row // 4) % len(BASS_SEQ)]
        msgs.append(cell(rid, pattern, row, 2, note=n, instrument=4, volume=0x40))
        rid += 1
    return rid


def fill_chords(msgs, id_start, pattern, rows=64, style="stab"):
    rid = id_start
    for block in range(rows // 16):
        chord = CHORD_STABS[block % len(CHORD_STABS)]
        base_row = block * 16
        if style == "stab":
            for off, n in enumerate(chord):
                msgs.append(cell(rid, pattern, base_row + off * 2, 3, note=n, instrument=5,
                                 volume=0x35, effect=0x0C, effect_param=0x30))
                rid += 1
        elif style == "arp":
            for i, n in enumerate(ARPEGGIO):
                r = base_row + i * 2
                if r < rows:
                    msgs.append(cell(rid, pattern, r, 3, note=n, instrument=5, volume=0x30))
                    rid += 1
    return rid


def fill_lead(msgs, id_start, pattern, rows=64):
    rid = id_start
    for i, n in enumerate(LEAD_HOOK):
        row = i * 4
        if row >= rows:
            break
        msgs.append(cell(rid, pattern, row, 3, note=n, instrument=6, volume=0x42))
        rid += 1
    return rid


def main():
    if not FT2.exists():
        print(f"Build ft2-clone first: {FT2}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    samples = {
        1: ("kick", gen_kick()),
        2: ("snare", gen_snare()),
        3: ("hihat", gen_hihat()),
        4: ("bass", gen_bass()),
        5: ("pad", gen_pad()),
        6: ("lead", gen_lead()),
    }

    msgs = [
        rpc(1, "initialize", {}),
        tool(2, "module_new", {"channels": 4, "name": "Neon Overdrive"}),
        tool(3, "song_set", {"bpm": 132, "speed": 6, "length": 48, "loop_start": 8, "name": "Neon Overdrive"}),
    ]

    rid = 4
    for instr, (name, pcm) in samples.items():
        msgs.append(tool(rid, "instrument_set", {"instrument": instr, "name": name}))
        rid += 1
        msgs.append(tool(rid, "sample_create_from_pcm", {
            "instrument": instr, "sample": 0, "pcm": b64_pcm_int16(pcm),
            "encoding": "int16", "name": name,
        }))
        rid += 1
        if instr == 4:
            msgs.append(tool(rid, "sample_set", {
                "instrument": 4, "sample": 0, "relative_note": -12, "volume": 64,
                "loop_start": 0, "loop_length": len(pcm), "flags": 1,
            }))
            rid += 1
        if instr == 5:
            msgs.append(tool(rid, "sample_set", {
                "instrument": 5, "sample": 0, "volume": 50, "panning": 96,
            }))
            rid += 1

    # 8 patterns x 64 rows (Lotus/Turrican scale)
    patterns = {
        0: ("intro", "sparse", False, "stab"),
        1: ("groove_a", "full", True, "stab"),
        2: ("groove_a2", "full", True, "arp"),
        3: ("chorus", "full", True, "lead"),
        4: ("breakdown", "break", True, "stab"),
        5: ("groove_b", "full", True, "arp"),
        6: ("fill", "full", True, "stab"),
        7: ("outro", "sparse", False, "stab"),
    }

    for p, (_, drum, bass, harm) in patterns.items():
        msgs.append(tool(rid, "pattern_set_length", {"pattern": p, "rows": 64}))
        rid += 1
        rid = fill_drums(msgs, rid, p, intensity=drum)
        rid = fill_bass(msgs, rid, p, active=bass)
        if harm == "lead":
            rid = fill_lead(msgs, rid, p)
        else:
            rid = fill_chords(msgs, rid, p, style=harm)

    # Order song structure (~48 positions, Turrican/Beast ambition)
    order = (
        [0, 0] +           # intro
        [1] * 6 +          # groove A
        [2] * 4 +          # variation
        [3] * 8 +          # chorus
        [4] * 4 +          # Agony-style breakdown
        [5] * 6 +          # groove B
        [6] * 2 +          # fill
        [3] * 8 +          # chorus
        [7, 7]             # outro
    )
    for pos, pat in enumerate(order):
        msgs.append(tool(rid, "order_set", {"position": pos, "pattern": pat}))
        rid += 1

    msgs.append(tool(rid, "module_save", {"path": str(OUT_XM), "format": "xm"}))
    rid += 1
    msgs.append(tool(rid, "module_info", {}))

    payload = "\n".join(msgs) + "\n"
    proc = subprocess.run(
        [str(FT2), "--mcp"],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )

    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode)

    errors = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "result" in r and "content" in r.get("result", {}):
            if r["result"].get("isError"):
                errors.append(r["result"]["content"][0]["text"])

    if errors:
        print("MCP errors:", *errors, sep="\n", file=sys.stderr)
        sys.exit(1)

    print(f"Wrote {OUT_XM} ({OUT_XM.stat().st_size} bytes)")
    print(proc.stdout.splitlines()[-1])


if __name__ == "__main__":
    main()