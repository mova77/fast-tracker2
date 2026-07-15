# mods/ — Amiga & DOS game music reference collection

A curated library of tracker modules ripped from classic games, plus original compositions inspired by the collection. Used as reference material for the ft2-clone headless interfaces (CLI, REST, MCP).

**Total tracker files:** 128 (82 `.mod`, 40 `.s3m`, 3 `.xm`, 3 `.it`) across 11 game folders + 1 original folder.  
**Source archives:** Mirsoft / UnExoticA game-rip packs (see per-folder `info.txt` and `archives/*.zip`).

---

## Collection at a glance

| Folder | Platform | Year | Format | Tracks | Composer(s) | Notes |
|--------|----------|------|--------|--------|---------------|-------|
| [Agony](Agony/) | Amiga | 1992 | MOD | 12 | Tim Wright, Franck Sauer, et al. | Psygnosis; loaders + intro; unused demo mods included |
| [Alien 3](Alien%203/) | Amiga | 1992 | MOD | 6 | Matt Furniss | Level themes + boss |
| [Cannon Fodder](Cannon%20Fodder/) | Amiga | 1993 | MOD | 1 | Richard Joseph | Single long theme (~243 KB) |
| [Fantastic Dizzy](Fantastic%20Dizzy/) | Amiga | 1993 | MOD | 17 | Matthew Simmonds | Zone stingers; title/undersea standouts |
| [Jazz Jackrabbit](Jazz%20Jackrabbit/) | PC | 1994 | S3M | 33 | Robert Allen, Joshua Jensen | Not MOD/XM — Scream Tracker 3 |
| [Lotus 2](Lotus%202/) | Amiga | 1991 | MOD, XM | 12 | Barry Leitch | Racing courses; `lotuscr1/2.xm` are post-release remixes |
| [Lotus 3](Lotus%203/) | Amiga | 1992 | MOD | 23 | Patrick Phelan | Largest Amiga set; course + CD-style tracks |
| [Neon Overdrive](Neon%20Overdrive/) | — | 2026 | XM | 1 | ft2-clone MCP (original) | Original composition inspired by this collection |
| [One Must Fall 2097](One%20Must%20Fall%202097/) | DOS | 1994 | MOD | 2 | — | Prelude + intro |
| [Shadow of the Beast](Shadow%20of%20the%20Beast/) | Amiga | 1989 | MOD | 4 | David Whittaker (conv. Jogeir Liljedahl) | Long atmospheric pieces |
| [Super Street Fighter 2 Turbo](Super%20Street%20Fighter%202%20Turbo/) | PC | 1994 | IT | 1 | — | Impulse Tracker |
| [Turrican 2](Turrican%202/) | Amiga | 1991 | MOD | 7 | Chris Huelsbeck (community remixes) | Dense arrangements; not original Factor 5 rips |

---

## Findings (what these modules have in common)

Analysis used ProTracker MOD offsets (song length @950, orders @952, channel ID @1080) and FT2 XM headers, cross-checked with `ft2-clone --mcp` → `module_load` / `module_info`.

### Format & channels

- **78 of 80** scanned `.mod`/`.xm` game rips are **4-channel ProTracker MOD** (`M.K.` / `M!K!`).
- **XM** appears only in **Lotus 2** (`lotuscr1.xm`, `lotuscr2.xm`) — Barry Leitch remixes, not original in-game format.
- **Jazz Jackrabbit** uses **S3M**; **SSF2 Turbo** uses **IT** — loadable by ft2-clone but outside the MOD/XM catalog below.

### Size & complexity

| Metric | Typical range | Notable outliers |
|--------|---------------|------------------|
| File size | 4–100 KB (most); up to 243 KB | Cannon Fodder (243K), Agony intro (175K), Turrican remix (147K) |
| Patterns | 2–35 | Turrican `Turrica2 - Remix.mod` (60 pat) |
| Song length (orders) | 2–50 | Turrican remixes (45–66), Lotus 2 XM remixes (276 orders in file) |
| Pattern rows | 64 (implicit on MOD) | Course mods often 16-row feel within 64-row patterns |

### Musical / structural traits

1. **Four channels as roles** — drums, bass, harmony, lead/FX; not “more tracks.”
2. **Short loops** — loaders 1–7 orders; zone stingers 2–12; level themes 8–50.
3. **Tempo** — MOD has no header BPM; ft2-clone defaults **125 BPM, speed 6**. Racing/action material often feels **130+** via in-pattern **Fxx** commands.
4. **Pattern economy** — few patterns transposed/reused (Lotus 3 courses share 3–6 patterns across 16 orders).
5. **Sample-heavy** — file size is mostly sample data; pattern data is tiny.
6. **Genre fingerprints**
   - **Racing (Lotus 2/3):** driving drums, repetitive hooks, 16-order course loops
   - **Platform (Fantastic Dizzy):** short zone cues, lighter percussion
   - **Action (Alien 3, Turrican):** denser percussion, minor keys, arpeggios
   - **Atmospheric (Agony, Shadow of the Beast):** longer samples, sparse loaders, slow builds

### Most complex modules (patterns × song length)

| Module | Pat | Len | Size | Style |
|--------|-----|-----|------|-------|
| `Turrican 2/Turrica2 - Remix.mod` | 60 | 66 | 147K | Dense action remix |
| `Turrican 2/turrican2ingame1rmx.mod` | 55 | 56 | 107K | In-game remix |
| `Shadow of the Beast/Beast1_4.mod` | 35 | 48 | 94K | Cinematic |
| `Agony/agony intro.mod` | 17 | 41 | 175K | Large sample set |
| `Lotus 3/l3_cd3_lotus3.mod` | 19 | 29 | 75K | CD-style hook |

---

## Catalog — ProTracker MOD & FastTracker XM

Columns: **Ch** = channels, **Pat** = pattern count (max order + 1), **Len** = song length in orders, **Size** = file size.

### Agony

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `agony intro.mod` | MOD | 4 | 17 | 41 | 175K | mod.agony intro |
| `agony_end of game.mod` | MOD | 4 | 19 | 21 | 85K | agony_end of game |
| `foret(unused).mod` | MOD | 4 | 21 | 44 | 49K | foret |
| `Loading_Mountain.mod` | MOD | 4 | 7 | 7 | 24K | MOD.Loading_Mountain |
| `loading_sea.mod` | MOD | 4 | 3 | 3 | 22K | loading_sea |
| `loading_sea(unused).mod` | MOD | 4 | 16 | 17 | 75K | loading_sea |
| `loading_marshes.mod` | MOD | 4 | 1 | 1 | 21K | loading_marshes |
| `loading_forest.mod` | MOD | 4 | 1 | 1 | 15K | loading_forest |
| `loading_highlands.mod` | MOD | 4 | 1 | 1 | 23K | loading_highlands |
| `loading_fire.mod` | MOD | 4 | 5 | 1 | 26K | loading_fire |
| `agony-highlands2(unused).mod` | MOD | 4 | 12 | 12 | 46K | agony-highlands2 |
| `agony(volcano load)(unused).mod` | MOD | 4 | 7 | 7 | 24K | agony(volcano load) |

### Alien 3

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `a3level1.mod` | MOD | 4 | 10 | 11 | 68K | a3level1 |
| `a3level2.mod` | MOD | 4 | 10 | 11 | 75K | a3level2 |
| `a3level3.mod` | MOD | 4 | 8 | 9 | 73K | a3level3 |
| `a3level4.mod` | MOD | 4 | 6 | 13 | 71K | a3level4 |
| `a3level5.mod` | MOD | 4 | 5 | 10 | 74K | a3level5.mod |
| `a3boss.mod` | MOD | 4 | 4 | 4 | 69K | a3boss |

### Cannon Fodder

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `CFODDER.MOD` | MOD | 4 | 18 | 30 | 243K | Cannon Fodder |

### Fantastic Dizzy

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `f.a.dizzy-title.mod` | MOD | 4 | 10 | 11 | 45K | f.a.dizzy-title |
| `f.a.dizzy-undersea.mod` | MOD | 4 | 8 | 9 | 16K | f.a.dizzy-undersea |
| `f.a.dizzy-castlesub.mod` | MOD | 4 | 10 | 11 | 24K | f.a.dizzy-castlesub |
| `f.a.dizzy-treehouse.mod` | MOD | 4 | 8 | 8 | 36K | f.a.dizzy-treehouse |
| `f.a.dizzy-complete.mod` | MOD | 4 | 4 | 4 | 36K | f.a.dizzy-complete |
| `f.a.dizzy-pirate.mod` | MOD | 4 | 3 | 3 | 28K | f.a.dizzy-pirate |
| `f.a.dizzy-bubble.mod` | MOD | 4 | 4 | 4 | 26K | f.a.dizzy-bubble |
| `f.a.dizzy-minecart.mod` | MOD | 4 | 7 | 12 | 18K | f.a.dizzy-minecart |
| `f.a.dizzy-puzzle.mod` | MOD | 4 | 8 | 11 | 16K | f.a.dizzy-puzzle |
| `f.a.dizzy-graveyard.mod` | MOD | 4 | 6 | 8 | 9K | f.a.dizzy-graveyard |
| `f.a.dizzy-castle.mod` | MOD | 4 | 4 | 4 | 17K | f.a.dizzy-castle |
| `f.a.dizzy-rapids.mod` | MOD | 4 | 2 | 3 | 11K | f.a.dizzy-rapids |
| `f.a.dizzy-world.mod` | MOD | 4 | 2 | 2 | 10K | f.a.dizzy-world |
| `f.a.dizzy-archery.mod` | MOD | 4 | 4 | 4 | 8K | f.a.dizzy-archery |
| `f.a.dizzy-zak.mod` | MOD | 4 | 4 | 4 | 7K | f.a.dizzy-zak |
| `f.a.dizzy-gameover.mod` | MOD | 4 | 2 | 2 | 8K | f.a.dizzy-gameover |
| `f.a.dizzy-loselife.mod` | MOD | 4 | 2 | 2 | 4K | f.a.dizzy-loselife |

### Lotus 2

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `lotus20.mod` | MOD | 4 | 15 | 22 | 81K | LOTUS 2 |
| `lotus26.mod` | MOD | 4 | 23 | 34 | 93K | new |
| `lotus2rmx.mod` | MOD | 4 | 17 | 15 | 63K | Lotus2 Liverpool RMX |
| `lotus21.mod` | MOD | 4 | 3 | 3 | 38K | jingle6 |
| `lotus22.mod` | MOD | 4 | 4 | 4 | 26K | jingle3 |
| `lotus23.mod` | MOD | 4 | 4 | 4 | 40K | jingle2 |
| `lotus24.mod` | MOD | 4 | 3 | 3 | 27K | jingle7 |
| `lotus25.mod` | MOD | 4 | 3 | 3 | 31K | jingle8 |
| `lotus27.mod` | MOD | 4 | 3 | 3 | 36K | jingle1 |
| `lotus28.mod` | MOD | 4 | 4 | 4 | 19K | jingle4 |
| `lotuscr1.xm` | XM | 38* | 0* | 276* | 171K | new (remix) |
| `lotuscr2.xm` | XM | 32* | 6* | 276* | 190K | new (remix) |

\* XM header fields for the Lotus 2 remixes are non-standard; load in ft2-clone for accurate playback metadata.

### Lotus 3

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `l3_intro.mod` | MOD | 4 | 10 | 10 | 61K | l3_intro |
| `l3_cd3_lotus3.mod` | MOD | 4 | 19 | 29 | 75K | l3_cd3_lotus3 |
| `l3_cd2-metalmachine.mod` | MOD | 4 | 17 | 39 | 60K | L3_CD2-MetalMachine |
| `l3_cd4-spaceninja.mod` | MOD | 4 | 15 | 31 | 71K | l3_cd4-spaceninja |
| `l3_cd5-miamiice.mod` | MOD | 4 | 16 | 29 | 58K | l3_cd5-miamiice |
| `l3_cd1-breathless.mod` | MOD | 4 | 12 | 22 | 63K | l3_cd1-breathless |
| `l3_cd6-shamrip.mod` | MOD | 4 | 11 | 24 | 58K | l3_cd6-shamrip |
| `l3_complete.mod` | MOD | 4 | 9 | 13 | 50K | l3_complete |
| `l3_storm.mod` | MOD | 4 | 6 | 16 | 38K | l3_storm |
| `l3_wind.mod` | MOD | 4 | 6 | 16 | 38K | l3_wind |
| `l3_forest.mod` | MOD | 4 | 5 | 16 | 39K | l3_forest |
| `l3_fog.mod` | MOD | 4 | 5 | 16 | 36K | l3_fog |
| `l3_futureworld.mod` | MOD | 4 | 5 | 16 | 33K | l3_futureworld |
| `l3_dez.mod` | MOD | 4 | 5 | 16 | 35K | l3_dez |
| `l3_results.mod` | MOD | 4 | 5 | 16 | 37K | l3_results |
| `l3_night.mod` | MOD | 4 | 5 | 16 | 27K | l3_night |
| `l3_rally.mod` | MOD | 4 | 3 | 16 | 28K | l3_rally |
| `l3_snow.mod` | MOD | 4 | 3 | 16 | 30K | l3_snow |
| `l3_roadwerx.mod` | MOD | 4 | 4 | 16 | 32K | l3_roadwerx |
| `l3_marsh.mod` | MOD | 4 | 4 | 16 | 31K | l3_marsh |
| `l3_motorway.mod` | MOD | 4 | 4 | 16 | 24K | l3_motorway |
| `l3_mountain.mod` | MOD | 4 | 4 | 16 | 22K | l3_mountain |
| `l3_gameover.mod` | MOD | 4 | 2 | 16 | 33K | l3_gameover |

### One Must Fall 2097

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `01-PRELUDE.MOD` | MOD | 4 | 6 | 11 | 21K | prelude |
| `02-INTRO.MOD` | MOD | 4 | 6 | 6 | 33K | One Must Fall A1 |

### Shadow of the Beast

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `Beast1_4.mod` | MOD | 4 | 35 | 48 | 94K | Beast-Playtune4 |
| `Beast1_3.mod` | MOD | 4 | 21 | 50 | 97K | Beast-Playtune3 |
| `Beast1_2.mod` | MOD | 4 | 27 | 32 | 97K | Beast-Playtune2 |
| `Beast1_5.mod` | MOD | 4 | 16 | 25 | 101K | Beast-Playtune5 |

### Turrican 2

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `Turrica2 - Remix.mod` | MOD | 4 | 60 | 66 | 147K | turrican ii.noise3 |
| `turrican2ingame1rmx.mod` | MOD | 4 | 55 | 56 | 107K | turrican 2.1 |
| `turrican2ingame2rmx.mod` | MOD | 4 | 38 | 45 | 88K | turrican 2.3 |
| `TURRICN2.MOD` | MOD | 4 | 11 | 14 | 86K | Turrican 2-REMIX |
| `the_great_bath.mod` | MOD | 4 | 15 | 16 | 95K | the great bath |
| `turrican2endrmx.mod` | MOD | 4 | 14 | 18 | 102K | turrican end-part |
| `turrican2titlermx.mod` | MOD | 4 | 9 | 9 | 37K | turrican ii |

### Neon Overdrive (original)

| File | Fmt | Ch | Pat | Len | Size | Title |
|------|-----|----|-----|-----|------|-------|
| `neon_overdrive.xm` | XM | 4 | 8 | 48 | 41K | Neon Overdrive |

Engine metadata (via `--mcp` → `module_info`): 132 BPM, speed 6, loop start 8.  
Compose script: [`../scripts/compose_neon_overdrive.py`](../scripts/compose_neon_overdrive.py).

---

## Other formats (not in MOD/XM catalog)

### Jazz Jackrabbit — 33× S3M

33 Scream Tracker 3 modules — see [`Jazz Jackrabbit/`](Jazz%20Jackrabbit/) (e.g. `Battleships.s3m`, `Diamondus.s3m`, `Ending.s3m`, …). Full list in that folder's `info.txt`.

### Super Street Fighter 2 Turbo — 1× IT

`CAMMY214.IT`

---

## Using this collection with ft2-clone

```bash
# Render any module to WAV (CLI)
ft2-clone --cli render "mods/Lotus 3/l3_storm.mod" /tmp/l3_storm.wav

# Inspect via MCP
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"module_load","arguments":{"path":"mods/Agony/agony intro.mod"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"module_info","arguments":{}}}' \
  | ft2-clone --mcp
```

Regenerate MOD/XM header stats locally:

```bash
python3 scripts/catalog_mods.py   # if added; or see git history for inline parser
```

---

## Original compositions

| Folder | Description |
|--------|-------------|
| [Neon Overdrive](Neon%20Overdrive/) | C-minor racing/action XM — 8 patterns, 48 orders, 6 synthesized instruments. Inspired by Lotus 3 + Turrican density + Agony breakdown + 4ch Amiga layout. |

---

## Archives

`archives/` contains the original `.zip` packs (Lotus 2/3, Agony, Turrican 2, etc.) from which the per-game folders were extracted.