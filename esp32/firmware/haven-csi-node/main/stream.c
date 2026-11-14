/**
 * Sender task: drains the CSI queue outside the Wi-Fi task.
 *
 * UDP: one datagram per frame to target_ip:target_port. On ENOMEM (lwIP/Wi-Fi buffers exhausted) the
 * sender backs off exponentially instead of hammering sendto (failure mode documented in RuView).
 *
 * Serial (optional, for networks that block device-to-laptop traffic): each frame is printed as one
 * line "CSIB:<base64 of the exact UDP payload>" at the console baud rate (921600). Status packets
 * use the same prefix. Log lines are interleaved and ignored by the host.
 */
#include "stream.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "esp_log.h"
#include "esp_timer.h"
#include "lwip/sockets.h"
#include "mbedtls/base64.h"
#include "csi.h"
#include "motion.h"
#include "node_config.h"

static const char *TAG = "stream";

static int s_sock = -1;
static struct sockaddr_in s_dest;
static int64_t s_backoff_until;
static uint32_t s_backoff_ms;
static stream_stats_t s_stats;
static uint8_t s_mac[6];
static int8_t s_last_rssi;

static void udp_open(void)
{
    if (!(g_cfg.stream & STREAM_UDP) || !g_cfg.target_ip[0]) return;
    memset(&s_dest, 0, sizeof(s_dest));
    s_dest.sin_family = AF_INET;
    s_dest.sin_port = htons(g_cfg.target_port);
    if (inet_pton(AF_INET, g_cfg.target_ip, &s_dest.sin_addr) != 1) {
        ESP_LOGE(TAG, "target_ip '%s' is not an IPv4 address", g_cfg.target_ip);
        return;
    }
    s_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s_sock < 0) {
        ESP_LOGE(TAG, "socket() failed: errno %d", errno);
        return;
    }
    ESP_LOGI(TAG, "UDP -> %s:%u", g_cfg.target_ip, g_cfg.target_port);
}

static void udp_send(const uint8_t *d, size_t n)
{
    if (s_sock < 0) return;
    int64_t now = esp_timer_get_time();
    if (now < s_backoff_until) {
        s_stats.udp_failed++;
        return;
    }
    if (sendto(s_sock, d, n, 0, (struct sockaddr *)&s_dest, sizeof(s_dest)) >= 0) {
        s_stats.udp_sent++;
        s_backoff_ms = 0;
        return;
    }
    s_stats.udp_failed++;
    if (errno == ENOMEM) {
        s_backoff_ms = s_backoff_ms ? (s_backoff_ms * 2 > 2000 ? 2000 : s_backoff_ms * 2) : 50;
        s_backoff_until = now + (int64_t)s_backoff_ms * 1000;
        if (s_backoff_ms >= 400) ESP_LOGW(TAG, "sendto ENOMEM, backing off %lu ms", (unsigned long)s_backoff_ms);
    }
}

static void serial_send(const uint8_t *d, size_t n)
{
    static unsigned char line[5 + ((CSI_FRAME_MAX + 2) / 3) * 4 + 2];
    size_t olen = 0;
    memcpy(line, "CSIB:", 5);
    if (mbedtls_base64_encode(line + 5, sizeof(line) - 7, &olen, d, n) != 0) return;
    line[5 + olen] = '\n';
    fwrite(line, 1, 5 + olen + 1, stdout);  /* one write per line keeps it whole */
    s_stats.serial_sent++;
}

static void emit(const uint8_t *d, size_t n)
{
    if (g_cfg.stream & STREAM_UDP) udp_send(d, n);
    if (g_cfg.stream & STREAM_SERIAL) serial_send(d, n);
}

static void send_status(void)
{
    vitals_pkt_t p = {0};
    float energy, floor;
    bool moving, recent;
    motion_get(&energy, &floor, &moving, &recent);
    p.magic = VITALS_MAGIC;
    p.node_id = g_cfg.node_id;
    p.flags = (recent ? 0x01 : 0) | (moving ? 0x04 : 0);
    p.rssi = s_last_rssi;
    p.mac01[0] = s_mac[0];
    p.mac01[1] = s_mac[1];
    memcpy(p.mac25, &s_mac[2], 4);
    p.motion_energy = energy;
    p.presence_score = floor > 0.0f ? energy / floor : 0.0f;
    p.uptime_ms = (uint32_t)(esp_timer_get_time() / 1000);
    emit((const uint8_t *)&p, sizeof(p));
}

static void stream_task(void *arg)
{
    (void)arg;
    static csi_item_t item;
    int64_t next_status = esp_timer_get_time() + 1000000;
    for (;;) {
        if (xQueueReceive(g_csi_queue, &item, pdMS_TO_TICKS(100)) == pdTRUE) {
            if (item.src == SRC_AP) {
                motion_add((const int8_t *)&item.data[CSI_HEADER_SIZE], item.len - CSI_HEADER_SIZE - 6);
                s_last_rssi = item.rssi;
            }
            emit(item.data, item.len);
        }
        int64_t now = esp_timer_get_time();
        if (now >= next_status) {
            next_status = now + 1000000;
            send_status();
        }
    }
}

void stream_start(const uint8_t own_mac[6])
{
    memcpy(s_mac, own_mac, 6);
    udp_open();
    xTaskCreatePinnedToCore(stream_task, "stream", 4096, NULL, 5, NULL, 1);
}

void stream_get_stats(stream_stats_t *out)
{
    memcpy(out, &s_stats, sizeof(*out));
}
