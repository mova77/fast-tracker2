#pragma once

#include <stdint.h>
#include <stdbool.h>

typedef struct {
	uint32_t sample_rate;      /* 44100, 48000, etc */
	uint8_t  bit_depth;         /* 16 or 32 */
	int16_t  amplification;     /* 1-32 */
	uint8_t  start_pos;         /* Song position 0-255 */
	uint8_t  stop_pos;          /* Song position 0-255 */
	uint16_t max_loops;         /* infinite-loop safety net: bail after this many
	                               redundant replays of already-visited song state.
	                               The song's own end/loop logic always wins first;
	                               this only triggers on truly endless modules.
	                               1 = default, 0 = disabled (render until 2GB cap) */
} render_config_t;

typedef struct {
	bool success;
	uint32_t total_samples;
	uint32_t duration_ms;
	char error_message[256];
} render_result_t;

/* Main rendering function - synchronous */
render_result_t render_mod_to_wav(
	const char *input_file,
	const char *output_file,
	render_config_t config
);

/* Get human-readable error message */
const char *render_error_to_string(const render_result_t *result);
