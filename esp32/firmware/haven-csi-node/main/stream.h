/** Sends queued CSI frames to the host over UDP and/or the USB serial port, plus a 1 Hz status packet. */
#pragma once

#include <stdint.h>

typedef struct {
    uint32_t udp_sent, udp_failed, serial_sent;
} stream_stats_t;

/** Start the sender task (after csi_init()). own_mac goes into the status packet. */
void stream_start(const uint8_t own_mac[6]);

void stream_get_stats(stream_stats_t *out);
