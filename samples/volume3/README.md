# FT2-Samples-Volume3

All-synth hi-res disk — waves, bass, leads, pads, keys/FM only.
Sample rate **16726 Hz** (2 × classic C-4 8363 Hz).
Sized for one **Amiga DD floppy (880 KiB)**.

- **Sample rate:** 16726 Hz mono 16-bit PCM WAV
- **FT2 C-4 rate:** 8363 Hz
- **Samples:** 48
- **On-disk size:** 813 KiB (Amiga DD target = 880 KiB)
- **Fill:** 92% of one 880 KiB floppy

## Single-Cycle Waves (`01-waves/`)

| File | Frames | Notes |
|------|--------|-------|
| `wave_sine.wav` | 4160 | Sine @ C4 (~0.25s, seamless). Loop full (smpl). |
| `wave_saw.wav` | 4160 | Saw @ C4 (~0.25s, seamless). Loop full (smpl). |
| `wave_square.wav` | 4160 | Square @ C4 (~0.25s, seamless). Loop full (smpl). |
| `wave_pulse25.wav` | 4160 | 25% pulse @ C4 (~0.25s). Loop full (smpl). |
| `wave_pulse12.wav` | 4160 | 12.5% pulse @ C4 (~0.25s, SID-like). Loop full (smpl). |
| `wave_triangle.wav` | 4160 | Triangle @ C4 (~0.25s). Loop full (smpl). |
| `wave_halfsine.wav` | 4160 | Half-sine @ C4 (~0.25s). Loop full (smpl). |
| `wave_supersaw.wav` | 4992 | Detuned supersaw (~0.30s). Loop full (smpl). |
| `wave_noise.wav` | 4992 | Deterministic noise (~0.30s). Loop full (smpl). |

## Synth Bass (`02-bass/`)

| File | Frames | Notes |
|------|--------|-------|
| `analog_bass.wav` | 6699 | Analog saw+square bass. Loop full. |
| `analog_bass_sub.wav` | 6496 | Sub analog bass (E1). Loop full. |
| `fm_bass.wav` | 6656 | 2-op FM bass. Loop full; try rel. note −12. |
| `fm_bass_metal.wav` | 6656 | Metallic FM bass. Loop full. |
| `fm_bass_growl.wav` | 7424 | Growly FM bass. Loop full. |
| `acid_bass.wav` | 8512 | 303-ish resonant acid bass. Loop full. |
| `acid_squelch.wav` | 9120 | Longer acid filter cycle. Loop full. |
| `chip_bass.wav` | 5856 | Chip wave — play down for bass. Loop full. |
| `hoover_bass.wav` | 7600 | Hoover stack (play down). Loop full. |
| `pwm_bass.wav` | 6720 | PWM body as bass (play down). Loop full. |

## Synth Leads (`03-leads/`)

| File | Frames | Notes |
|------|--------|-------|
| `sid_lead.wav` | 6720 | SID pulse+tri lead. Loop full. |
| `chip_lead.wav` | 5856 | 8-bit PWM chip lead. Loop full. |
| `pwm_lead.wav` | 6720 | Slow PWM square lead. Loop full. |
| `pwm_deep.wav` | 7552 | Deeper PWM body. Loop full. |
| `brass_synth.wav` | 7524 | Synth brass. Loop full. |
| `brass_soft.wav` | 8360 | Softer brass. Loop full. |
| `hard_sync.wav` | 6656 | Hard-sync saw lead. Loop full. |
| `ring_mod.wav` | 5852 | Ring-mod metallic lead. Loop full. |
| `supersaw_lead.wav` | 6656 | Multi-voice supersaw lead. Loop full. |
| `hoover.wav` | 7600 | Classic hoover / Juno stack. Loop full. |
| `theremin.wav` | 6688 | Pure sine theremin body. Loop full. |
| `sync_octave.wav` | 5888 | Hard-sync variant (use with arps). Loop full. |

## Synth Pads (`04-pads/`)

| File | Frames | Notes |
|------|--------|-------|
| `pad_warm.wav` | 17374 | Warm detuned pad. Loop full; vol/pan envs. |
| `pad_choir.wav` | 18392 | Choir formant pad. Loop full. |
| `pad_dark.wav` | 18396 | Dark low pad. Loop full. |
| `pad_shimmer.wav` | 15872 | High shimmer pad. Loop full. |
| `pad_strings.wav` | 17664 | String-section pad. Loop full. |
| `pad_glass.wav` | 15960 | Glass/crystal pad. Loop full. |
| `pad_drone.wav` | 19152 | Low atmospheric drone. Loop full. |
| `pad_supersaw.wav` | 14208 | Supersaw pad bed. Loop full. |

## Keys & FM (`05-keys-fm/`)

| File | Frames | Notes |
|------|--------|-------|
| `organ_drawbar.wav` | 8320 | Hammond-ish drawbar organ. Loop full. |
| `organ_perc.wav` | 5888 | Shorter organ (percussive). Loop full. |
| `fm_bell.wav` | 11708 | Bright FM bell. One-shot. |
| `fm_bell_low.wav` | 13380 | Lower FM bell/chime. One-shot. |
| `fm_epiano.wav` | 15053 | FM electric-piano-ish. One-shot. |
| `fm_pluck.wav` | 6690 | FM pluck. One-shot. |
| `fm_bell_bright.wav` | 10871 | Bright high FM bell. One-shot. |
| `tone_c4.wav` | 5824 | C4 sine reference @ 2× rate. Loop full. |
| `tone_a440.wav` | 5852 | A440 sine reference. Loop full. |

## Loading in FT2 / ft2-clone

1. Disk Op. → Samples → browse this volume folder
2. Load WAV into an instrument slot
3. Looped material: Sample Ed. → Forward loop, start 0, full length
4. Pads: Instr. Ed. volume + panning envelopes for attack/width

## Note on 2× C-4 rate

These samples are recorded at **16726 Hz** (2 × 8363).
ft2-clone retunes relative note / finetune on load so C-4 still
plays at concert pitch — you get cleaner highs without manual retuning.
