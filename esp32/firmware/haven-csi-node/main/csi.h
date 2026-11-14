/** Haven CSI node: CSI capture, transmitter allow-list, per-link rate limit, frame serialization. */
#pragma once

#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "protocol.h"

/* Transmitter slots: 0 = the access point we joined, 1..n = peer boards, last = anyone else
 * (only used when accept_all is set). */
#define SRC_AP 0
#define SRC_OTHER (CONFIG_HAVEN_MAX_PEERS + 1)
#define SRC_SLOTS (CONFIG_HAVEN_MAX_PEERS + 2)

typedef struct {
    uint16_t len;     /* bytes used in data */
    uint8_t src;      /* SRC_AP, 1..n (peer index + 1) or SRC_OTHER */
    int8_t rssi;
    uint8_t data[CSI_FRAME_MAX];
} csi_item_t;

typedef struct {
    uint32_t callbacks;          /* every CSI callback from the driver */
    uint32_t foreign;            /* dropped: transmitter not in the allow-list */
    uint32_t rate_limited;       /* dropped: link or total rate limit */
    uint32_t queue_full;         /* dropped: sender task fell behind */
    uint32_t kept[SRC_SLOTS];    /* queued for sending, per transmitter slot */
} csi_stats_t;

/** Queue of csi_item_t consumed by the stream task. Valid after csi_init(). */
extern QueueHandle_t g_csi_queue;

void csi_init(void);

/** Record the access point's BSSID (call on every (re)connect). */
void csi_set_ap(const uint8_t bssid[6]);

/** Turn on promiscuous capture (only when peers are configured) and the CSI callback. */
void csi_start(void);

void csi_get_stats(csi_stats_t *out);
