#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "ft2_mix.h" // MIXER_FRAC_BITS

#define SINC_KERNELS 3
#define SINC8_TAPS 8
#define SINC16_TAPS 16

// 8192 phases has a decent trade-off between low aliasing and cache usage
#define INTRP_PHASES 8192

// log2(INTRP_PHASES)
#define INTRP_PHASES_BITS 13

// log2(SINC8_TAPS)
#define SINC8_TAPS_BITS 3

// log2(SINC16_TAPS)
#define SINC16_TAPS_BITS 4

#define SINC8_FRACSHIFT (MIXER_FRAC_BITS-(INTRP_PHASES_BITS+SINC8_TAPS_BITS))
#define SINC8_FRACMASK ((SINC8_TAPS*INTRP_PHASES)-SINC8_TAPS)
#define SINC16_FRACSHIFT (MIXER_FRAC_BITS-(INTRP_PHASES_BITS+SINC16_TAPS_BITS))
#define SINC16_FRACMASK ((SINC16_TAPS*INTRP_PHASES)-SINC16_TAPS)

extern float *fSinc[SINC_KERNELS], *fSinc8[SINC_KERNELS], *fSinc16[SINC_KERNELS];
extern uint64_t sincRatio1, sincRatio2;

bool setupWindowedSincTables(void);
void freeWindowedSincTables(void);
