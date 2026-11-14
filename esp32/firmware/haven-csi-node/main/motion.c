#include "motion.h"

#include <math.h>
#include <string.h>
#include "esp_timer.h"

#define WIN 50   /* ~1 s at 50 frames/s */
#define NSC 51   /* LLTF subcarriers 2..26 and -26..-1 (index 1 can be invalid on ESP32) */

static float s_amp[WIN][NSC];
static int s_n, s_i;
static float s_floor = -1.0f;
static int64_t s_last_motion_us = -60000000LL;

static int sc_index(int k)  /* k-th used subcarrier -> position in the 64-entry LLTF block */
{
    return k < 25 ? k + 2 : k - 25 + 38;
}

void motion_add(const int8_t *csi, uint16_t len)
{
    if (len < 128) return;
    float sum = 0.0f, *row = s_amp[s_i];
    for (int k = 0; k < NSC; k++) {
        int p = sc_index(k);
        float im = csi[2 * p], re = csi[2 * p + 1];
        row[k] = sqrtf(im * im + re * re);
        sum += row[k];
    }
    if (sum <= 0.0f) return;
    float scale = NSC / sum;  /* automatic gain changes per packet: keep only the shape */
    for (int k = 0; k < NSC; k++) row[k] *= scale;
    s_i = (s_i + 1) % WIN;
    if (s_n < WIN) s_n++;
}

void motion_get(float *energy, float *floor, bool *moving, bool *recent)
{
    float e = 0.0f;
    if (s_n >= 10) {
        for (int k = 0; k < NSC; k++) {
            float m = 0.0f, v = 0.0f;
            for (int j = 0; j < s_n; j++) m += s_amp[j][k];
            m /= s_n;
            for (int j = 0; j < s_n; j++) v += (s_amp[j][k] - m) * (s_amp[j][k] - m);
            e += sqrtf(v / s_n) / (m + 1e-3f);
        }
        e /= NSC;
        /* floor follows quiet periods quickly and drifts up slowly (~1%/s) otherwise */
        if (s_floor < 0.0f || e < s_floor) s_floor = e;
        else s_floor += (e - s_floor) * 0.01f;
    }
    int64_t now = esp_timer_get_time();
    bool mv = s_floor > 0.0f && e > 2.0f * s_floor + 0.02f;
    if (mv) s_last_motion_us = now;
    *energy = e;
    *floor = s_floor < 0.0f ? 0.0f : s_floor;
    *moving = mv;
    *recent = now - s_last_motion_us < 30000000LL;
}
