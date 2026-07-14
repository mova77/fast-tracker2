// Headless MOD/module -> WAV renderer.
//
// Drives the real FastTracker II replayer + mixer without the GUI/video layer,
// then reuses the actual WAV-render loop in ft2_wav_renderer.c. The engine is
// initialized once (lazily) and reused across renders (important for the REST
// server, which may render many modules in one process).

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#define render_getcwd _getcwd
#define render_chdir  _chdir
#else
#include <unistd.h>
#define render_getcwd getcwd
#define render_chdir  chdir
#endif

#include "ft2_header.h"
#include "ft2_audio.h"
#include "ft2_config.h"
#include "ft2_diskop.h"
#include "ft2_hpc.h"
#include "ft2_module_loader.h"
#include "ft2_replayer.h"
#include "ft2_unicode.h"
#include "ft2_structs.h"
#include "ft2_wav_renderer.h"
#include "ft2_audioselector.h"
#include "mixer/ft2_windowed_sinc.h"

#include "ft2_renderer.h"

// implemented in ft2_main.c (exposed for headless use)
extern void initializeVars(void);

static bool engineInitialized = false;

bool ft2_headlessEngineInit(char *errBuf, size_t errBufSize)
{
	if (engineInitialized)
		return true;

	// audio subsystem only; no video/window is created in headless mode
	if (SDL_Init(SDL_INIT_AUDIO) != 0)
	{
		snprintf(errBuf, errBufSize, "SDL audio init failed: %s", SDL_GetError());
		return false;
	}

	hpc_Init();
	initializeVars();

	// the module loader writes the module path here; normally allocated by
	// setupGUI(), which we skip in headless mode
	editor.tmpFilenameU      = (UNICHAR *)malloc((PATH_MAX + 1) * sizeof (UNICHAR));
	editor.tmpInstrFilenameU = (UNICHAR *)malloc((PATH_MAX + 1) * sizeof (UNICHAR));
	if (editor.tmpFilenameU == NULL || editor.tmpInstrFilenameU == NULL)
	{
		snprintf(errBuf, errBufSize, "Out of memory");
		return false;
	}
	editor.tmpFilenameU[0] = 0;
	editor.tmpInstrFilenameU[0] = 0;

	if (!setupExecutablePath() || !setupWindowedSincTables())
	{
		snprintf(errBuf, errBufSize, "Failed to set up executable path / sinc tables");
		return false;
	}

	loadConfigOrSetDefaults();

	audio.currOutputDevice = getAudioOutputDeviceFromConfig();
	audio.currInputDevice  = getAudioInputDeviceFromConfig();

	// open the audio device: this also allocates the mixer buffers and tables
	// used by mixReplayerTickToBuffer(). The device stays paused during render.
	if (!setupAudio(CONFIG_HIDE_ERRORS))
	{
		setToDefaultAudioOutputDevice();
		if (!setupAudio(CONFIG_HIDE_ERRORS))
		{
			config.audioFreq = 44100;
			config.specialFlags &= ~(BITDEPTH_32 + BUFFSIZE_512 + BUFFSIZE_2048);
			config.specialFlags |=  (BITDEPTH_16 + BUFFSIZE_1024);
			if (!setupAudio(CONFIG_HIDE_ERRORS))
			{
				snprintf(errBuf, errBufSize, "Failed to initialize audio mixer");
				return false;
			}
		}
	}

	if (!setupReplayer())
	{
		snprintf(errBuf, errBufSize, "Failed to set up replayer");
		return false;
	}

	pauseAudio(); // keep the device silent; we render straight to file

	engineInitialized = true;
	return true;
}

render_result_t render_mod_to_wav(
	const char *input_file,
	const char *output_file,
	render_config_t config_in)
{
	render_result_t result = {0};

	// --- validate arguments ---
	if (!input_file || !output_file)
	{
		snprintf(result.error_message, sizeof(result.error_message),
			"Input or output file path is NULL");
		return result;
	}

	if (config_in.bit_depth != 16 && config_in.bit_depth != 32)
	{
		snprintf(result.error_message, sizeof(result.error_message),
			"Bit depth must be 16 or 32, got %d", config_in.bit_depth);
		return result;
	}

	if (config_in.sample_rate < 8000 || config_in.sample_rate > 384000)
	{
		snprintf(result.error_message, sizeof(result.error_message),
			"Sample rate must be between 8000-384000 Hz, got %u",
			config_in.sample_rate);
		return result;
	}

	if (config_in.amplification < 1 || config_in.amplification > 32)
	{
		snprintf(result.error_message, sizeof(result.error_message),
			"Amplification must be between 1-32, got %d",
			config_in.amplification);
		return result;
	}

	// remember the caller's working directory: engine init (config loading)
	// chdir's to the config folder, which would break relative input/output paths
	char savedCwd[PATH_MAX + 1];
	const bool haveCwd = (render_getcwd(savedCwd, sizeof(savedCwd)) != NULL);

	// --- initialize the engine (once) ---
	if (!ft2_headlessEngineInit(result.error_message, sizeof(result.error_message)))
		return result;

	if (haveCwd)
		(void)render_chdir(savedCwd); // restore the caller's working directory

	// --- load the module ---
	if (!loadModuleFromPathHeadless(input_file))
	{
		snprintf(result.error_message, sizeof(result.error_message),
			"Failed to load module: %s", input_file);
		return result;
	}

	// --- render to WAV ---
	uint32_t totalSamples = 0; // interleaved stereo sample count
	bool ok = renderModuleToWavFileHeadless(
		output_file,
		config_in.sample_rate,
		config_in.bit_depth,
		config_in.amplification,
		config_in.start_pos,
		config_in.stop_pos,
		config_in.max_loops,
		&totalSamples);

	if (!ok)
	{
		snprintf(result.error_message, sizeof(result.error_message),
			"Rendering failed (could not write output or file exceeded 2GB): %s",
			output_file);
		return result;
	}

	const uint32_t frames = totalSamples / 2; // stereo -> per-channel frames
	result.total_samples = totalSamples;
	result.duration_ms = (config_in.sample_rate > 0)
		? (uint32_t)(((uint64_t)frames * 1000) / config_in.sample_rate)
		: 0;
	result.success = true;
	return result;
}

const char *render_error_to_string(const render_result_t *result)
{
	if (!result)
		return "Invalid result pointer";

	if (result->success)
		return "Rendering successful";

	return result->error_message;
}
