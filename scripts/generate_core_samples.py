#!/usr/bin/env python3
"""
Generate FastTracker II sample disks (Amiga DD–sized volumes).

Classic Amiga double-density floppy = 880 KiB. Each volume targets that
budget so a full disk of tracker samples fits the era's mental model.

  volume1/  FT2-Samples-Volume1  — core categories + variants (~880 KiB)
  volume2/  FT2-Samples-Volume2  — extras, FX, breaks, utilities (~880 KiB)

All files: mono 16-bit PCM WAV @ 8363 Hz (FT2 middle-C / C-4 rate).

Usage:
  python3 scripts/generate_core_samples.py
  python3 scripts/generate_core_samples.py --volume 1
  python3 scripts/generate_core_samples.py --volume 2
  python3 scripts/generate_core_samples.py --out samples --rate 8363
"""
from __future__ import annotations

import argparse
import math
import random
import shutil
import struct
import wave
from pathlib import Path

# Classic FT2 / Amiga middle-C sample rate
C4_RATE = 8363
# Amiga DD floppy capacity (KiB)
AMIGA_DD_KIB = 880
AMIGA_DD_BYTES = AMIGA_DD_KIB * 1024


# ---------------------------------------------------------------------------
# WAV helpers
# ---------------------------------------------------------------------------

def clamp16(x: float) -> int:
    return int(max(-32767, min(32767, round(x))))


def write_wav(path: Path, samples: list[int], rate: int = C4_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def soft_clip(x: float, drive: float = 1.0) -> float:
    return math.tanh(x * drive)


def exp_env(t: float, decay: float) -> float:
    return math.exp(-t * decay)


def highpass_noise(rng: random.Random, prev: float, amount: float = 0.85) -> tuple[float, float]:
    n = rng.uniform(-1.0, 1.0)
    hp = n - prev * amount
    return hp, n


def seamless_loop_frames(rate: int, base_hz: float, seconds: float) -> tuple[int, float]:
    target = max(1, int(rate * seconds))
    period = max(1, int(round(rate / base_hz)))
    cycles = max(1, int(round(target / period)))
    n = cycles * period
    exact_hz = rate / period
    return n, exact_hz


def N(rate: int, seconds: float) -> int:
    return max(1, int(rate * seconds))


def crossfade_loop(raw: list[float], xfade: int | None = None) -> list[int]:
    n = len(raw)
    xfade = min(xfade or min(64, n // 8), n // 4)
    out = []
    for i in range(n):
        if i < xfade:
            a = i / xfade
            s = raw[i] * a + raw[n - xfade + i] * (1 - a)
        else:
            s = raw[i]
        out.append(clamp16(s * 14000 if abs(s) <= 1.5 else s))
    return out


# ---------------------------------------------------------------------------
# Drums
# ---------------------------------------------------------------------------

def gen_kick(n: int, rate: int, base: float = 55.0, drop: float = 120.0,
             decay: float = 9.0, click_hz: float = 1800.0, drive: float = 1.4,
             amp: float = 30000, seed: int = 0) -> list[int]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        t = i / rate
        pitch = base + drop * math.exp(-t * 28.0)
        body = math.sin(2 * math.pi * pitch * t)
        click = math.sin(2 * math.pi * click_hz * t) * math.exp(-t * 80) * 0.25
        noise = rng.uniform(-1, 1) * math.exp(-t * 100) * 0.08
        env = exp_env(t, decay)
        s = soft_clip((body + click + noise) * env, drive)
        out.append(clamp16(s * amp))
    return out


def gen_snare(n: int, rate: int, tone_hz: float = 185.0, decay: float = 14.0,
              noise_amt: float = 0.85, amp: float = 24000, seed: int = 42) -> list[int]:
    rng = random.Random(seed)
    out, prev = [], 0.0
    for i in range(n):
        t = i / rate
        env = math.exp(-t * decay) * (1.0 - math.exp(-t * 250.0))
        tone = math.sin(2 * math.pi * tone_hz * t) * env * 0.4
        tone += math.sin(2 * math.pi * tone_hz * 1.78 * t) * env * 0.15
        hp, prev = highpass_noise(rng, prev, 0.7)
        s = soft_clip((tone + hp * env * noise_amt) * 1.1, 1.2)
        out.append(clamp16(s * amp))
    return out


def gen_snare_clap(n: int, rate: int, seed: int = 77) -> list[int]:
    rng = random.Random(seed)
    out, prev = [], 0.0
    bursts = [0.0, 0.012, 0.024, 0.040]
    for i in range(n):
        t = i / rate
        env = 0.0
        for b in bursts:
            if t >= b:
                env += math.exp(-(t - b) * 35.0)
        env = min(1.0, env * 0.55)
        hp, prev = highpass_noise(rng, prev, 0.6)
        tone = math.sin(2 * math.pi * 210 * t) * env * 0.2
        s = soft_clip((hp * env + tone) * 1.0, 1.1)
        out.append(clamp16(s * 22000))
    return out


def gen_hat(n: int, rate: int, decay: float = 55.0, metallic: float = 0.08,
            amp: float = 14000, seed: int = 99) -> list[int]:
    rng = random.Random(seed)
    out, prev = [], 0.0
    partials = [5400, 7800, 9200, 10500]
    for i in range(n):
        t = i / rate
        env = math.exp(-t * decay)
        hp, prev = highpass_noise(rng, prev, 0.92)
        metal = sum(math.sin(2 * math.pi * f * t) * (1.0 / (k + 1))
                    for k, f in enumerate(partials)) * env * metallic
        s = soft_clip(hp * env * 0.9 + metal, 1.0)
        out.append(clamp16(s * amp))
    return out


def gen_crash(n: int, rate: int, decay: float = 2.8, seed: int = 200) -> list[int]:
    rng = random.Random(seed)
    out, prev = [], 0.0
    partials = [3200, 4100, 5300, 6700, 8100, 9900, 11200]
    for i in range(n):
        t = i / rate
        env = math.exp(-t * decay) * (1.0 - math.exp(-t * 40.0))
        hp, prev = highpass_noise(rng, prev, 0.88)
        metal = sum(math.sin(2 * math.pi * f * t + k) / (k + 1.5)
                    for k, f in enumerate(partials)) * env * 0.12
        s = soft_clip(hp * env * 0.7 + metal, 1.0)
        out.append(clamp16(s * 16000))
    return out


def gen_ride(n: int, rate: int, seed: int = 210) -> list[int]:
    """Ride cymbal — brighter, pingier than crash."""
    rng = random.Random(seed)
    out, prev = [], 0.0
    partials = [4800, 6200, 7500, 9100, 11000, 12500]
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 3.5) * (1.0 - math.exp(-t * 60.0))
        hp, prev = highpass_noise(rng, prev, 0.93)
        ping = math.sin(2 * math.pi * 4800 * t) * math.exp(-t * 8) * 0.3
        metal = sum(math.sin(2 * math.pi * f * t) / (k + 1.2)
                    for k, f in enumerate(partials)) * env * 0.1
        s = soft_clip(hp * env * 0.55 + metal + ping, 1.0)
        out.append(clamp16(s * 15000))
    return out


def gen_tom(n: int, rate: int, base_hz: float = 120.0) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        pitch = base_hz * (1.0 + 0.8 * math.exp(-t * 12.0))
        body = math.sin(2 * math.pi * pitch * t)
        body += 0.3 * math.sin(2 * math.pi * pitch * 1.5 * t)
        env = math.exp(-t * 7.0)
        s = soft_clip(body * env, 1.3)
        out.append(clamp16(s * 26000))
    return out


def gen_rim(n: int, rate: int, seed: int = 33) -> list[int]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 90.0)
        click = math.sin(2 * math.pi * 2400 * t) * env
        noise = rng.uniform(-1, 1) * env * 0.4
        s = soft_clip(click * 0.7 + noise, 1.2)
        out.append(clamp16(s * 18000))
    return out


def gen_cowbell(n: int, rate: int) -> list[int]:
    """Classic two-partial cowbell."""
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 12.0)
        s = (math.sin(2 * math.pi * 540 * t) + 0.7 * math.sin(2 * math.pi * 800 * t)) * env
        s = soft_clip(s, 1.5)
        out.append(clamp16(s * 18000))
    return out


def gen_clave(n: int, rate: int) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 45.0)
        s = math.sin(2 * math.pi * 2100 * t) * env
        s += 0.4 * math.sin(2 * math.pi * 3200 * t) * env
        out.append(clamp16(s * 16000))
    return out


def gen_shaker(n: int, rate: int, seed: int = 50) -> list[int]:
    rng = random.Random(seed)
    out, prev = [], 0.0
    for i in range(n):
        t = i / rate
        # Grain envelope bursts
        grain = abs(math.sin(2 * math.pi * 40 * t)) ** 3
        env = math.exp(-t * 8.0) * (0.3 + 0.7 * grain)
        hp, prev = highpass_noise(rng, prev, 0.95)
        out.append(clamp16(hp * env * 12000))
    return out


def gen_conga(n: int, rate: int, base_hz: float = 200.0) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        pitch = base_hz * (1.0 + 0.3 * math.exp(-t * 20))
        env = math.exp(-t * 10.0)
        s = math.sin(2 * math.pi * pitch * t) * env
        s += 0.25 * math.sin(2 * math.pi * pitch * 2.2 * t) * env
        slap = math.sin(2 * math.pi * 1800 * t) * math.exp(-t * 50) * 0.3
        out.append(clamp16(soft_clip(s + slap, 1.2) * 22000))
    return out


# ---------------------------------------------------------------------------
# Synth
# ---------------------------------------------------------------------------

def gen_single_cycle(rate: int, waveshape: str, cycles: int = 1) -> list[int]:
    freq = 261.625565
    period = max(1, int(round(rate / freq)))
    n = period * cycles
    out = []
    for i in range(n):
        phase = (i % period) / period
        p2 = phase * 2 * math.pi
        if waveshape == "sine":
            s = math.sin(p2)
        elif waveshape == "saw":
            s = 2.0 * phase - 1.0
        elif waveshape == "square":
            s = 1.0 if phase < 0.5 else -1.0
        elif waveshape == "pulse25":
            s = 1.0 if phase < 0.25 else -1.0
        elif waveshape == "pulse12":
            s = 1.0 if phase < 0.125 else -1.0
        elif waveshape == "triangle":
            s = -(4.0 * abs(phase - 0.5) - 1.0)
        elif waveshape == "supersaw":
            s = sum((2.0 * ((phase + d) % 1.0) - 1.0) for d in (-0.02, -0.008, 0, 0.008, 0.02)) / 5
        elif waveshape == "noise":
            # Deterministic "noise" cycle (repeats) — useful for hats via pitch
            s = math.sin(p2 * 7.3) * math.sin(p2 * 13.1) * math.cos(p2 * 3.7)
        elif waveshape == "halfsine":
            s = abs(math.sin(p2)) * 2 - 1
        else:
            s = math.sin(p2)
        out.append(clamp16(s * 20000))
    return out


def gen_sid_lead(rate: int, seconds: float = 0.5) -> list[int]:
    n, freq = seamless_loop_frames(rate, 261.63, seconds)
    out = []
    for i in range(n):
        phase = (i * freq / rate) % 1.0
        width = 0.35 + 0.08 * math.sin(2 * math.pi * (2 * i / n))
        pulse = 1.0 if phase < width else -1.0
        tri = -(4.0 * abs(phase - 0.5) - 1.0)
        s = pulse * 0.55 + tri * 0.35 + 0.1 * math.sin(2 * math.pi * phase * 2)
        s *= 0.92 + 0.08 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 18000))
    return out


def gen_fm_bass(rate: int, seconds: float = 0.5, ratio: float = 2.0, idx0: float = 2.5) -> list[int]:
    n, fc = seamless_loop_frames(rate, 65.41, seconds)
    out = []
    for i in range(n):
        t = i / rate
        idx = idx0 + 1.5 * math.sin(2 * math.pi * i / n)
        mod = math.sin(2 * math.pi * fc * ratio * t) * idx
        car = math.sin(2 * math.pi * fc * t + mod)
        sub = math.sin(2 * math.pi * fc * 0.5 * t) * 0.25
        out.append(clamp16((car * 0.85 + sub) * 20000))
    return out


def gen_fm_bell(n: int, rate: int, fc: float = 440.0, ratio: float = 3.5) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 2.2)
        idx = 4.0 * math.exp(-t * 3.5)
        mod = math.sin(2 * math.pi * fc * ratio * t) * idx
        s = math.sin(2 * math.pi * fc * t + mod) * env
        s += 0.3 * math.sin(2 * math.pi * fc * 2.01 * t) * env
        out.append(clamp16(s * 18000))
    return out


def gen_analog_bass(rate: int, seconds: float = 0.5, freq_hz: float = 82.41) -> list[int]:
    n, freq = seamless_loop_frames(rate, freq_hz, seconds)
    out = []
    for i in range(n):
        phase = (i * freq / rate) % 1.0
        saw = 2.0 * phase - 1.0
        sq = 1.0 if phase < 0.5 else -1.0
        s = soft_clip(saw * 0.6 + sq * 0.25 + 0.15 * math.sin(2 * math.pi * phase), 1.3)
        out.append(clamp16(s * 19000))
    return out


def gen_chip_lead(rate: int, seconds: float = 0.4) -> list[int]:
    n, freq = seamless_loop_frames(rate, 523.25, seconds)
    out = []
    for i in range(n):
        phase = (i * freq / rate) % 1.0
        width = 0.5 + 0.25 * math.sin(2 * math.pi * (2 * i / n))
        s = 1.0 if phase < width else -1.0
        s = round(s * 8) / 8.0
        out.append(clamp16(s * 16000))
    return out


def gen_acid_bass(rate: int, seconds: float = 0.6) -> list[int]:
    """TB-303-ish resonant saw with filter sweep (loop-safe LFO)."""
    n, freq = seamless_loop_frames(rate, 55.0, seconds)
    out = []
    # Simple resonant filter state
    lp, bp = 0.0, 0.0
    for i in range(n):
        phase = (i * freq / rate) % 1.0
        saw = 2.0 * phase - 1.0
        # Cutoff LFO: 1 cycle over loop
        cutoff = 0.08 + 0.35 * (0.5 + 0.5 * math.sin(2 * math.pi * i / n))
        res = 0.85
        hp = saw - lp
        bp = bp + cutoff * hp
        lp = lp + cutoff * bp
        bp = bp * res
        s = soft_clip(hp * 0.3 + bp * 0.9, 1.8)
        out.append(clamp16(s * 18000))
    return out


def gen_organ(rate: int, seconds: float = 0.8) -> list[int]:
    """Hammond-ish drawbar organ (looped)."""
    n, f0 = seamless_loop_frames(rate, 130.81, seconds)  # C3
    # Drawbars: 16' 5⅓' 8' 4' 2⅔' 2' 1⅗' 1⅓' 1'
    drawbars = [(1, 0.8), (3, 0.4), (2, 0.9), (4, 0.6), (6, 0.35),
                (8, 0.3), (10, 0.2), (12, 0.15), (16, 0.1)]
    out = []
    for i in range(n):
        t = i / rate
        s = sum(a * math.sin(2 * math.pi * f0 * h * t) for h, a in drawbars)
        s /= 3.0
        # Leslie-ish AM (1 cycle)
        s *= 0.85 + 0.15 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 16000))
    return out


def gen_brass_synth(rate: int, seconds: float = 0.7) -> list[int]:
    """Synth brass — saw with formant-ish peaks."""
    n, f0 = seamless_loop_frames(rate, 220.0, seconds)
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for h in range(1, 10):
            s += math.sin(2 * math.pi * f0 * h * t) / h
        # Brass formants
        s += 0.3 * math.sin(2 * math.pi * 500 * t) * abs(s)
        s *= 0.9 + 0.1 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(soft_clip(s / 2.5, 1.1) * 17000))
    return out


def gen_pwm_pad_lead(rate: int, seconds: float = 0.5) -> list[int]:
    """Slow PWM square — classic 80s lead body."""
    n, freq = seamless_loop_frames(rate, 261.63, seconds)
    out = []
    for i in range(n):
        phase = (i * freq / rate) % 1.0
        width = 0.5 + 0.35 * math.sin(2 * math.pi * i / n)
        s = 1.0 if phase < width else -1.0
        # Soften a bit
        s = soft_clip(s * 0.9, 1.0)
        out.append(clamp16(s * 17000))
    return out


# ---------------------------------------------------------------------------
# Pads
# ---------------------------------------------------------------------------

def gen_pad_warm(rate: int, seconds: float = 2.0) -> list[int]:
    n, f0 = seamless_loop_frames(rate, 32.703, seconds)
    harmonics = [4, 5, 6, 8, 10, 12, 16]
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for k, h in enumerate(harmonics):
            f = f0 * h
            partial = sum(math.sin(2 * math.pi * f * m * t) / m for m in range(1, 5))
            partial += 0.35 * math.sin(2 * math.pi * f * t + 2 * math.pi * (k + 1) * i / n)
            s += partial / (1 + k * 0.12)
        s /= len(harmonics)
        s *= 0.75 + 0.25 * math.sin(2 * math.pi * i / n)
        s *= 0.9 + 0.1 * math.sin(4 * math.pi * i / n + 1.2)
        out.append(clamp16(s * 12000))
    return out


def gen_pad_choir(rate: int, seconds: float = 2.5) -> list[int]:
    n, base = seamless_loop_frames(rate, 110.0, seconds)
    formant_mults = [5, 8, 20, 25]
    amps = [1.0, 0.7, 0.35, 0.2]
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for det in (-1, 0, 1):
            phase0 = 2 * math.pi * base * t + det * 2 * math.pi * i / n
            fund = math.sin(phase0)
            for mult, amp in zip(formant_mults, amps):
                ff = base * mult
                s += amp * math.sin(2 * math.pi * ff * t + det) * (0.5 + 0.5 * fund) * 0.15
                s += amp * 0.35 * math.sin(2 * math.pi * (ff + base) * t) * 0.1
            s += fund * 0.25
        s /= 3.0
        s *= 0.7 + 0.3 * math.sin(2 * math.pi * i / n)
        s *= 0.85 + 0.15 * math.sin(4 * math.pi * i / n + 0.7)
        out.append(clamp16(soft_clip(s, 0.9) * 14000))
    return out


def gen_pad_dark(rate: int, seconds: float = 2.5) -> list[int]:
    n, f0 = seamless_loop_frames(rate, 32.703, seconds)
    harmonics = [2, 3, 4, 6, 8]
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for k, h in enumerate(harmonics):
            f = f0 * h
            s += math.sin(2 * math.pi * f * t) / (k + 1)
            s += 0.2 * math.sin(2 * math.pi * f * 2 * t) / (k + 1)
        s /= 2.0
        bright = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(2 * math.pi * i / n))
        shimmer_f = f0 * 16
        s = s * (0.6 + 0.4 * bright) + bright * 0.12 * math.sin(2 * math.pi * shimmer_f * t) * abs(s)
        s *= 0.8 + 0.2 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 11000))
    return out


def gen_pad_shimmer(rate: int, seconds: float = 2.0) -> list[int]:
    n, f0 = seamless_loop_frames(rate, 65.406, seconds)
    harmonics = [8, 10, 12, 16, 20]
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for k, h in enumerate(harmonics):
            f = f0 * h
            phase = 2 * math.pi * f * t + 0.15 * math.sin(2 * math.pi * (k + 1) * i / n)
            s += math.sin(phase) / (k + 1.2)
        s /= 2.5
        s *= 0.65 + 0.35 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 10000))
    return out


def gen_pad_strings(rate: int, seconds: float = 2.2) -> list[int]:
    """String section pad — many detuned saws, harmonic grid."""
    n, f0 = seamless_loop_frames(rate, 65.406, seconds)
    # C3–C5 string stack via harmonics
    harmonics = [2, 3, 4, 5, 6, 8]
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for k, h in enumerate(harmonics):
            f = f0 * h
            saw = sum(math.sin(2 * math.pi * f * m * t) / m for m in range(1, 7))
            # Ensemble phase offsets
            saw += 0.4 * sum(math.sin(2 * math.pi * f * t + 2 * math.pi * (d + 1) * i / n)
                             for d in range(3)) / 3
            s += saw / (1 + k * 0.2)
        s /= 8.0
        s *= 0.8 + 0.2 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 13000))
    return out


def gen_pad_glass(rate: int, seconds: float = 2.0) -> list[int]:
    """Glass / crystal pad — high inharmonic-ish but loop-safe harmonics."""
    n, f0 = seamless_loop_frames(rate, 110.0, seconds)
    mults = [1, 2, 3, 5, 7, 11, 13]
    out = []
    for i in range(n):
        t = i / rate
        s = sum(math.sin(2 * math.pi * f0 * m * t) / (m ** 0.7) for m in mults) / 4
        s *= 0.7 + 0.3 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 11000))
    return out


def gen_pad_drone(rate: int, seconds: float = 3.0) -> list[int]:
    """Low drone / didgeridoo-ish for atmosphere."""
    n, f0 = seamless_loop_frames(rate, 55.0, seconds)
    out = []
    for i in range(n):
        t = i / rate
        s = math.sin(2 * math.pi * f0 * t)
        s += 0.5 * math.sin(2 * math.pi * f0 * 2 * t + 0.3 * math.sin(2 * math.pi * i / n))
        s += 0.25 * math.sin(2 * math.pi * f0 * 3 * t)
        s += 0.15 * math.sin(2 * math.pi * f0 * 4 * t)
        # Growl
        s += 0.1 * math.sin(2 * math.pi * f0 * t) * math.sin(2 * math.pi * 6 * i / n)
        s *= 0.85 + 0.15 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(soft_clip(s, 1.0) * 16000))
    return out


# ---------------------------------------------------------------------------
# Acoustic
# ---------------------------------------------------------------------------

def gen_piano_strike(n: int, rate: int, freq: float = 261.63) -> list[int]:
    ratios = [1.0, 2.003, 3.01, 4.02, 5.04, 6.07, 7.1, 8.15]
    amps = [1.0, 0.55, 0.35, 0.22, 0.14, 0.09, 0.06, 0.04]
    out = []
    for i in range(n):
        t = i / rate
        env = (1.0 - math.exp(-t * 200.0)) * math.exp(-t * 3.5)
        hammer = math.sin(2 * math.pi * 2200 * t) * math.exp(-t * 60) * 0.15
        s = hammer
        for r, a in zip(ratios, amps):
            s += a * math.sin(2 * math.pi * freq * r * t) * math.exp(-t * (3.0 + r * 0.8))
        out.append(clamp16(s * env * 18000))
    return out


def gen_pizzicato(n: int, rate: int, freq: float = 196.0, seed: int = 55) -> list[int]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 12.0)
        pluck = rng.uniform(-1, 1) * math.exp(-t * 80) * 0.4
        body = sum(math.sin(2 * math.pi * freq * h * t) / h * math.exp(-t * (6 + h * 2))
                   for h in range(1, 8))
        out.append(clamp16((pluck + body * 0.85) * env * 20000))
    return out


def gen_guitar_pluck(n: int, rate: int, freq: float = 110.0) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        env = (1.0 - math.exp(-t * 150.0)) * math.exp(-t * 4.5)
        s = sum((1.0 / h) * math.sin(2 * math.pi * freq * h * t) * math.exp(-t * (3 + h * 1.2))
                for h in range(1, 10))
        s += 0.2 * math.sin(2 * math.pi * 3500 * t) * math.exp(-t * 100)
        out.append(clamp16(soft_clip(s * env, 1.1) * 19000))
    return out


def gen_orch_hit(n: int, rate: int, freqs: list[float], seed: int = 12) -> list[int]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        t = i / rate
        env = (1.0 - math.exp(-t * 80.0)) * math.exp(-t * 5.5)
        s = sum(math.sin(2 * math.pi * f * t) / (1 + k * 0.3)
                + 0.3 * math.sin(2 * math.pi * f * 2 * t) / (1 + k)
                for k, f in enumerate(freqs))
        s += rng.uniform(-1, 1) * math.exp(-t * 20) * 0.25
        out.append(clamp16(soft_clip(s * env / 2.0, 1.2) * 22000))
    return out


def gen_bass_acoustic(n: int, rate: int, freq: float = 55.0) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        env = (1.0 - math.exp(-t * 100.0)) * math.exp(-t * 3.0)
        s = math.sin(2 * math.pi * freq * t)
        s += 0.45 * math.sin(2 * math.pi * freq * 2 * t) * math.exp(-t * 5)
        s += 0.2 * math.sin(2 * math.pi * freq * 3 * t) * math.exp(-t * 8)
        s += 0.1 * math.sin(2 * math.pi * freq * 4 * t) * math.exp(-t * 12)
        s += 0.08 * math.sin(2 * math.pi * 1800 * t) * math.exp(-t * 40)
        out.append(clamp16(s * env * 24000))
    return out


def gen_flute_soft(rate: int, seconds: float = 1.0) -> list[int]:
    n, freq = seamless_loop_frames(rate, 523.25, seconds)
    rng = random.Random(7)
    raw = []
    for i in range(n):
        t = i / rate
        s = math.sin(2 * math.pi * freq * t)
        s += 0.15 * math.sin(2 * math.pi * freq * 2 * t)
        s += 0.05 * math.sin(2 * math.pi * freq * 3 * t)
        s = (s + rng.uniform(-1, 1) * 0.05) * (0.9 + 0.1 * math.sin(2 * math.pi * i / n))
        raw.append(s)
    return crossfade_loop(raw)


def gen_trumpet(n: int, rate: int, freq: float = 349.23) -> list[int]:
    """Brassy trumpet strike — bright odd harmonics."""
    out = []
    for i in range(n):
        t = i / rate
        env = (1.0 - math.exp(-t * 80.0)) * math.exp(-t * 2.8)
        s = 0.0
        for h in range(1, 12):
            # Odd harmonics dominate
            a = (1.0 / h) if h % 2 else (0.3 / h)
            s += a * math.sin(2 * math.pi * freq * h * t) * math.exp(-t * (2 + h * 0.5))
        s += 0.15 * math.sin(2 * math.pi * 1500 * t) * math.exp(-t * 30)
        out.append(clamp16(soft_clip(s * env, 1.2) * 18000))
    return out


def gen_violin_bow(rate: int, seconds: float = 1.2) -> list[int]:
    """Bowed string loop — saw-like with slow bow pressure AM."""
    n, freq = seamless_loop_frames(rate, 440.0, seconds)
    out = []
    for i in range(n):
        t = i / rate
        s = sum(math.sin(2 * math.pi * freq * h * t) / h for h in range(1, 12)) / 3
        # Rosin noise
        s += 0.04 * math.sin(2 * math.pi * 3000 * t) * math.sin(2 * math.pi * i / n * 3)
        s *= 0.85 + 0.15 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(s * 14000))
    return out


def gen_marimba(n: int, rate: int, freq: float = 523.25) -> list[int]:
    """Mallet / marimba hit — inharmonic bars."""
    # Bar modes approximate
    modes = [1.0, 3.99, 10.5]
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 5.0)
        s = sum(math.sin(2 * math.pi * freq * m * t) * math.exp(-t * (4 + k * 3)) / (k + 1)
                for k, m in enumerate(modes))
        strike = math.sin(2 * math.pi * 2000 * t) * math.exp(-t * 80) * 0.2
        out.append(clamp16((s + strike) * env * 18000))
    return out


def gen_harp(n: int, rate: int, freq: float = 392.0) -> list[int]:
    """Harp pluck — bright, long-ish decay."""
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 3.5)
        s = sum(math.sin(2 * math.pi * freq * h * t) / (h ** 1.2) * math.exp(-t * (2 + h))
                for h in range(1, 14))
        out.append(clamp16(s * env * 16000))
    return out


# ---------------------------------------------------------------------------
# Volume 2: FX, breaks, utility, world
# ---------------------------------------------------------------------------

def gen_whoosh(n: int, rate: int, seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    out, prev = [], 0.0
    for i in range(n):
        t = i / rate
        # Rising filter noise
        pos = i / n
        env = math.sin(math.pi * pos) ** 1.5
        hp, prev = highpass_noise(rng, prev, 0.5 + 0.45 * pos)
        tone = math.sin(2 * math.pi * (200 + 2000 * pos) * t) * env * 0.2
        out.append(clamp16((hp * env * 0.8 + tone) * 14000))
    return out


def gen_reverse_cymbal(n: int, rate: int, seed: int = 2) -> list[int]:
    # Generate crash and reverse
    crash = gen_crash(n, rate, decay=2.5, seed=seed)
    return list(reversed(crash))


def gen_laser(n: int, rate: int) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        pos = i / max(1, n - 1)
        freq = 2000 * (1.0 - 0.85 * pos) + 80
        env = math.exp(-t * 6.0)
        s = math.sin(2 * math.pi * freq * t) * env
        s += 0.3 * math.sin(2 * math.pi * freq * 2 * t) * env
        out.append(clamp16(s * 20000))
    return out


def gen_explosion(n: int, rate: int, seed: int = 3) -> list[int]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 4.0)
        noise = rng.uniform(-1, 1)
        boom = math.sin(2 * math.pi * (40 + 80 * math.exp(-t * 8)) * t)
        s = soft_clip((noise * 0.7 + boom * 0.5) * env, 1.5)
        out.append(clamp16(s * 24000))
    return out


def gen_powerup(n: int, rate: int) -> list[int]:
    """Chiptune power-up blip."""
    out = []
    notes = [261.63, 329.63, 392.00, 523.25]
    seg = n // len(notes)
    for i in range(n):
        t = i / rate
        ni = min(len(notes) - 1, i // max(1, seg))
        f = notes[ni]
        env = 0.7 + 0.3 * ((i % seg) / max(1, seg))
        s = (1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0) * env
        out.append(clamp16(s * math.exp(-t * 1.5) * 16000))
    return out


def gen_impact_metal(n: int, rate: int, seed: int = 4) -> list[int]:
    rng = random.Random(seed)
    out = []
    partials = [220, 340, 510, 780, 1200]
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 6.0)
        s = sum(math.sin(2 * math.pi * f * t) * math.exp(-t * (3 + k)) / (k + 1)
                for k, f in enumerate(partials))
        s += rng.uniform(-1, 1) * math.exp(-t * 25) * 0.4
        out.append(clamp16(soft_clip(s * env, 1.3) * 20000))
    return out


def gen_noise_burst(n: int, rate: int, decay: float = 15.0, seed: int = 5) -> list[int]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        t = i / rate
        out.append(clamp16(rng.uniform(-1, 1) * math.exp(-t * decay) * 18000))
    return out


def gen_break_loop(rate: int, bpm: float, bars: float = 1.0, seed: int = 10) -> list[int]:
    """
    One-bar drum break (kick/snare/hat pattern) at given BPM.
    Loop the entire sample in FT2 for continuous breakbeat.
    """
    # bar length in samples
    beats = 4 * bars
    n = int(rate * (60.0 / bpm) * beats)
    mix = [0.0] * n
    rng = random.Random(seed)

    kick = gen_kick(N(rate, 0.35), rate, base=50, drop=100, decay=12, seed=seed)
    snare = gen_snare(N(rate, 0.28), rate, seed=seed + 1)
    hat_c = gen_hat(N(rate, 0.08), rate, decay=70, seed=seed + 2)
    hat_o = gen_hat(N(rate, 0.25), rate, decay=15, seed=seed + 3)

    def place(src: list[int], at: int, gain: float = 1.0) -> None:
        for j, v in enumerate(src):
            if at + j < n:
                mix[at + j] += v * gain

    step = n // 16  # 16th notes
    for s in range(16):
        pos = s * step
        # closed hat on most 16ths
        if s % 2 == 0:
            place(hat_c, pos, 0.55)
        else:
            place(hat_c, pos, 0.3)
        # kick on 1 and 3 (and sometimes 'and' of 2)
        if s in (0, 8) or (s == 6 and seed % 2):
            place(kick, pos, 0.95)
        # snare on 2 and 4
        if s in (4, 12):
            place(snare, pos, 0.85)
        # open hat on last 16th of bar sometimes
        if s == 14:
            place(hat_o, pos, 0.5)

    # Soft clip mix
    peak = max(abs(x) for x in mix) or 1.0
    scale = 28000 / peak
    return [clamp16(x * scale) for x in mix]


def gen_silence(n: int) -> list[int]:
    return [0] * n


def gen_tick(n: int, rate: int, freq: float = 1000.0) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 80.0)
        out.append(clamp16(math.sin(2 * math.pi * freq * t) * env * 20000))
    return out


def gen_noise_loop(rate: int, seconds: float, kind: str = "white", seed: int = 9) -> list[int]:
    n = N(rate, seconds)
    rng = random.Random(seed)
    out = []
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    for i in range(n):
        w = rng.uniform(-1, 1)
        if kind == "white":
            s = w
        else:
            # Paul Kellet pink noise approximation
            b0 = 0.99886 * b0 + w * 0.0555179
            b1 = 0.99332 * b1 + w * 0.0750759
            b2 = 0.96900 * b2 + w * 0.1538520
            b3 = 0.86650 * b3 + w * 0.3104856
            b4 = 0.55000 * b4 + w * 0.5329522
            b5 = -0.7616 * b5 - w * 0.0168980
            s = b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362
            b6 = w * 0.115926
            s *= 0.11
        out.append(clamp16(s * 12000))
    # Crossfade for seamless noise loop
    raw = [x / 14000 for x in out]
    return crossfade_loop(raw, xfade=min(128, n // 8))


def gen_tone_loop(rate: int, hz: float, seconds: float = 0.5) -> list[int]:
    n, freq = seamless_loop_frames(rate, hz, seconds)
    return [clamp16(math.sin(2 * math.pi * freq * i / rate) * 16000) for i in range(n)]


def gen_vocal_ah(rate: int, seconds: float = 1.0) -> list[int]:
    """Simple vocal 'ah' formant loop."""
    n, f0 = seamless_loop_frames(rate, 220.0, seconds)
    # Formants F1 F2 F3 for 'ah'
    formants = [(700, 1.0), (1200, 0.6), (2600, 0.25)]
    out = []
    for i in range(n):
        t = i / rate
        fund = math.sin(2 * math.pi * f0 * t)
        s = fund * 0.4
        for ff, a in formants:
            s += a * math.sin(2 * math.pi * ff * t) * (0.4 + 0.6 * fund) * 0.2
        s *= 0.85 + 0.15 * math.sin(2 * math.pi * i / n)
        out.append(clamp16(soft_clip(s, 0.9) * 15000))
    return out


def gen_sitar_pluck(n: int, rate: int, freq: float = 146.83) -> list[int]:
    """Buzzing sitar-ish pluck with sympathetic buzz."""
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 4.0)
        s = sum(math.sin(2 * math.pi * freq * h * t) / h * math.exp(-t * (2 + h * 0.8))
                for h in range(1, 16))
        # Buzz / jawari
        s += 0.2 * math.sin(2 * math.pi * freq * 2 * t) * abs(math.sin(2 * math.pi * 40 * t)) * env
        out.append(clamp16(soft_clip(s * env, 1.2) * 17000))
    return out


def gen_kalimba(n: int, rate: int, freq: float = 440.0) -> list[int]:
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 4.5)
        s = math.sin(2 * math.pi * freq * t)
        s += 0.35 * math.sin(2 * math.pi * freq * 2.01 * t) * math.exp(-t * 6)
        s += 0.12 * math.sin(2 * math.pi * freq * 4.1 * t) * math.exp(-t * 10)
        out.append(clamp16(s * env * 19000))
    return out


# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------

Item = tuple[str, str, list[int], str]  # category, filename, pcm, description

CAT_TITLES_V1 = {
    "01-drums-percussion": "Drums & Percussion",
    "02-synth-leads-bass": "Synth Leads & Bass",
    "03-pads-choirs": "Pads & Choirs",
    "04-acoustic": "Acoustic Emulations",
}

CAT_TITLES_V2 = {
    "01-drums-variants": "Drum Variants & Latin",
    "02-synth-advanced": "Advanced Synth",
    "03-fx-impacts": "FX & Impacts",
    "04-breaks-loops": "Breaks & Loops",
    "05-utility": "Utility & Test Tones",
    "06-world-misc": "World & Vocal",
}


def build_volume1(rate: int) -> list[Item]:
    """Core disk — aim ~880 KiB Amiga DD."""
    items: list[Item] = []
    d = "01-drums-percussion"
    items += [
        (d, "kick_808.wav", gen_kick(N(rate, 0.55), rate, 55, 120, 9, 1800, 1.4, 30000, 1),
         "Deep 808-style sine kick. One-shot."),
        (d, "kick_tight.wav", gen_kick(N(rate, 0.28), rate, 70, 90, 18, 2000, 1.6, 29000, 2),
         "Short punchy dance kick. One-shot."),
        (d, "kick_909.wav", gen_kick(N(rate, 0.40), rate, 48, 160, 11, 3500, 1.8, 30000, 3),
         "909-style kick — more click, shorter body. One-shot."),
        (d, "kick_electro.wav", gen_kick(N(rate, 0.32), rate, 80, 70, 22, 2500, 2.0, 28000, 4),
         "Electro / 8-bit tight kick. One-shot."),
        (d, "snare_tight.wav", gen_snare(N(rate, 0.35), rate, 185, 14, 0.85, 24000, 42),
         "Tight electronic snare. One-shot."),
        (d, "snare_fat.wav", gen_snare(N(rate, 0.45), rate, 160, 9, 0.95, 25000, 43),
         "Fatter snare, longer noise tail. One-shot."),
        (d, "snare_piccolo.wav", gen_snare(N(rate, 0.28), rate, 280, 18, 0.7, 22000, 44),
         "High piccolo snare. One-shot."),
        (d, "snare_clap.wav", gen_snare_clap(N(rate, 0.40), rate, 77),
         "Multi-burst electronic clap. One-shot."),
        (d, "hat_closed.wav", gen_hat(N(rate, 0.12), rate, 55, 0.08, 14000, 99),
         "Closed hi-hat. One-shot."),
        (d, "hat_closed_dark.wav", gen_hat(N(rate, 0.14), rate, 45, 0.04, 12000, 100),
         "Darker closed hat. One-shot."),
        (d, "hat_open.wav", gen_hat(N(rate, 0.55), rate, 8.5, 0.10, 13000, 101),
         "Open hi-hat. One-shot."),
        (d, "hat_pedal.wav", gen_hat(N(rate, 0.18), rate, 30, 0.06, 11000, 102),
         "Pedal / half-open hat. One-shot."),
        (d, "crash_elec.wav", gen_crash(N(rate, 1.4), rate, 2.8, 200),
         "Electronic crash. One-shot."),
        (d, "ride_elec.wav", gen_ride(N(rate, 1.2), rate, 210),
         "Electronic ride. One-shot."),
        (d, "tom_low.wav", gen_tom(N(rate, 0.45), rate, 90),
         "Low tom. One-shot."),
        (d, "tom_mid.wav", gen_tom(N(rate, 0.40), rate, 140),
         "Mid tom. One-shot."),
        (d, "tom_high.wav", gen_tom(N(rate, 0.35), rate, 200),
         "High tom. One-shot."),
        (d, "rimshot.wav", gen_rim(N(rate, 0.08), rate, 33),
         "Rimshot. One-shot."),
        (d, "cowbell.wav", gen_cowbell(N(rate, 0.35), rate),
         "Two-partial cowbell. One-shot."),
        (d, "clave.wav", gen_clave(N(rate, 0.12), rate),
         "Clave wood block. One-shot."),
        (d, "shaker.wav", gen_shaker(N(rate, 0.40), rate, 50),
         "Shaker grain. One-shot."),
    ]

    s = "02-synth-leads-bass"
    items += [
        (s, "wave_sine.wav", gen_single_cycle(rate, "sine"),
         "Single-cycle sine @ C4. Loop full."),
        (s, "wave_saw.wav", gen_single_cycle(rate, "saw"),
         "Single-cycle saw @ C4. Loop full."),
        (s, "wave_square.wav", gen_single_cycle(rate, "square"),
         "Single-cycle square @ C4. Loop full."),
        (s, "wave_pulse25.wav", gen_single_cycle(rate, "pulse25"),
         "Single-cycle 25% pulse @ C4. Loop full."),
        (s, "wave_pulse12.wav", gen_single_cycle(rate, "pulse12"),
         "Single-cycle 12.5% pulse (SID-like). Loop full."),
        (s, "wave_triangle.wav", gen_single_cycle(rate, "triangle"),
         "Single-cycle triangle @ C4. Loop full."),
        (s, "wave_supersaw.wav", gen_single_cycle(rate, "supersaw", 4),
         "Detuned supersaw (4 cycles). Loop full."),
        (s, "wave_halfsine.wav", gen_single_cycle(rate, "halfsine"),
         "Half-sine / full-wave rectified. Loop full."),
        (s, "wave_noise.wav", gen_single_cycle(rate, "noise", 8),
         "Deterministic noise cycle (pitchable hats). Loop full."),
        (s, "sid_lead.wav", gen_sid_lead(rate, 0.5),
         "SID pulse+tri lead. Loop full."),
        (s, "fm_bass.wav", gen_fm_bass(rate, 0.5),
         "2-op FM bass. Loop full; rel. note −12/−24."),
        (s, "fm_bass_metal.wav", gen_fm_bass(rate, 0.5, ratio=3.5, idx0=3.5),
         "Metallic FM bass (higher ratio). Loop full."),
        (s, "fm_bell.wav", gen_fm_bell(N(rate, 1.2), rate),
         "Bright FM bell. One-shot."),
        (s, "fm_bell_low.wav", gen_fm_bell(N(rate, 1.4), rate, fc=220.0, ratio=2.7),
         "Lower FM bell / chime. One-shot."),
        (s, "analog_bass.wav", gen_analog_bass(rate, 0.5),
         "Analog saw+square bass. Loop full."),
        (s, "analog_bass_sub.wav", gen_analog_bass(rate, 0.5, 41.20),
         "Sub analog bass (E1). Loop full."),
        (s, "chip_lead.wav", gen_chip_lead(rate, 0.4),
         "8-bit PWM chip lead. Loop full."),
        (s, "acid_bass.wav", gen_acid_bass(rate, 0.6),
         "303-ish resonant acid bass. Loop full."),
        (s, "organ_drawbar.wav", gen_organ(rate, 0.8),
         "Hammond-ish drawbar organ. Loop full."),
        (s, "brass_synth.wav", gen_brass_synth(rate, 0.7),
         "Synth brass. Loop full."),
        (s, "pwm_lead.wav", gen_pwm_pad_lead(rate, 0.5),
         "Slow PWM square lead. Loop full."),
    ]

    p = "03-pads-choirs"
    items += [
        (p, "pad_warm.wav", gen_pad_warm(rate, 2.2),
         "Warm detuned saw pad. Loop full; vol/pan envs."),
        (p, "pad_choir.wav", gen_pad_choir(rate, 2.5),
         "Choir formant pad. Loop full."),
        (p, "pad_dark.wav", gen_pad_dark(rate, 2.5),
         "Dark low pad. Loop full."),
        (p, "pad_shimmer.wav", gen_pad_shimmer(rate, 2.0),
         "High shimmer pad. Loop full."),
        (p, "pad_strings.wav", gen_pad_strings(rate, 2.2),
         "String-section pad. Loop full."),
        (p, "pad_glass.wav", gen_pad_glass(rate, 2.0),
         "Glass/crystal pad. Loop full."),
        (p, "pad_drone.wav", gen_pad_drone(rate, 3.0),
         "Low atmospheric drone. Loop full."),
    ]

    a = "04-acoustic"
    minor = [130.81, 155.56, 196.00, 261.63, 311.13, 392.00]
    major = [130.81, 164.81, 196.00, 261.63, 329.63, 392.00]
    dim = [130.81, 155.56, 185.00, 246.94, 311.13]
    items += [
        (a, "piano_c4.wav", gen_piano_strike(N(rate, 1.5), rate, 261.63),
         "Piano C4. One-shot."),
        (a, "piano_c3.wav", gen_piano_strike(N(rate, 1.8), rate, 130.81),
         "Piano C3. One-shot."),
        (a, "piano_c5.wav", gen_piano_strike(N(rate, 1.2), rate, 523.25),
         "Piano C5. One-shot."),
        (a, "pizz_g3.wav", gen_pizzicato(N(rate, 0.6), rate, 196.0),
         "Pizzicato G3. One-shot."),
        (a, "pizz_c4.wav", gen_pizzicato(N(rate, 0.55), rate, 261.63),
         "Pizzicato C4. One-shot."),
        (a, "pizz_e4.wav", gen_pizzicato(N(rate, 0.5), rate, 329.63, 56),
         "Pizzicato E4. One-shot."),
        (a, "guitar_a2.wav", gen_guitar_pluck(N(rate, 1.0), rate, 110.0),
         "Guitar pluck A2. One-shot."),
        (a, "guitar_e3.wav", gen_guitar_pluck(N(rate, 0.9), rate, 164.81),
         "Guitar pluck E3. One-shot."),
        (a, "guitar_d3.wav", gen_guitar_pluck(N(rate, 0.95), rate, 146.83),
         "Guitar pluck D3. One-shot."),
        (a, "orch_hit_minor.wav", gen_orch_hit(N(rate, 0.9), rate, minor, 12),
         "Orch stab minor. One-shot."),
        (a, "orch_hit_major.wav", gen_orch_hit(N(rate, 0.85), rate, major, 18),
         "Orch stab major. One-shot."),
        (a, "orch_hit_dim.wav", gen_orch_hit(N(rate, 0.85), rate, dim, 19),
         "Orch stab diminished. One-shot."),
        (a, "bass_acoustic.wav", gen_bass_acoustic(N(rate, 0.9), rate, 55.0),
         "Acoustic bass A1. One-shot."),
        (a, "bass_acoustic_e.wav", gen_bass_acoustic(N(rate, 0.9), rate, 41.20),
         "Acoustic bass E1. One-shot."),
        (a, "flute_soft.wav", gen_flute_soft(rate, 1.0),
         "Soft flute C5. Loop full."),
        (a, "trumpet_f4.wav", gen_trumpet(N(rate, 1.0), rate, 349.23),
         "Trumpet F4. One-shot."),
        (a, "violin_a4.wav", gen_violin_bow(rate, 1.2),
         "Bowed violin A4. Loop full."),
        (a, "marimba_c5.wav", gen_marimba(N(rate, 1.0), rate, 523.25),
         "Marimba C5. One-shot."),
        (a, "harp_g4.wav", gen_harp(N(rate, 1.3), rate, 392.0),
         "Harp G4. One-shot."),
    ]
    return items


def build_volume2(rate: int) -> list[Item]:
    """Disk 2 — variants, FX, breaks, utilities, world."""
    items: list[Item] = []

    d = "01-drums-variants"
    items += [
        (d, "kick_sub.wav", gen_kick(N(rate, 0.70), rate, 35, 90, 6, 1200, 1.2, 30000, 20),
         "Subby long kick. One-shot."),
        (d, "kick_gabber.wav", gen_kick(N(rate, 0.25), rate, 90, 50, 30, 4000, 2.5, 31000, 21),
         "Distorted gabber-ish kick. One-shot."),
        (d, "snare_brush.wav", gen_snare(N(rate, 0.50), rate, 200, 7, 1.0, 18000, 60),
         "Brushy soft snare. One-shot."),
        (d, "snare_gate.wav", gen_snare(N(rate, 0.18), rate, 190, 40, 0.9, 26000, 61),
         "Gated short snare. One-shot."),
        (d, "clap_room.wav", gen_snare_clap(N(rate, 0.55), rate, 88),
         "Roomier clap. One-shot."),
        (d, "hat_808.wav", gen_hat(N(rate, 0.10), rate, 80, 0.02, 10000, 110),
         "808-ish closed hat (less metal). One-shot."),
        (d, "crash_short.wav", gen_crash(N(rate, 0.7), rate, 5.0, 201),
         "Short crash choke. One-shot."),
        (d, "ride_bell.wav", gen_ride(N(rate, 0.6), rate, 220),
         "Ride bell emphasis (shorter). One-shot."),
        (d, "conga_low.wav", gen_conga(N(rate, 0.40), rate, 160),
         "Low conga. One-shot."),
        (d, "conga_high.wav", gen_conga(N(rate, 0.32), rate, 280),
         "High conga. One-shot."),
        (d, "conga_slap.wav", gen_conga(N(rate, 0.22), rate, 320),
         "Conga slap. One-shot."),
        (d, "tom_floor.wav", gen_tom(N(rate, 0.55), rate, 65),
         "Floor tom. One-shot."),
        (d, "tom_rack.wav", gen_tom(N(rate, 0.30), rate, 250),
         "High rack tom. One-shot."),
        (d, "shaker_long.wav", gen_shaker(N(rate, 0.70), rate, 51),
         "Longer shaker. One-shot."),
        (d, "cowbell_mute.wav", gen_cowbell(N(rate, 0.18), rate),
         "Muted short cowbell. One-shot."),
    ]

    s = "02-synth-advanced"
    items += [
        (s, "fm_epiano.wav", gen_fm_bell(N(rate, 1.5), rate, fc=261.63, ratio=1.0),
         "FM electric-piano-ish. One-shot."),
        (s, "fm_pluck.wav", gen_fm_bell(N(rate, 0.6), rate, fc=330.0, ratio=4.0),
         "FM pluck. One-shot."),
        (s, "fm_bass_growl.wav", gen_fm_bass(rate, 0.7, ratio=1.5, idx0=4.5),
         "Growly FM bass. Loop full."),
        (s, "sid_noise_lead.wav", gen_sid_lead(rate, 0.6),
         "SID lead variant (longer loop). Loop full."),
        (s, "chip_bass.wav", gen_chip_lead(rate, 0.5),
         "Chip wave — play down for bass. Loop full."),
        (s, "organ_perc.wav", gen_organ(rate, 0.5),
         "Shorter organ loop (percussive use). Loop full."),
        (s, "acid_squelch.wav", gen_acid_bass(rate, 0.8),
         "Longer acid filter cycle. Loop full."),
        (s, "pwm_deep.wav", gen_pwm_pad_lead(rate, 0.8),
         "Deep PWM body. Loop full."),
        (s, "brass_soft.wav", gen_brass_synth(rate, 1.0),
         "Softer brass loop. Loop full."),
        (s, "wave_saw_oct.wav", gen_single_cycle(rate, "saw", 2),
         "Two-cycle saw (slightly smoother). Loop full."),
        (s, "wave_pulse33.wav", gen_single_cycle(rate, "pulse25", 1),
         "Pulse variant (use as 33% body). Loop full."),
        (s, "theremin.wav", gen_tone_loop(rate, 440.0, 1.0),
         "Pure sine theremin body — vibrato via pattern. Loop full."),
    ]

    fx = "03-fx-impacts"
    items += [
        (fx, "whoosh_up.wav", gen_whoosh(N(rate, 0.8), rate, 1),
         "Noise whoosh rising. One-shot."),
        (fx, "whoosh_down.wav", list(reversed(gen_whoosh(N(rate, 0.8), rate, 2))),
         "Whoosh falling. One-shot."),
        (fx, "reverse_crash.wav", gen_reverse_cymbal(N(rate, 1.2), rate, 2),
         "Reverse crash swell. One-shot."),
        (fx, "laser_zap.wav", gen_laser(N(rate, 0.45), rate),
         "Sci-fi laser zap. One-shot."),
        (fx, "explosion.wav", gen_explosion(N(rate, 0.9), rate, 3),
         "Explosion boom. One-shot."),
        (fx, "powerup.wav", gen_powerup(N(rate, 0.5), rate),
         "Chiptune power-up. One-shot."),
        (fx, "impact_metal.wav", gen_impact_metal(N(rate, 0.7), rate, 4),
         "Metallic impact. One-shot."),
        (fx, "noise_hit.wav", gen_noise_burst(N(rate, 0.25), rate, 20, 5),
         "Short noise hit. One-shot."),
        (fx, "noise_riser.wav", gen_noise_burst(N(rate, 1.0), rate, 2.5, 6),
         "Long noise riser (quiet end). One-shot."),
        (fx, "impact_sub.wav", gen_kick(N(rate, 0.8), rate, 30, 40, 4, 800, 1.0, 28000, 30),
         "Sub impact / trailer boom. One-shot."),
    ]

    br = "04-breaks-loops"
    items += [
        (br, "break_120bpm.wav", gen_break_loop(rate, 120, 1.0, 10),
         "1-bar drum break @ 120 BPM. Loop full."),
        (br, "break_125bpm.wav", gen_break_loop(rate, 125, 1.0, 11),
         "1-bar drum break @ 125 BPM. Loop full."),
        (br, "break_128bpm.wav", gen_break_loop(rate, 128, 1.0, 12),
         "1-bar drum break @ 128 BPM. Loop full."),
        (br, "break_132bpm.wav", gen_break_loop(rate, 132, 1.0, 13),
         "1-bar drum break @ 132 BPM. Loop full."),
        (br, "break_140bpm.wav", gen_break_loop(rate, 140, 1.0, 14),
         "1-bar drum break @ 140 BPM. Loop full."),
        (br, "break_160bpm.wav", gen_break_loop(rate, 160, 1.0, 15),
         "1-bar drum break @ 160 BPM (dnb-ish). Loop full."),
        (br, "break_100bpm.wav", gen_break_loop(rate, 100, 1.0, 16),
         "1-bar drum break @ 100 BPM. Loop full."),
    ]

    u = "05-utility"
    items += [
        (u, "silence_1s.wav", gen_silence(N(rate, 1.0)),
         "1 second silence (padding / offsets)."),
        (u, "tick_1k.wav", gen_tick(N(rate, 0.05), rate, 1000),
         "Metronome tick 1 kHz. One-shot."),
        (u, "tick_2k.wav", gen_tick(N(rate, 0.04), rate, 2000),
         "Bright metronome tick. One-shot."),
        (u, "tick_accent.wav", gen_tick(N(rate, 0.06), rate, 1500),
         "Accent tick. One-shot."),
        (u, "noise_white.wav", gen_noise_loop(rate, 0.5, "white", 9),
         "White noise loop. Loop full."),
        (u, "noise_pink.wav", gen_noise_loop(rate, 0.5, "pink", 10),
         "Pink noise loop. Loop full."),
        (u, "tone_a440.wav", gen_tone_loop(rate, 440.0, 0.5),
         "A440 reference sine. Loop full."),
        (u, "tone_c4.wav", gen_tone_loop(rate, 261.63, 0.5),
         "C4 reference sine. Loop full."),
        (u, "tone_c2.wav", gen_tone_loop(rate, 65.41, 0.5),
         "C2 reference sine. Loop full."),
        (u, "tone_c5.wav", gen_tone_loop(rate, 523.25, 0.5),
         "C5 reference sine. Loop full."),
        (u, "tone_e4.wav", gen_tone_loop(rate, 329.63, 0.5),
         "E4 reference sine. Loop full."),
        (u, "tone_g4.wav", gen_tone_loop(rate, 392.00, 0.5),
         "G4 reference sine. Loop full."),
    ]

    w = "06-world-misc"
    items += [
        (w, "vocal_ah.wav", gen_vocal_ah(rate, 1.0),
         "Vocal 'ah' formant. Loop full."),
        (w, "sitar_d3.wav", gen_sitar_pluck(N(rate, 1.0), rate, 146.83),
         "Sitar-ish pluck D3. One-shot."),
        (w, "kalimba_a4.wav", gen_kalimba(N(rate, 0.9), rate, 440.0),
         "Kalimba A4. One-shot."),
        (w, "kalimba_e5.wav", gen_kalimba(N(rate, 0.8), rate, 659.25),
         "Kalimba E5. One-shot."),
        (w, "marimba_c4.wav", gen_marimba(N(rate, 0.9), rate, 261.63),
         "Marimba C4. One-shot."),
        (w, "harp_c5.wav", gen_harp(N(rate, 1.0), rate, 523.25),
         "Harp C5. One-shot."),
        (w, "pad_glass_v2.wav", gen_pad_glass(rate, 1.8),
         "Glass pad (v2 colour). Loop full."),
        (w, "pad_drone_deep.wav", gen_pad_drone(rate, 2.2),
         "Deep drone. Loop full."),
        (w, "flute_low.wav", gen_flute_soft(rate, 1.0),
         "Flute loop (play down for alto). Loop full."),
        (w, "violin_soft.wav", gen_violin_bow(rate, 1.1),
         "Violin bow loop. Loop full."),
    ]
    return items


# ---------------------------------------------------------------------------
# Write + docs
# ---------------------------------------------------------------------------

def pcm_bytes(items: list[Item]) -> int:
    """Approx on-disk size: PCM + 44-byte WAV header each."""
    return sum(len(pcm) * 2 + 44 for _, _, pcm, _ in items)


def write_volume(root: Path, volume_name: str, title: str, blurb: list[str],
                 items: list[Item], cat_titles: dict[str, str], rate: int) -> int:
    vol = root / volume_name
    if vol.exists():
        shutil.rmtree(vol)
    vol.mkdir(parents=True)

    by_cat: dict[str, list[tuple[str, str, int]]] = {}
    total = 0
    for cat, name, pcm, desc in items:
        path = vol / cat / name
        write_wav(path, pcm, rate)
        by_cat.setdefault(cat, []).append((name, desc, len(pcm)))
        total += path.stat().st_size
        print(f"  wrote {volume_name}/{cat}/{name}  ({len(pcm)} frames)")

    lines = [
        f"# {title}",
        "",
        *blurb,
        "",
        f"- **Sample rate:** {rate} Hz mono 16-bit PCM WAV",
        f"- **FT2 C-4 rate:** {C4_RATE} Hz",
        f"- **Samples:** {len(items)}",
        f"- **On-disk size:** {total / 1024:.0f} KiB "
        f"(Amiga DD target = {AMIGA_DD_KIB} KiB)",
        f"- **Fill:** {100.0 * total / AMIGA_DD_BYTES:.0f}% of one 880 KiB floppy",
        "",
    ]
    for cat, entries in by_cat.items():
        lines += [
            f"## {cat_titles.get(cat, cat)} (`{cat}/`)",
            "",
            "| File | Frames | Notes |",
            "|------|--------|-------|",
        ]
        for name, desc, frames in entries:
            lines.append(f"| `{name}` | {frames} | {desc} |")
        lines.append("")

    lines += [
        "## Loading in FT2 / ft2-clone",
        "",
        "1. Disk Op. → Samples → browse this volume folder",
        "2. Load WAV into an instrument slot",
        "3. Looped material: Sample Ed. → Forward loop, start 0, full length",
        "4. Pads: Instr. Ed. volume + panning envelopes for attack/width",
        "",
    ]
    (vol / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return total


def write_root_readme(root: Path, sizes: dict[str, tuple[int, int]], rate: int) -> None:
    v1_bytes, v1_n = sizes.get("volume1", (0, 0))
    v2_bytes, v2_n = sizes.get("volume2", (0, 0))
    lines = [
        "# FT2 Sample Disks",
        "",
        "Two Amiga double-density–sized sample packs for **ft2-clone / FastTracker II**.",
        "A classic Amiga DD floppy holds **880 KiB** — each volume targets that budget",
        "so a full “disk” of instruments matches the era’s workflow.",
        "",
        "| Volume | Folder | Role | Samples | Size | Fill |",
        "|--------|--------|------|---------|------|------|",
        f"| **Volume 1** | [`volume1/`](volume1/) | Core categories + variants | {v1_n} | "
        f"{v1_bytes/1024:.0f} KiB | {100*v1_bytes/AMIGA_DD_BYTES:.0f}% |",
        f"| **Volume 2** | [`volume2/`](volume2/) | FX, breaks, utils, world | {v2_n} | "
        f"{v2_bytes/1024:.0f} KiB | {100*v2_bytes/AMIGA_DD_BYTES:.0f}% |",
        "",
        f"**Combined:** {(v1_bytes+v2_bytes)/1024:.0f} KiB · {v1_n+v2_n} samples · "
        f"{rate} Hz mono 16-bit",
        "",
        "## Volume 1 — Core Instrument Disk",
        "",
        "Four classic tracker categories, filled out with useful variants:",
        "",
        "- **Drums & Percussion** — kicks (808/909/tight/electro), snares, hats,",
        "  crash/ride, toms, rim, cowbell, clave, shaker",
        "- **Synth Leads & Bass** — single-cycle waves, SID, FM, analog, acid,",
        "  organ, brass, PWM, chip",
        "- **Pads & Choirs** — warm, choir, dark, shimmer, strings, glass, drone",
        "- **Acoustic Emulations** — piano, pizz, guitar, orch hits, bass, flute,",
        "  trumpet, violin, marimba, harp",
        "",
        "See [`volume1/README.md`](volume1/README.md).",
        "",
        "## Volume 2 — Expansion Disk",
        "",
        "Material that did not fit the “core four” mental model:",
        "",
        "- **Drum variants & Latin** — sub/gabber kicks, brush/gate snares, congas…",
        "- **Advanced synth** — more FM colours, longer acid/PWM, theremin body",
        "- **FX & impacts** — whooshes, reverse crash, laser, explosion, power-up",
        "- **Breaks & loops** — 1–2 bar drum breaks at 100–160 BPM (loop in Sample Ed.)",
        "- **Utility** — silence, metronome ticks, white/pink noise, tuning tones",
        "- **World & vocal** — formant voice, sitar, kalimba, extra pads",
        "",
        "See [`volume2/README.md`](volume2/README.md).",
        "",
        "## Loop cheat-sheet",
        "",
        "| Kind | Loop? | Tip |",
        "|------|-------|-----|",
        "| Drum one-shots | No | — |",
        "| Single-cycle waves | Yes, full sample | Rel. note 0 @ 8363 Hz |",
        "| Synth multi / pads | Yes, full sample | Bass: rel. note −12/−24 |",
        "| Break loops | Yes, full sample | Match song BPM to break BPM |",
        "| Noise / tones | Yes, full sample | Utility & beds |",
        "| Acoustic strikes | No | Piano, pizz, guitar, orch… |",
        "",
        "## Regeneration",
        "",
        "```bash",
        "python3 scripts/generate_core_samples.py           # both volumes",
        "python3 scripts/generate_core_samples.py --volume 1",
        "python3 scripts/generate_core_samples.py --volume 2",
        "```",
        "",
        "Generated by `scripts/generate_core_samples.py`.",
        "",
    ]
    (root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate FT2 Amiga-disk sample volumes")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parents[1] / "samples")
    ap.add_argument("--rate", type=int, default=C4_RATE)
    ap.add_argument("--volume", type=int, choices=[1, 2], default=None,
                    help="Generate only volume 1 or 2 (default: both)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    # Remove old flat category dirs from earlier layout
    for old in ("01-drums-percussion", "02-synth-leads-bass",
                "03-pads-choirs", "04-acoustic"):
        p = args.out / old
        if p.is_dir():
            shutil.rmtree(p)
            print(f"  removed legacy {old}/")

    sizes: dict[str, tuple[int, int]] = {}

    if args.volume in (None, 1):
        print("=== Volume 1 (core) ===")
        items = build_volume1(args.rate)
        est = pcm_bytes(items)
        print(f"  catalog: {len(items)} samples, ~{est/1024:.0f} KiB estimated")
        nbytes = write_volume(
            args.out, "volume1", "FT2-Samples-Volume1",
            [
                "Core instrument disk for FastTracker II — drums, synth, pads, acoustic.",
                f"Sized for one **Amiga DD floppy ({AMIGA_DD_KIB} KiB)**.",
            ],
            items, CAT_TITLES_V1, args.rate,
        )
        sizes["volume1"] = (nbytes, len(items))
        print(f"  volume1 total: {nbytes/1024:.1f} KiB "
              f"({100*nbytes/AMIGA_DD_BYTES:.0f}% of {AMIGA_DD_KIB} KiB)")

    if args.volume in (None, 2):
        print("=== Volume 2 (expansion) ===")
        items = build_volume2(args.rate)
        est = pcm_bytes(items)
        print(f"  catalog: {len(items)} samples, ~{est/1024:.0f} KiB estimated")
        nbytes = write_volume(
            args.out, "volume2", "FT2-Samples-Volume2",
            [
                "Expansion disk — drum variants, advanced synth, FX, breaks, utilities,",
                "and world/vocal colours. Second **Amiga DD (880 KiB)** mental model.",
            ],
            items, CAT_TITLES_V2, args.rate,
        )
        sizes["volume2"] = (nbytes, len(items))
        print(f"  volume2 total: {nbytes/1024:.1f} KiB "
              f"({100*nbytes/AMIGA_DD_BYTES:.0f}% of {AMIGA_DD_KIB} KiB)")

    # If only one volume requested, still refresh root readme with whatever exists
    if args.volume is not None:
        for vol in ("volume1", "volume2"):
            if vol in sizes:
                continue
            vpath = args.out / vol
            if vpath.is_dir():
                wavs = list(vpath.rglob("*.wav"))
                nbytes = sum(p.stat().st_size for p in wavs)
                sizes[vol] = (nbytes, len(wavs))

    write_root_readme(args.out, sizes, args.rate)
    print(f"\nRoot manifest: {args.out / 'README.md'}")
    print("Done.")


if __name__ == "__main__":
    main()
