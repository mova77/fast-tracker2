#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "ft2_unicode.h"

void saveMusic(UNICHAR *filenameU);
bool saveXM(UNICHAR *filenameU);

// headless synchronous module save (no GUI thread). saveMode: 0=MOD, 1=XM.
bool saveModuleHeadless(UNICHAR *filenameU, int32_t saveMode);
