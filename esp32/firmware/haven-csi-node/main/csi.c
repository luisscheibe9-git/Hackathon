/**
 * CSI capture for classic ESP32.
 *
 * Which frames produce a "link":
 *   - frames sent by the access point we joined (the router answering our ~50 Hz gateway pings, and
 *     its traffic to the other boards)  -> link "R>me"
 *   - frames sent by another Haven board (its pings to the router, overheard in promiscuous mode)
 *                                       -> link "<peer>>me"
 * Everything else (neighbours, phones) is dropped in the callback before any copying, so the CSI
 * budget is not spent on traffic that has no fixed position in the room.
 *
 * Each transmitter gets its own token bucket (link_hz), so a busy router cannot crowd out the
 * board-to-board links, and a total bucket caps the work done in the Wi-Fi task.
 *
 * Design follows RuView esp32-csi-node (MIT) and wifi-sensing-kit (MIT); written for the ESP32's
 * legacy CSI configuration and rx_ctrl layout.
 */
#include "csi.h"

#include <string.h>
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "node_config.h"

static const char *TAG = "csi";

QueueHandle_t g_csi_queue;

static uint8_t s_ap[6];
static volatile bool s_ap_set;
static csi_stats_t s_stats;
static uint32_t s_seq;
static csi_item_t s_item;  /* built in the Wi-Fi task (single caller), copied into the queue */

typedef struct {
    float tokens;
    int64_t last_us;
} bucket_t;

static bucket_t s_link[SRC_SLOTS];
static bucket_t s_total;
static float s_link_rate, s_total_rate;

#define QUEUE_DEPTH 24

static bool take(bucket_t *b, float rate, float burst, int64_t now)
{
    b->tokens += (float)(now - b->last_us) * rate * 1e-6f;
    if (b->tokens > burst) b->tokens = burst;
    b->last_us = now;
    if (b->tokens < 1.0f) return false;
    b->tokens -= 1.0f;
    return true;
}

static int source_slot(const uint8_t *mac)
{
    if (s_ap_set && memcmp(mac, s_ap, 6) == 0) return SRC_AP;
    for (int i = 0; i < g_cfg.n_peers; i++) {
        if (memcmp(mac, g_cfg.peers[i], 6) == 0) return i + 1;
    }
    return g_cfg.accept_all ? SRC_OTHER : -1;
}

static uint32_t channel_mhz(unsigned ch)
{
    if (ch >= 1 && ch <= 13) return 2407 + 5 * ch;
    if (ch == 14) return 2484;
    return 0;
}

static void csi_cb(void *ctx, wifi_csi_info_t *info)
{
    (void)ctx;
    if (info == NULL || info->buf == NULL || info->len == 0) return;
    s_stats.callbacks++;

    int src = source_slot(info->mac);
    if (src < 0) {
        s_stats.foreign++;
        return;
    }
    int64_t now = esp_timer_get_time();
    if (!take(&s_link[src], s_link_rate, 3.0f, now) || !take(&s_total, s_total_rate, 10.0f, now)) {
        s_stats.rate_limited++;
        return;
    }

    const wifi_pkt_rx_ctrl_t *rx = &info->rx_ctrl;
    uint16_t len = info->len > CSI_MAX_LEN ? CSI_MAX_LEN : info->len;
    uint8_t *b = s_item.data;
    uint32_t magic = CSI_MAGIC, freq = channel_mhz(rx->channel), seq = s_seq++;
    uint16_t n_sc = len / 2;
    memcpy(&b[0], &magic, 4);
    b[4] = g_cfg.node_id;
    b[5] = 1;
    memcpy(&b[6], &n_sc, 2);
    memcpy(&b[8], &freq, 4);
    memcpy(&b[12], &seq, 4);
    b[16] = (uint8_t)(int8_t)rx->rssi;
    b[17] = (uint8_t)(int8_t)rx->noise_floor;
    b[18] = 0;
    uint8_t flags = CSI_FLAG_TX_MAC;
    if (rx->cwb) flags |= CSI_FLAG_BW40;
    if (rx->stbc) flags |= CSI_FLAG_STBC;
    if (src == SRC_AP) flags |= CSI_FLAG_FROM_AP;
    if (info->first_word_invalid) flags |= CSI_FLAG_FIRST_WORD_BAD;
    b[19] = flags;
    memcpy(&b[CSI_HEADER_SIZE], info->buf, len);
    memcpy(&b[CSI_HEADER_SIZE + len], info->mac, 6);
    s_item.len = CSI_HEADER_SIZE + len + 6;
    s_item.src = (uint8_t)src;
    s_item.rssi = (int8_t)rx->rssi;

    if (xQueueSend(g_csi_queue, &s_item, 0) == pdTRUE) {
        s_stats.kept[src]++;
    } else {
        s_stats.queue_full++;
    }
}

static void promisc_cb(void *buf, wifi_promiscuous_pkt_type_t type)
{
    /* Nothing to do: promiscuous mode only widens which frames reach the CSI callback. */
    (void)buf;
    (void)type;
}

void csi_init(void)
{
    g_csi_queue = xQueueCreate(QUEUE_DEPTH, sizeof(csi_item_t));
    configASSERT(g_csi_queue);
    s_link_rate = (float)g_cfg.link_hz;
    s_total_rate = (float)CONFIG_HAVEN_TOTAL_HZ;
}

void csi_set_ap(const uint8_t bssid[6])
{
    s_ap_set = false;
    memcpy(s_ap, bssid, 6);
    s_ap_set = true;
}

void csi_start(void)
{
    /* Peers are only heard in promiscuous mode (their frames are addressed to the router, not us).
     * With no peers, the router's replies to our own pings are enough and the radio does less work. */
    bool promisc = g_cfg.n_peers > 0 || g_cfg.accept_all;
    if (promisc) {
        wifi_promiscuous_filter_t filt = {
            .filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT | WIFI_PROMIS_FILTER_MASK_DATA,
        };
        ESP_ERROR_CHECK(esp_wifi_set_promiscuous_rx_cb(promisc_cb));
        ESP_ERROR_CHECK(esp_wifi_set_promiscuous_filter(&filt));
        ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));
    }

    wifi_csi_config_t cfg = {
        .lltf_en = true,
        .htltf_en = true,
        .stbc_htltf2_en = true,
        .ltf_merge_en = true,
        .channel_filter_en = false,  /* keep neighbouring subcarriers independent */
        .manu_scale = false,
        .shift = 0,
        .dump_ack_en = false,
    };
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_cb, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
    ESP_LOGI(TAG, "CSI on: %s, %u peer(s), <= %u frames/s per transmitter, <= %d total",
             promisc ? "promiscuous MGMT+DATA" : "own traffic only", g_cfg.n_peers, g_cfg.link_hz,
             CONFIG_HAVEN_TOTAL_HZ);
}

void csi_get_stats(csi_stats_t *out)
{
    memcpy(out, &s_stats, sizeof(*out));
}
