/** Coarse on-board motion score from the router link, sent in the 1 Hz vitals/status packet.
 *  Host-side models do the real classification; this is a health check and a fallback signal. */
#pragma once

#include <stdbool.h>
#include <stdint.h>

/** Add one router-link CSI frame (raw ESP-IDF CSI bytes, LLTF first). */
void motion_add(const int8_t *csi, uint16_t len);

/** Motion energy over the last ~1 s (mean per-subcarrier coefficient of variation), its adaptive
 *  still-room floor, and whether motion was seen now / in the last 30 s. */
void motion_get(float *energy, float *floor, bool *moving, bool *recent);
