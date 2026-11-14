#include "node_config.h"

#include <string.h>
#include "esp_log.h"
#include "nvs.h"

static const char *TAG = "config";

node_config_t g_cfg;

static void get_str(nvs_handle_t h, const char *key, char *out, size_t cap)
{
    size_t len = cap;
    if (nvs_get_str(h, key, out, &len) != ESP_OK) {
        out[0] = '\0';
    }
}

void node_config_load(void)
{
    memset(&g_cfg, 0, sizeof(g_cfg));
    g_cfg.target_port = CONFIG_HAVEN_TARGET_PORT;
    g_cfg.node_id = 1;
    g_cfg.ping_hz = CONFIG_HAVEN_PING_HZ;
    g_cfg.link_hz = CONFIG_HAVEN_LINK_HZ;
    g_cfg.stream = STREAM_UDP;

    nvs_handle_t h;
    if (nvs_open("csi_cfg", NVS_READONLY, &h) != ESP_OK) {
        ESP_LOGW(TAG, "no settings in NVS: run tools/haven_fw.py provision");
        return;
    }
    get_str(h, "ssid", g_cfg.ssid, sizeof(g_cfg.ssid));
    get_str(h, "password", g_cfg.password, sizeof(g_cfg.password));
    get_str(h, "target_ip", g_cfg.target_ip, sizeof(g_cfg.target_ip));
    uint8_t u8;
    uint16_t u16;
    if (nvs_get_u16(h, "target_port", &u16) == ESP_OK && u16) g_cfg.target_port = u16;
    if (nvs_get_u8(h, "node_id", &u8) == ESP_OK) g_cfg.node_id = u8;
    if (nvs_get_u8(h, "ping_hz", &u8) == ESP_OK && u8 >= 5 && u8 <= 100) g_cfg.ping_hz = u8;
    if (nvs_get_u8(h, "link_hz", &u8) == ESP_OK && u8 >= 5 && u8 <= 100) g_cfg.link_hz = u8;
    if (nvs_get_u8(h, "stream", &u8) == ESP_OK && (u8 & (STREAM_UDP | STREAM_SERIAL))) g_cfg.stream = u8;
    if (nvs_get_u8(h, "tx_qdbm", &u8) == ESP_OK && u8 >= 8 && u8 <= 84) g_cfg.tx_qdbm = u8;
    if (nvs_get_u8(h, "accept_all", &u8) == ESP_OK) g_cfg.accept_all = u8 != 0;

    uint8_t blob[CONFIG_HAVEN_MAX_PEERS * 6];
    size_t len = sizeof(blob);
    if (nvs_get_blob(h, "link_macs", blob, &len) == ESP_OK) {
        g_cfg.n_peers = (uint8_t)(len / 6);
        memcpy(g_cfg.peers, blob, g_cfg.n_peers * 6);
    } else {
        /* RuView's single-MAC filter, if present, becomes a one-entry allow-list */
        len = 6;
        if (nvs_get_blob(h, "filter_mac", blob, &len) == ESP_OK && len == 6) {
            g_cfg.n_peers = 1;
            memcpy(g_cfg.peers[0], blob, 6);
        }
    }
    nvs_close(h);
}
