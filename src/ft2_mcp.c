// MCP server: JSON-RPC 2.0 over stdio for headless FT2 module authoring.
// stdout carries only JSON-RPC responses; diagnostics go to stderr.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdint.h>
#include <stdbool.h>
#ifdef _WIN32
#include <direct.h>
#define mcp_getcwd _getcwd
#define mcp_chdir  _chdir
#else
#include <unistd.h>
#define mcp_getcwd getcwd
#define mcp_chdir  chdir
#endif

#include "jsmn.h"
#include "ft2_header.h"
#include "ft2_audio.h"
#include "ft2_diskop.h"
#include "ft2_module_loader.h"
#include "ft2_module_saver.h"
#include "ft2_pattern_ed.h"
#include "ft2_replayer.h"
#include "ft2_renderer.h"
#include "ft2_sample_loader.h"
#include "ft2_structs.h"
#include "ft2_tables.h"
#include "ft2_unicode.h"
#include "ft2_wav_renderer.h"
#include "ft2_mcp.h"

#define MCP_PROTOCOL_VERSION "2024-11-05"
#define MCP_SERVER_NAME      "ft2-clone"
#define MCP_SERVER_VERSION   "1.0"
#define MCP_MAX_LINE         65536
#define MCP_MAX_TOKENS       512
#define MCP_RESULT_BUF       4096

static const char *noteNameTab[12] =
{
	"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
};

/* --- jsmn helpers ------------------------------------------------------- */

static bool json_token_eq(const char *js, const jsmntok_t *tok, const char *s)
{
	const int len = (int)strlen(s);
	return (tok->end - tok->start == len &&
		memcmp(js + tok->start, s, (size_t)len) == 0);
}

static int json_skip_tokens(const jsmntok_t *toks, int i)
{
	int j = i + 1;
	for (int k = 0; k < toks[i].size; k++)
		j = json_skip_tokens(toks, j);
	return j;
}

static int json_object_find(const char *js, const jsmntok_t *toks, int obj_idx,
	const char *key)
{
	if (toks[obj_idx].type != JSMN_OBJECT)
		return -1;

	int idx = obj_idx + 1;
	for (int i = 0; i < toks[obj_idx].size; i++)
	{
		if (json_token_eq(js, &toks[idx], key))
			return idx + 1;
		idx = json_skip_tokens(toks, idx + 1);
	}
	return -1;
}

static bool json_token_string(const char *js, const jsmntok_t *tok,
	char *out, size_t outSize)
{
	if (tok->type != JSMN_STRING || outSize == 0)
		return false;

	const int len = tok->end - tok->start;
	if (len < 0 || (size_t)len >= outSize)
		return false;

	memcpy(out, js + tok->start, (size_t)len);
	out[len] = '\0';
	return true;
}

static bool json_token_int(const char *js, const jsmntok_t *tok, int32_t *out)
{
	if (tok->type != JSMN_PRIMITIVE)
		return false;

	char tmp[32];
	const int len = tok->end - tok->start;
	if (len <= 0 || len >= (int)sizeof(tmp))
		return false;

	memcpy(tmp, js + tok->start, (size_t)len);
	tmp[len] = '\0';

	char *end = NULL;
	const long v = strtol(tmp, &end, 10);
	if (end == tmp)
		return false;

	*out = (int32_t)v;
	return true;
}

static bool json_token_bool(const char *js, const jsmntok_t *tok, bool *out)
{
	if (tok->type != JSMN_PRIMITIVE)
		return false;

	const int len = tok->end - tok->start;
	if (len == 4 && memcmp(js + tok->start, "true", 4) == 0)
	{
		*out = true;
		return true;
	}
	if (len == 5 && memcmp(js + tok->start, "false", 5) == 0)
	{
		*out = false;
		return true;
	}
	return false;
}

static bool json_has_key(const char *js, const jsmntok_t *toks, int obj_idx,
	const char *key)
{
	return json_object_find(js, toks, obj_idx, key) >= 0;
}

static bool args_get_string(const char *js, const jsmntok_t *toks, int args_idx,
	const char *key, char *out, size_t outSize)
{
	const int vidx = json_object_find(js, toks, args_idx, key);
	if (vidx < 0 || toks[vidx].type != JSMN_STRING)
		return false;
	return json_token_string(js, &toks[vidx], out, outSize);
}

static bool args_get_int(const char *js, const jsmntok_t *toks, int args_idx,
	const char *key, int32_t *out, bool *found)
{
	const int vidx = json_object_find(js, toks, args_idx, key);
	if (vidx < 0)
	{
		*found = false;
		return true;
	}

	*found = true;
	return json_token_int(js, &toks[vidx], out);
}

static bool args_get_note(const char *js, const jsmntok_t *toks, int args_idx,
	const char *key, uint8_t *out, bool *found, char *err, size_t errSize)
{
	const int vidx = json_object_find(js, toks, args_idx, key);
	if (vidx < 0)
	{
		*found = false;
		return true;
	}

	*found = true;

	if (toks[vidx].type == JSMN_PRIMITIVE)
	{
		int32_t n = 0;
		if (!json_token_int(js, &toks[vidx], &n))
		{
			snprintf(err, errSize, "invalid note integer");
			return false;
		}
		if (n < 0 || n > NOTE_OFF)
		{
			snprintf(err, errSize, "note must be 0..%d", NOTE_OFF);
			return false;
		}
		*out = (uint8_t)n;
		return true;
	}

	if (toks[vidx].type != JSMN_STRING)
	{
		snprintf(err, errSize, "note must be a string or integer");
		return false;
	}

	char noteStr[32];
	if (!json_token_string(js, &toks[vidx], noteStr, sizeof(noteStr)))
	{
		snprintf(err, errSize, "invalid note string");
		return false;
	}

	/* trim */
	char *s = noteStr;
	while (*s && isspace((unsigned char)*s))
		s++;

	if (*s == '\0')
	{
		*out = 0;
		return true;
	}

	if (strcasecmp(s, "off") == 0 || strcmp(s, "===") == 0)
	{
		*out = NOTE_OFF;
		return true;
	}

	int semi = -1;
	switch (toupper((unsigned char)s[0]))
	{
		case 'C': semi = 0;  break;
		case 'D': semi = 2;  break;
		case 'E': semi = 4;  break;
		case 'F': semi = 5;  break;
		case 'G': semi = 7;  break;
		case 'A': semi = 9;  break;
		case 'B': semi = 11; break;
		default:
			snprintf(err, errSize, "unrecognized note: %s", noteStr);
			return false;
	}

	char *p = s + 1;
	if (*p == '#' || *p == 'b')
	{
		if (*p == '#')
			semi++;
		else
			semi--;
		p++;
	}

	if (semi < 0)
		semi += 12;
	else if (semi > 11)
		semi -= 12;

	if (*p == '-')
		p++;

	if (!isdigit((unsigned char)*p))
	{
		snprintf(err, errSize, "missing octave in note: %s", noteStr);
		return false;
	}

	const int octave = (int)strtol(p, NULL, 10);
	if (octave < 0 || octave > 9)
	{
		snprintf(err, errSize, "octave out of range in note: %s", noteStr);
		return false;
	}

	const int index = (octave * 12) + semi;
	if (index < 0 || index > 95)
	{
		snprintf(err, errSize, "note out of tracker range: %s", noteStr);
		return false;
	}

	*out = (uint8_t)(index + 1);
	return true;
}

/* --- JSON output helpers ------------------------------------------------ */

static size_t json_append_escaped(char *dst, size_t pos, size_t cap, const char *src)
{
	for (size_t i = 0; src[i] != '\0'; i++)
	{
		const char c = src[i];
		const char *rep = NULL;
		char scratch[2];

		switch (c)
		{
			case '\\': rep = "\\\\"; break;
			case '"':  rep = "\\\""; break;
			case '\n': rep = "\\n";  break;
			case '\r': rep = "\\r";  break;
			case '\t': rep = "\\t";  break;
			default:
				if ((unsigned char)c < 0x20)
				{
					snprintf(scratch, sizeof(scratch), "%c", c);
					rep = scratch;
				}
				break;
		}

		if (rep != NULL)
		{
			const size_t rlen = strlen(rep);
			if (pos + rlen >= cap)
				break;
			memcpy(dst + pos, rep, rlen);
			pos += rlen;
		}
		else
		{
			if (pos + 1 >= cap)
				break;
			dst[pos++] = c;
		}
	}

	if (pos < cap)
		dst[pos] = '\0';
	return pos;
}

static void mcp_write_response(const char *id_json, const char *result_json)
{
	printf("{\"jsonrpc\":\"2.0\",\"id\":%s,\"result\":%s}\n",
		id_json ? id_json : "null", result_json);
	fflush(stdout);
}

static void mcp_write_error(const char *id_json, int code, const char *message)
{
	char msgEsc[MCP_RESULT_BUF];
	json_append_escaped(msgEsc, 0, sizeof(msgEsc), message);

	printf("{\"jsonrpc\":\"2.0\",\"id\":%s,\"error\":{\"code\":%d,\"message\":\"%s\"}}\n",
		id_json ? id_json : "null", code, msgEsc);
	fflush(stdout);
}

static void mcp_write_tool_result(const char *id_json, const char *text, bool isError)
{
	char textEsc[MCP_RESULT_BUF * 2];
	json_append_escaped(textEsc, 0, sizeof(textEsc), text);

	char result[MCP_RESULT_BUF * 3];
	snprintf(result, sizeof(result),
		"{\"content\":[{\"type\":\"text\",\"text\":\"%s\"}],\"isError\":%s}",
		textEsc, isError ? "true" : "false");
	mcp_write_response(id_json, result);
}

/* --- note formatting ------------------------------------------------------ */

static void note_to_string(uint8_t note, char *out, size_t outSize)
{
	if (outSize == 0)
		return;

	if (note == 0)
	{
		out[0] = '\0';
		return;
	}

	if (note == NOTE_OFF)
	{
		strncpy(out, "off", outSize - 1);
		out[outSize - 1] = '\0';
		return;
	}

	if (note < 1 || note > 96)
	{
		snprintf(out, outSize, "%u", note);
		return;
	}

	const int idx = (int)note - 1;
	const uint8_t semi = noteTab1[idx];
	const uint8_t octave = noteTab2[idx];
	const char *name = noteNameTab[semi];

	if (strchr(name, '#') != NULL)
		snprintf(out, outSize, "%s%d", name, octave);
	else
		snprintf(out, outSize, "%s-%d", name, octave);
}

/* --- engine helpers ----------------------------------------------------- */

static bool ensureReservedInstruments(void)
{
	if (instr[0] == NULL)
	{
		if (!allocateInstr(0))
			return false;
		instr[0]->smp[0].volume = 0;
	}

	if (instr[130] == NULL)
	{
		if (!allocateInstr(130))
			return false;
		memset(instr[130], 0, sizeof(instr_t));
	}

	if (instr[131] == NULL)
	{
		if (!allocateInstr(131))
			return false;
		memset(instr[131], 0, sizeof(instr_t));
		for (int32_t i = 0; i < 16; i++)
			instr[131]->smp[i].panning = 128;
	}

	return true;
}

static int32_t normalize_channel_count(int32_t channels)
{
	if (channels < 2)
		channels = 2;
	if (channels > MAX_CHANNELS)
		channels = MAX_CHANNELS;
	channels &= ~1;
	if (channels < 2)
		channels = 2;
	return channels;
}

static bool tool_module_new(const char *js, const jsmntok_t *toks, int args_idx,
	char *err, size_t errSize)
{
	int32_t channels = 8;
	bool found = false;

	if (!args_get_int(js, toks, args_idx, "channels", &channels, &found))
	{
		snprintf(err, errSize, "invalid channels argument");
		return false;
	}

	char name[32] = "";
	(void)args_get_string(js, toks, args_idx, "name", name, sizeof(name));

	channels = normalize_channel_count(channels);

	lockMixerCallback();

	freeAllInstr();
	freeAllPatterns();

	playMode = PLAYMODE_IDLE;
	songPlaying = false;

	song.songLength = 1;
	song.songLoopStart = 0;
	song.BPM = 125;
	song.speed = 6;
	song.initialSpeed = 6;
	song.globalVolume = 64;
	song.songPos = 0;
	song.pattNum = 0;
	song.numChannels = channels;

	memset(song.name, 0, sizeof(song.name));
	if (name[0] != '\0')
	{
		strncpy(song.name, name, sizeof(song.name) - 1);
		song.name[sizeof(song.name) - 1] = '\0';
	}

	memset(song.orders, 0, sizeof(song.orders));
	song.orders[0] = 0;

	for (int32_t i = 0; i < MAX_PATTERNS; i++)
		patternNumRows[i] = 64;

	if (!ensureReservedInstruments())
	{
		unlockMixerCallback();
		snprintf(err, errSize, "failed to allocate reserved instruments");
		return false;
	}

	if (!allocatePattern(0))
	{
		unlockMixerCallback();
		snprintf(err, errSize, "failed to allocate pattern 0");
		return false;
	}

	patternNumRows[0] = 64;
	song.currNumRows = 64;

	resetChannels();
	setSongPos(0, 0, RESET_SONG_TICK);
	setMixerBPM(song.BPM);

	editor.songPos = 0;
	editor.editPattern = 0;
	editor.BPM = song.BPM;
	editor.speed = song.speed;
	editor.globalVolume = song.globalVolume;
	editor.tick = 1;

	unlockMixerCallback();
	setSongModifiedFlag();
	return true;
}

static bool tool_module_load(const char *js, const jsmntok_t *toks, int args_idx,
	char *err, size_t errSize)
{
	char path[PATH_MAX + 1];
	if (!args_get_string(js, toks, args_idx, "path", path, sizeof(path)))
	{
		snprintf(err, errSize, "missing required argument: path");
		return false;
	}

	if (!loadModuleFromPathHeadless(path))
	{
		snprintf(err, errSize, "failed to load module: %s", path);
		return false;
	}

	return true;
}

static bool tool_module_info(char *out, size_t outSize)
{
	snprintf(out, outSize,
		"{\"name\":\"%s\",\"channels\":%d,\"bpm\":%u,\"speed\":%u,"
		"\"global_volume\":%u,\"song_length\":%u,\"loop_start\":%u,"
		"\"current_pattern\":%u,\"pattern_rows\":%d}",
		song.name,
		(int)song.numChannels,
		(unsigned)song.BPM,
		(unsigned)song.speed,
		(unsigned)song.globalVolume,
		(unsigned)song.songLength,
		(unsigned)song.songLoopStart,
		(unsigned)song.pattNum,
		(int)patternNumRows[song.pattNum]);
	return true;
}

static note_t *cell_ptr(uint16_t pattNum, uint16_t row, uint16_t channel, char *err,
	size_t errSize)
{
	if (pattNum >= MAX_PATTERNS)
	{
		snprintf(err, errSize, "pattern %u out of range (max %d)", pattNum, MAX_PATTERNS - 1);
		return NULL;
	}
	if (row >= MAX_PATT_LEN)
	{
		snprintf(err, errSize, "row %u out of range (max %d)", row, MAX_PATT_LEN - 1);
		return NULL;
	}
	if (channel >= (uint16_t)song.numChannels || channel >= MAX_CHANNELS)
	{
		snprintf(err, errSize, "channel %u out of range (song has %d channels)",
			channel, (int)song.numChannels);
		return NULL;
	}

	if (pattern[pattNum] == NULL && !allocatePattern(pattNum))
	{
		snprintf(err, errSize, "failed to allocate pattern %u", pattNum);
		return NULL;
	}

	return &pattern[pattNum][(row * MAX_CHANNELS) + channel];
}

static bool tool_pattern_set_cell(const char *js, const jsmntok_t *toks, int args_idx,
	char *err, size_t errSize)
{
	int32_t pattern = 0, row = 0, channel = 0;
	bool found = false;

	if (!args_get_int(js, toks, args_idx, "pattern", &pattern, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: pattern");
		return false;
	}
	if (!args_get_int(js, toks, args_idx, "row", &row, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: row");
		return false;
	}
	if (!args_get_int(js, toks, args_idx, "channel", &channel, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: channel");
		return false;
	}

	note_t *cell = cell_ptr((uint16_t)pattern, (uint16_t)row, (uint16_t)channel, err, errSize);
	if (cell == NULL)
		return false;

	uint8_t note = cell->note;
	if (!args_get_note(js, toks, args_idx, "note", &note, &found, err, errSize))
		return false;
	if (found)
		cell->note = note;

	int32_t val = 0;
	if (args_get_int(js, toks, args_idx, "instrument", &val, &found) && found)
	{
		if (val < 0 || val > MAX_INST)
		{
			snprintf(err, errSize, "instrument must be 0..%d", MAX_INST);
			return false;
		}
		cell->instr = (uint8_t)val;
	}

	if (args_get_int(js, toks, args_idx, "volume", &val, &found) && found)
	{
		if (val < 0 || val > 255)
		{
			snprintf(err, errSize, "volume must be 0..255");
			return false;
		}
		cell->vol = (uint8_t)val;
	}

	if (args_get_int(js, toks, args_idx, "effect", &val, &found) && found)
	{
		if (val < 0 || val > 255)
		{
			snprintf(err, errSize, "effect must be 0..255");
			return false;
		}
		cell->efx = (uint8_t)val;
	}

	if (args_get_int(js, toks, args_idx, "effect_param", &val, &found) && found)
	{
		if (val < 0 || val > 255)
		{
			snprintf(err, errSize, "effect_param must be 0..255");
			return false;
		}
		cell->efxData = (uint8_t)val;
	}

	setSongModifiedFlag();
	return true;
}

static bool tool_pattern_get_cell(const char *js, const jsmntok_t *toks, int args_idx,
	char *out, size_t outSize, char *err, size_t errSize)
{
	int32_t pattNum = 0, row = 0, channel = 0;
	bool found = false;

	if (!args_get_int(js, toks, args_idx, "pattern", &pattNum, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: pattern");
		return false;
	}
	if (!args_get_int(js, toks, args_idx, "row", &row, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: row");
		return false;
	}
	if (!args_get_int(js, toks, args_idx, "channel", &channel, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: channel");
		return false;
	}

	if (pattNum < 0 || pattNum >= MAX_PATTERNS || row < 0 || row >= MAX_PATT_LEN ||
		channel < 0 || channel >= (int32_t)song.numChannels || channel >= MAX_CHANNELS)
	{
		snprintf(err, errSize, "pattern/row/channel out of range");
		return false;
	}

	note_t empty = {0};
	const note_t *cell = &empty;
	if (pattern[(uint16_t)pattNum] != NULL)
		cell = &pattern[(uint16_t)pattNum][((uint16_t)row * MAX_CHANNELS) + (uint16_t)channel];

	char noteStr[16];
	note_to_string(cell->note, noteStr, sizeof(noteStr));

	snprintf(out, outSize,
		"{\"pattern\":%d,\"row\":%d,\"channel\":%d,"
		"\"note\":%u,\"note_name\":\"%s\",\"instrument\":%u,"
		"\"volume\":%u,\"effect\":%u,\"effect_param\":%u}",
		pattNum, row, channel,
		(unsigned)cell->note, noteStr,
		(unsigned)cell->instr,
		(unsigned)cell->vol,
		(unsigned)cell->efx,
		(unsigned)cell->efxData);
	return true;
}

static bool tool_sample_load(const char *js, const jsmntok_t *toks, int args_idx,
	char *err, size_t errSize)
{
	char path[PATH_MAX + 1];
	if (!args_get_string(js, toks, args_idx, "path", path, sizeof(path)))
	{
		snprintf(err, errSize, "missing required argument: path");
		return false;
	}

	int32_t instrument = 0, sample = 0;
	bool found = false;

	if (!args_get_int(js, toks, args_idx, "instrument", &instrument, &found) || !found)
	{
		snprintf(err, errSize, "missing required argument: instrument");
		return false;
	}
	if (!args_get_int(js, toks, args_idx, "sample", &sample, &found))
	{
		snprintf(err, errSize, "invalid sample argument");
		return false;
	}
	if (!found)
		sample = 0;

	if (instrument < 1 || instrument > MAX_INST)
	{
		snprintf(err, errSize, "instrument must be 1..%d", MAX_INST);
		return false;
	}
	if (sample < 0 || sample >= MAX_SMP_PER_INST)
	{
		snprintf(err, errSize, "sample must be 0..%d", MAX_SMP_PER_INST - 1);
		return false;
	}

	if (!loadSampleHeadless(path, (uint8_t)instrument, (uint8_t)sample, false))
	{
		snprintf(err, errSize, "failed to load sample: %s", path);
		return false;
	}

	setSongModifiedFlag();
	return true;
}

static bool tool_module_save(const char *js, const jsmntok_t *toks, int args_idx,
	char *err, size_t errSize)
{
	char path[PATH_MAX + 1];
	if (!args_get_string(js, toks, args_idx, "path", path, sizeof(path)))
	{
		snprintf(err, errSize, "missing required argument: path");
		return false;
	}

	char format[8] = "xm";
	(void)args_get_string(js, toks, args_idx, "format", format, sizeof(format));

	int32_t saveMode = MOD_SAVE_MODE_XM;
	if (strcasecmp(format, "mod") == 0)
		saveMode = MOD_SAVE_MODE_MOD;
	else if (strcasecmp(format, "xm") != 0)
	{
		snprintf(err, errSize, "format must be \"xm\" or \"mod\"");
		return false;
	}

	if (!saveModuleHeadless(path, saveMode))
	{
		snprintf(err, errSize, "failed to save module: %s", path);
		return false;
	}

	return true;
}

static bool tool_module_render(const char *js, const jsmntok_t *toks, int args_idx,
	char *out, size_t outSize, char *err, size_t errSize)
{
	char path[PATH_MAX + 1];
	if (!args_get_string(js, toks, args_idx, "path", path, sizeof(path)))
	{
		snprintf(err, errSize, "missing required argument: path");
		return false;
	}

	int32_t rate = 44100, bits = 16, amp = 16, loops = 1, start = 0, stop = 255;
	bool found = false;

	(void)args_get_int(js, toks, args_idx, "rate", &rate, &found);
	(void)args_get_int(js, toks, args_idx, "bits", &bits, &found);
	(void)args_get_int(js, toks, args_idx, "amp", &amp, &found);
	(void)args_get_int(js, toks, args_idx, "loops", &loops, &found);
	(void)args_get_int(js, toks, args_idx, "start", &start, &found);
	(void)args_get_int(js, toks, args_idx, "stop", &stop, &found);

	if (bits != 16 && bits != 32)
	{
		snprintf(err, errSize, "bits must be 16 or 32");
		return false;
	}
	if (rate < MIN_WAV_RENDER_FREQ || rate > MAX_WAV_RENDER_FREQ)
	{
		snprintf(err, errSize, "rate must be %d..%d", MIN_WAV_RENDER_FREQ, MAX_WAV_RENDER_FREQ);
		return false;
	}
	if (amp < 1 || amp > 32)
	{
		snprintf(err, errSize, "amp must be 1..32");
		return false;
	}
	if (start < 0 || start > 255 || stop < 0 || stop > 255)
	{
		snprintf(err, errSize, "start/stop must be 0..255");
		return false;
	}
	if (loops < 0 || loops > 65535)
	{
		snprintf(err, errSize, "loops must be 0..65535");
		return false;
	}

	uint32_t totalSamples = 0;
	if (!renderModuleToWavFileHeadless(path, (uint32_t)rate, (uint8_t)bits, (int16_t)amp,
		(uint8_t)start, (uint8_t)stop, (uint16_t)loops, &totalSamples))
	{
		snprintf(err, errSize, "failed to render module to: %s", path);
		return false;
	}

	const double duration = (double)totalSamples / (double)rate;
	snprintf(out, outSize,
		"{\"path\":\"%s\",\"samples\":%u,\"duration_seconds\":%.3f,"
		"\"rate\":%d,\"bits\":%d}",
		path, totalSamples, duration, rate, bits);
	return true;
}

/* --- MCP protocol handlers ---------------------------------------------- */

static const char *TOOLS_LIST_JSON =
	"{\"tools\":["
	"{\"name\":\"module_new\",\"description\":\"Create a new empty module\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"channels\":{\"type\":\"integer\",\"description\":\"Even channel count 2..32\"},"
	"\"name\":{\"type\":\"string\",\"description\":\"Song name\"}},"
	"\"additionalProperties\":false}},"
	"{\"name\":\"module_load\",\"description\":\"Load a module from disk\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"path\":{\"type\":\"string\"}},\"required\":[\"path\"],\"additionalProperties\":false}},"
	"{\"name\":\"module_info\",\"description\":\"Return current module metadata\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{},\"additionalProperties\":false}},"
	"{\"name\":\"pattern_set_cell\",\"description\":\"Set one pattern cell\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"pattern\":{\"type\":\"integer\"},\"row\":{\"type\":\"integer\"},"
	"\"channel\":{\"type\":\"integer\"},\"note\":{\"type\":[\"integer\",\"string\"]},"
	"\"instrument\":{\"type\":\"integer\"},\"volume\":{\"type\":\"integer\"},"
	"\"effect\":{\"type\":\"integer\"},\"effect_param\":{\"type\":\"integer\"}},"
	"\"required\":[\"pattern\",\"row\",\"channel\"],\"additionalProperties\":false}},"
	"{\"name\":\"pattern_get_cell\",\"description\":\"Read one pattern cell\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"pattern\":{\"type\":\"integer\"},\"row\":{\"type\":\"integer\"},"
	"\"channel\":{\"type\":\"integer\"}},"
	"\"required\":[\"pattern\",\"row\",\"channel\"],\"additionalProperties\":false}},"
	"{\"name\":\"sample_load\",\"description\":\"Load a sample into an instrument\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"path\":{\"type\":\"string\"},\"instrument\":{\"type\":\"integer\"},"
	"\"sample\":{\"type\":\"integer\",\"description\":\"Sample slot 0..15\"}},"
	"\"required\":[\"path\",\"instrument\"],\"additionalProperties\":false}},"
	"{\"name\":\"module_save\",\"description\":\"Save the current module\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"path\":{\"type\":\"string\"},\"format\":{\"type\":\"string\",\"enum\":[\"xm\",\"mod\"]}},"
	"\"required\":[\"path\"],\"additionalProperties\":false}},"
	"{\"name\":\"module_render\",\"description\":\"Render the current module to WAV\","
	"\"inputSchema\":{\"type\":\"object\",\"properties\":{"
	"\"path\":{\"type\":\"string\"},\"rate\":{\"type\":\"integer\"},"
	"\"bits\":{\"type\":\"integer\"},\"amp\":{\"type\":\"integer\"},"
	"\"loops\":{\"type\":\"integer\"},\"start\":{\"type\":\"integer\"},"
	"\"stop\":{\"type\":\"integer\"}},"
	"\"required\":[\"path\"],\"additionalProperties\":false}}"
	"]}";

static void handle_initialize(const char *id_json)
{
	char result[512];
	snprintf(result, sizeof(result),
		"{\"protocolVersion\":\"%s\",\"capabilities\":{\"tools\":{}},"
		"\"serverInfo\":{\"name\":\"%s\",\"version\":\"%s\"}}",
		MCP_PROTOCOL_VERSION, MCP_SERVER_NAME, MCP_SERVER_VERSION);
	mcp_write_response(id_json, result);
}

static void handle_tools_list(const char *id_json)
{
	mcp_write_response(id_json, TOOLS_LIST_JSON);
}

static void handle_ping(const char *id_json)
{
	mcp_write_response(id_json, "{}");
}

static void handle_tools_call(const char *js, const jsmntok_t *toks, int root_idx,
	const char *id_json)
{
	const int params_idx = json_object_find(js, toks, root_idx, "params");
	if (params_idx < 0 || toks[params_idx].type != JSMN_OBJECT)
	{
		mcp_write_error(id_json, -32602, "Invalid params");
		return;
	}

	const int name_idx = json_object_find(js, toks, params_idx, "name");
	if (name_idx < 0 || toks[name_idx].type != JSMN_STRING)
	{
		mcp_write_error(id_json, -32602, "Missing tool name");
		return;
	}

	char toolName[64];
	if (!json_token_string(js, &toks[name_idx], toolName, sizeof(toolName)))
	{
		mcp_write_error(id_json, -32602, "Invalid tool name");
		return;
	}

	// function-scope fallback for a missing "arguments" object (must outlive the
	// tool calls below, which keep referencing js/toks)
	static const char empty_obj[] = "{}";
	jsmntok_t empty_tok[4];

	int args_idx = json_object_find(js, toks, params_idx, "arguments");
	if (args_idx < 0)
	{
		/* empty arguments object */
		jsmn_parser p;
		jsmn_init(&p);
		if (jsmn_parse(&p, empty_obj, strlen(empty_obj), empty_tok, 4) < 0)
		{
			mcp_write_error(id_json, -32603, "Internal error");
			return;
		}
		args_idx = 0;
		js = empty_obj;
		toks = empty_tok;
	}
	else if (toks[args_idx].type != JSMN_OBJECT)
	{
		mcp_write_error(id_json, -32602, "Invalid arguments");
		return;
	}

	char err[MCP_RESULT_BUF];
	char out[MCP_RESULT_BUF];
	err[0] = '\0';
	out[0] = '\0';

	bool ok = false;

	if (strcmp(toolName, "module_new") == 0)
	{
		ok = tool_module_new(js, toks, args_idx, err, sizeof(err));
		if (ok)
			snprintf(out, sizeof(out), "created new module (%d channels)", (int)song.numChannels);
	}
	else if (strcmp(toolName, "module_load") == 0)
	{
		ok = tool_module_load(js, toks, args_idx, err, sizeof(err));
		if (ok)
			snprintf(out, sizeof(out), "loaded module");
	}
	else if (strcmp(toolName, "module_info") == 0)
	{
		ok = tool_module_info(out, sizeof(out));
		if (!ok)
			snprintf(err, sizeof(err), "failed to read module info");
	}
	else if (strcmp(toolName, "pattern_set_cell") == 0)
	{
		ok = tool_pattern_set_cell(js, toks, args_idx, err, sizeof(err));
		if (ok)
			snprintf(out, sizeof(out), "pattern cell updated");
	}
	else if (strcmp(toolName, "pattern_get_cell") == 0)
	{
		ok = tool_pattern_get_cell(js, toks, args_idx, out, sizeof(out), err, sizeof(err));
	}
	else if (strcmp(toolName, "sample_load") == 0)
	{
		ok = tool_sample_load(js, toks, args_idx, err, sizeof(err));
		if (ok)
			snprintf(out, sizeof(out), "sample loaded");
	}
	else if (strcmp(toolName, "module_save") == 0)
	{
		ok = tool_module_save(js, toks, args_idx, err, sizeof(err));
		if (ok)
			snprintf(out, sizeof(out), "module saved");
	}
	else if (strcmp(toolName, "module_render") == 0)
	{
		ok = tool_module_render(js, toks, args_idx, out, sizeof(out), err, sizeof(err));
	}
	else
	{
		snprintf(err, sizeof(err), "unknown tool: %s", toolName);
		mcp_write_tool_result(id_json, err, true);
		return;
	}

	if (!ok)
	{
		if (err[0] == '\0')
			snprintf(err, sizeof(err), "tool failed");
		mcp_write_tool_result(id_json, err, true);
		return;
	}

	mcp_write_tool_result(id_json, out, false);
}

static void handle_message(const char *line)
{
	jsmn_parser parser;
	jsmntok_t tokens[MCP_MAX_TOKENS];

	jsmn_init(&parser);
	const int tok_count = jsmn_parse(&parser, line, strlen(line), tokens, MCP_MAX_TOKENS);
	if (tok_count < 0)
	{
		fprintf(stderr, "mcp: JSON parse error on input line\n");
		return;
	}

	if (tok_count < 1 || tokens[0].type != JSMN_OBJECT)
	{
		fprintf(stderr, "mcp: expected JSON object\n");
		return;
	}

	const int method_idx = json_object_find(line, tokens, 0, "method");
	if (method_idx < 0 || tokens[method_idx].type != JSMN_STRING)
	{
		fprintf(stderr, "mcp: missing method\n");
		return;
	}

	char method[64];
	if (!json_token_string(line, &tokens[method_idx], method, sizeof(method)))
		return;

	const bool is_notification = !json_has_key(line, tokens, 0, "id");

	char id_buf[128];
	const char *id_json = "null";
	if (!is_notification)
	{
		const int id_idx = json_object_find(line, tokens, 0, "id");
		if (id_idx >= 0)
		{
			const jsmntok_t *id_tok = &tokens[id_idx];
			const int id_len = id_tok->end - id_tok->start;
			if (id_len > 0 && (size_t)id_len < sizeof(id_buf))
			{
				memcpy(id_buf, line + id_tok->start, (size_t)id_len);
				id_buf[id_len] = '\0';
				id_json = id_buf;
			}
		}
	}

	if (strcmp(method, "notifications/initialized") == 0)
		return;

	if (strcmp(method, "initialize") == 0)
	{
		if (!is_notification)
			handle_initialize(id_json);
		return;
	}

	if (strcmp(method, "tools/list") == 0)
	{
		if (!is_notification)
			handle_tools_list(id_json);
		return;
	}

	if (strcmp(method, "ping") == 0)
	{
		if (!is_notification)
			handle_ping(id_json);
		return;
	}

	if (strcmp(method, "tools/call") == 0)
	{
		if (!is_notification)
			handle_tools_call(line, tokens, 0, id_json);
		return;
	}

	if (!is_notification)
		mcp_write_error(id_json, -32601, "Method not found");
}

int handle_mcp_mode(int argc, char **argv)
{
	(void)argc;
	(void)argv;

	char savedCwd[PATH_MAX + 1];
	const bool haveCwd = (mcp_getcwd(savedCwd, sizeof(savedCwd)) != NULL);

	char errBuf[256];
	if (!ft2_headlessEngineInit(errBuf, sizeof(errBuf)))
	{
		fprintf(stderr, "mcp: engine init failed: %s\n", errBuf);
		return 1;
	}

	if (haveCwd)
		(void)mcp_chdir(savedCwd);

	fprintf(stderr, "mcp: ft2-clone MCP server ready (stdio JSON-RPC)\n");

	char *line = (char *)malloc(MCP_MAX_LINE);
	if (line == NULL)
	{
		fprintf(stderr, "mcp: out of memory\n");
		return 1;
	}

	while (fgets(line, MCP_MAX_LINE, stdin) != NULL)
	{
		size_t len = strlen(line);
		while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r'))
			line[--len] = '\0';

		if (len == 0)
			continue;

		handle_message(line);
	}

	free(line);
	return 0;
}