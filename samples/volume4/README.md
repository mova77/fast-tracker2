# FT2-Samples-Volume4

Electro / club remix toolkit — dirty drums, growl bass, stabs,
builds, and four-on-the-floor grooves.
Sample rate **16726 Hz** (2 × classic C-4 8363 Hz).
Sized for one **Amiga DD floppy (880 KiB)**.

- **Sample rate:** 16726 Hz mono 16-bit PCM WAV
- **FT2 C-4 rate:** 8363 Hz
- **Samples:** 47
- **On-disk size:** 851 KiB (Amiga DD target = 880 KiB)
- **Fill:** 97% of one 880 KiB floppy

## Club Drums (`01-club-drums/`)

| File | Frames | Notes |
|------|--------|-------|
| `kick_club.wav` | 6690 | Punchy club kick. One-shot. |
| `kick_dirty.wav` | 6355 | Dirtier clipped kick. One-shot. |
| `kick_tight.wav` | 4683 | Tight dance kick. One-shot. |
| `clap_stack.wav` | 6690 | Stacked electro clap. One-shot. |
| `clap_room.wav` | 9199 | Roomier clap. One-shot. |
| `snare_snap.wav` | 5017 | Snappy rock/electro snare. One-shot. |
| `snare_gate.wav` | 3010 | Gated short snare. One-shot. |
| `hat_closed.wav` | 1338 | Crisp closed electro hat. One-shot. |
| `hat_open.wav` | 5854 | Open electro hat. One-shot. |
| `hat_pedal.wav` | 2341 | Pedal / tight hat. One-shot. |
| `rim_click.wav` | 1003 | Rim / stick click. One-shot. |
| `tom_low.wav` | 6355 | Low club tom fill. One-shot. |
| `tom_high.wav` | 5017 | High club tom fill. One-shot. |

## Dirty Bass (`02-dirty-bass/`)

| File | Frames | Notes |
|------|--------|-------|
| `bass_growl.wav` | 6992 | Dirty mid-growl electro bass. Loop full. |
| `bass_drive.wav` | 6656 | Driving square/saw club bass. Loop full. |
| `bass_acid.wav` | 8323 | High-resonance acid bass/scream. Loop full. |
| `bass_sub.wav` | 6496 | Sub underlayer (E1). Loop full. |
| `bass_hoover.wav` | 6992 | Hoover stack — play down for bass. Loop full. |
| `bass_fm_grit.wav` | 6912 | Gritty FM bass. Loop full. |
| `bass_pwm.wav` | 6720 | PWM body as bass (play down). Loop full. |
| `bass_reese.wav` | 6992 | Detuned dual-saw reese undercurrent. Loop full. |
| `bass_rubber.wav` | 6820 | Rubber / 808-ish sine mono bass. Loop full. |

## Leads & Stabs (`03-leads-stabs/`)

| File | Frames | Notes |
|------|--------|-------|
| `lead_dist.wav` | 6688 | Overdriven saw/square lead. Loop full. |
| `lead_talk.wav` | 7980 | Talkbox/formant lead body. Loop full. |
| `lead_sync.wav` | 6656 | Hard-sync aggressive lead. Loop full. |
| `lead_supersaw.wav` | 6656 | Stacked supersaw lead. Loop full. |
| `lead_ring.wav` | 5852 | Metallic ring-mod lead. Loop full. |
| `stab_cm.wav` | 7526 | Minor chord stab (Cm). One-shot. |
| `stab_gm.wav` | 7024 | Minor chord stab (Gm). One-shot. |
| `stab_fm.wav` | 7024 | Dark minor stab. One-shot. |
| `stab_power.wav` | 6690 | Power-chord style stab. One-shot. |
| `stab_crush.wav` | 5854 | Bitcrushed lo-fi stab. One-shot. |
| `stab_crush_hi.wav` | 5017 | Higher crushed stab. One-shot. |
| `synth_blip.wav` | 2007 | Short crushed synth blip / fill. One-shot. |

## FX & Builds (`04-fx-builds/`)

| File | Frames | Notes |
|------|--------|-------|
| `build_noise.wav` | 16726 | Rising noise build / filter open. One-shot. |
| `build_noise_short.wav` | 8363 | Short noise riser. One-shot. |
| `drop_impact.wav` | 10035 | Club drop impact (sub + smash). One-shot. |
| `whoosh_up.wav` | 9199 | Whoosh rising. One-shot. |
| `whoosh_down.wav` | 8363 | Whoosh falling. One-shot. |
| `reverse_cym.wav` | 12544 | Reverse cymbal swell. One-shot. |
| `laser_hit.wav` | 5017 | Zap / laser hit. One-shot. |
| `noise_hit.wav` | 3010 | Short noise hit. One-shot. |

## Grooves & Breaks (`05-grooves/`)

| File | Frames | Notes |
|------|--------|-------|
| `groove_120.wav` | 33452 | 1-bar four-on-floor @ 120 BPM. Loop full. |
| `groove_125.wav` | 32113 | 1-bar four-on-floor @ 125 BPM. Loop full. |
| `groove_128.wav` | 31361 | 1-bar four-on-floor @ 128 BPM. Loop full. |
| `groove_130.wav` | 30878 | 1-bar four-on-floor @ 130 BPM. Loop full. |
| `groove_128_var.wav` | 31361 | 1-bar variant @ 128 BPM (ghost kick). Loop full. |

## Loading in FT2 / ft2-clone

1. Disk Op. → Samples → browse this volume folder
2. Load WAV into an instrument slot
3. Looped material: Sample Ed. → Forward loop, start 0, full length
4. Pads: Instr. Ed. volume + panning envelopes for attack/width

## Note on 2× C-4 rate

These samples are recorded at **16726 Hz** (2 × 8363).
ft2-clone retunes relative note / finetune on load so C-4 still
plays at concert pitch — you get cleaner highs without manual retuning.
