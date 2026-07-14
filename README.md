# ft2-clone
Fasttracker II clone for Windows/macOS/Linux

Aims to be a highly accurate clone of the classic Fasttracker II software for MS-DOS. \
The XM player itself has been directly ported from the original source code, for maximum accuracy. \
The code is partly my own, partly based on the original FT2 code.

*What is Fasttracker II? Read about it on [Wikipedia](https://en.wikipedia.org/wiki/FastTracker_2).*

# Releases
Windows/macOS binary releases can always be found at [16-bits.org](https://16-bits.org/ft2.php).

Linux binaries can be found [here](https://repology.org/project/fasttracker2/versions). \
If these don't work for you, you'll have to compile the code manually.

# Improvements over original DOS version
- New sample editor features, like waveform generators and resonant filters
- The channel resampler/mixer uses floating-point arithmetics for less errors, and has extra interpolation options (4-point cubic spline and 8-point/16-point windowed-sinc)
- The sample loader supports AIFF/FLAC/OGG/MP3/BRR (SNES) samples and more WAV types than original FT2. It will also attempt to tune the sample (finetune and rel. note) to its playback frequency on load.
- It contains a new "Trim" feature, which will remove unused stuff to potentially make the module smaller
- Drag n' drop of modules/samples
- The waveform display in the sample editor shows peak based data when zoomed out
- Textboxes have a text marking option, where you can cut/copy/paste
- MOD/STM/S3M import has been slightly improved (S3M import is still not ideal, as it's not compatible with XM)
- Supports loading DIGI Booster (non-Pro) modules
- Supports loading Impulse Tracker modules (Awful support! Don't use this for playback)
- It supports loading XMs with stereo samples, uneven amount of channels, more than 32 channels, more than 16 samples per instrument, more than 128 patterns etc. The unsupported data will be mixed to mono/truncated.
- It has some small additions to make life easier (C4/middle-C Hz display in Instr. Ed., envelope point coordinate display, etc).

# Headless interfaces

In addition to the GUI, this fork exposes three headless modes that drive the **real FT2 replayer/mixer** with no framebuffer or window. All three share the same engine initialization path.

| Mode | Invocation | Use case |
|------|------------|----------|
| **CLI** | `ft2-clone --cli …` | Batch render a module file on disk to WAV |
| **REST** | `ft2-clone --server [port]` | HTTP service for upload-and-render workflows |
| **MCP** | `ft2-clone --mcp` | JSON-RPC 2.0 over stdio for LLM/agent module authoring |

Run `ft2-clone --api-help` for CLI and REST usage. See [API_README.md](API_README.md) for REST endpoint details and deployment notes.

### CLI — render to WAV

```bash
ft2-clone --cli render song.mod song.wav
ft2-clone --cli render song.mod song.wav --rate 48000 --bits 16 --amp 16
ft2-clone --cli render song.mod song.wav --start 0 --stop 31 --loops 2
ft2-clone --cli help
```

Options: `--rate` (8000–384000 Hz), `--bits` (16 or 32), `--amp` (1–32), `--start` / `--stop` (song positions 0–255), `--loops` (infinite-loop safety net, default 1).

### REST — HTTP render API

```bash
ft2-clone --server          # default port 8080
ft2-clone --server 9000
```

Endpoints: `GET /api/health`, `POST /api/render` (raw module body), `GET /api/download/<file>`.

### MCP — in-process module authoring

Speaks [Model Context Protocol](https://modelcontextprotocol.io/) over stdin/stdout (one JSON-RPC object per line). **stdout is JSON-RPC only**; diagnostics go to stderr.

Example session:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"module_new","arguments":{"channels":4,"name":"test"}}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"pattern_set_cell","arguments":{"pattern":0,"row":0,"channel":0,"note":"C-4","instrument":1}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"module_save","arguments":{"path":"/tmp/out.xm","format":"xm"}}}' \
  | ft2-clone --mcp
```

**Tools (17):**

- **Module:** `module_new`, `module_load`, `module_info`, `module_save` (xm/mod), `module_render`
- **Song:** `song_set`, `order_set`
- **Pattern:** `pattern_set_cell`, `pattern_get_cell`, `pattern_clear`, `pattern_set_length`, `cell_clear`
- **Samples:** `sample_load`, `sample_save`, `sample_set`, `sample_create_from_pcm` (base64 int16/float32)
- **Instrument:** `instrument_set`

Notes accept strings (`"C-4"`, `"A#5"`, `"off"`) or integers (0–97). Pattern notes use FT2 encoding (C-4 = byte 49).

# Screenshots

![Example #1](https://16-bits.org/ft2-clone-3.png)
![Example #2](https://16-bits.org/ft2-clone-4.png)

# Compiling the code
Build instructions can be found in the repository (HOW-TO-COMPILE.txt).

On macOS (arm64), a quick local build including the headless interfaces:

```bash
brew install sdl2-compat libmicrohttpd
./make-simple.sh
# binary: release/macos/ft2-clone-macos.app/Contents/MacOS/ft2-clone-macos
```

Keep in mind that the program may fail to compile on Linux, depending on your distribution and GCC version. \
Please don't nag me about it, and try to use the Linux packages linked to from [16-bits.org](https://16-bits.org/ft2.php) instead.

PS: The source code is quite hackish and hardcoded. \
My first priority is to make an accurate clone, and not to make flexible and easily modifiable code.

Big parts of the code (except GUI) are directly ported from the original FT2 source code, with permission to use a BSD 3-Clause license.
