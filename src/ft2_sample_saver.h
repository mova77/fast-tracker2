#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "ft2_unicode.h"

enum
{
	SAVE_NORMAL = 0,
	SAVE_RANGE = 1
};

void saveSample(UNICHAR *filenameU, bool saveAsRange);

// headless synchronous sample save (no GUI thread; mirrors saveSampleThread)
bool saveSampleHeadless(UNICHAR *filenameU, uint8_t instrNr, uint8_t smpNr, int32_t saveMode);
