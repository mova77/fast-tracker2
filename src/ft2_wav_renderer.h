#pragma once

#include <stdint.h>
#include "ft2_header.h"

#define MIN_WAV_RENDER_FREQ 8000
#define MAX_WAV_RENDER_FREQ 384000

void cbToggleWavRenderIndividualTracks(void);
void setWavRenderFrequency(int32_t freq);
void setWavRenderBitDepth(uint8_t bitDepth);
void updateWavRendererSettings(void);
void drawWavRenderer(void);
void showWavRenderer(void);
void hideWavRenderer(void);
void exitWavRenderer(void);
void pbWavRender(void);
void pbWavExit(void);
void pbWavFreqUp(void);
void pbWavFreqDown(void);
void pbWavAmpUp(void);
void pbWavAmpDown(void);
void pbWavSongStartUp(void);
void pbWavSongStartDown(void);
void pbWavSongEndUp(void);
void pbWavSongEndDown(void);
void resetWavRenderer(void);
void rbWavRenderBitDepth16(void);
void rbWavRenderBitDepth32(void);

// headless song-to-WAV render (no GUI). Engine must be initialized and a module loaded.
// maxLoops: infinite-loop safety net (0 = disabled). See render_config_t.max_loops.
bool renderModuleToWavFileHeadless(const char *outputPath, uint32_t freq,
	uint8_t bitDepth, int16_t amp, uint8_t startPos, uint8_t stopPos,
	uint16_t maxLoops, uint32_t *outTotalSamples);
