/**
 * Haven CSI node: Wi-Fi CSI sensing firmware for classic ESP32 boards (ESP32-WROOM-32U, external antenna).
 *
 * Boot: load settings from NVS -> join the 2.4 GHz network -> ping the gateway ~50x/s (guaranteed traffic
 * to measure, which the other boards also overhear) -> stream CSI from the router and from the other
 * Haven boards to the host computer.
 *
 * The wire format matches RuView esp32-csi-node + the wifi-sensing-kit transmitter-MAC extension; see
 * protocol.h. Settings are written by esp32/tools/haven_fw.py provision; the firmware image itself
 * holds no Wi-Fi credentials.
 */
#include <stdio.h>
#include <string.h>
#include "esp_app_desc.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "lwip/ip_addr.h"
#include "nvs_flash.h"
#include "ping/ping_sock.h"

#include "csi.h"
#include "led.h"
#include "node_config.h"
#include "stream.h"

static const char *TAG = "haven";

#define GOT_IP_BIT BIT0
static EventGroupHandle_t s_events;
static esp_netif_t *s_netif;
static esp_ping_handle_t s_ping;
static int s_retries;
static esp_timer_handle_t s_reconnect;

static void reconnect_cb(void *arg)
{
    (void)arg;
    esp_wifi_connect();
}

#define MACSTR_FMT "%02x:%02x:%02x:%02x:%02x:%02x"
#define MAC_ARGS(m) (m)[0], (m)[1], (m)[2], (m)[3], (m)[4], (m)[5]

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t *d = data;
        xEventGroupClearBits(s_events, GOT_IP_BIT);
        led_set(LED_CONNECTING);
        s_retries++;
        if (s_retries <= 3 || s_retries % 20 == 0) {
            ESP_LOGW(TAG, "Wi-Fi disconnected (reason %d), retry %d. Check SSID/password and that the "
                          "network is 2.4 GHz.", d->reason, s_retries);
        }
        /* don't block the event loop: retry from a one-shot timer */
        esp_timer_stop(s_reconnect);
        esp_timer_start_once(s_reconnect, (s_retries < 5 ? 500 : 3000) * 1000LL);
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        s_retries = 0;
        xEventGroupSetBits(s_events, GOT_IP_BIT);
    }
}

static void wifi_start(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    const esp_timer_create_args_t t = {.callback = reconnect_cb, .name = "reconnect"};
    ESP_ERROR_CHECK(esp_timer_create(&t, &s_reconnect));
    s_netif = esp_netif_create_default_wifi_sta();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_event, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_event, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));

    wifi_config_t wc = {0};
    strlcpy((char *)wc.sta.ssid, g_cfg.ssid, sizeof(wc.sta.ssid));
    strlcpy((char *)wc.sta.password, g_cfg.password, sizeof(wc.sta.password));
    wc.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
    wc.sta.sort_method = WIFI_CONNECT_AP_BY_SIGNAL;
    wc.sta.threshold.authmode = g_cfg.password[0] ? WIFI_AUTH_WPA_PSK : WIFI_AUTH_OPEN;
    wc.sta.pmf_cfg.capable = true;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wc));
    ESP_ERROR_CHECK(esp_wifi_start());
    /* Modem sleep would skip frames between beacons; CSI needs the radio awake. */
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    if (g_cfg.tx_qdbm) {
        esp_err_t e = esp_wifi_set_max_tx_power((int8_t)g_cfg.tx_qdbm);
        ESP_LOGI(TAG, "max TX power %.2f dBm: %s", g_cfg.tx_qdbm / 4.0, esp_err_to_name(e));
    }
}

static void noop_ping_cb(esp_ping_handle_t h, void *a)
{
    (void)h;
    (void)a;
}

static void ping_gateway(const esp_netif_ip_info_t *ip)
{
    if (s_ping) return;
    ip_addr_t target = {0};
    target.type = IPADDR_TYPE_V4;
    target.u_addr.ip4.addr = ip->gw.addr;
    esp_ping_config_t cfg = ESP_PING_DEFAULT_CONFIG();
    cfg.target_addr = target;
    cfg.count = ESP_PING_COUNT_INFINITE;
    cfg.interval_ms = 1000 / g_cfg.ping_hz;
    cfg.data_size = 1;
    cfg.timeout_ms = 1000;
    cfg.task_stack_size = 3072;
    esp_ping_callbacks_t cbs = {.on_ping_success = noop_ping_cb, .on_ping_timeout = noop_ping_cb, .on_ping_end = noop_ping_cb};
    if (esp_ping_new_session(&cfg, &cbs, &s_ping) == ESP_OK) {
        esp_ping_start(s_ping);
        ESP_LOGI(TAG, "pinging gateway " IPSTR " at %u Hz (traffic for CSI)", IP2STR(&ip->gw), g_cfg.ping_hz);
    } else {
        ESP_LOGW(TAG, "could not start gateway ping; CSI will depend on other traffic");
        s_ping = NULL;
    }
}

static void announce_connection(void)
{
    wifi_ap_record_t ap;
    esp_netif_ip_info_t ip;
    if (esp_wifi_sta_get_ap_info(&ap) != ESP_OK || esp_netif_get_ip_info(s_netif, &ip) != ESP_OK) return;
    csi_set_ap(ap.bssid);
    /* One parseable line for tools/haven_fw.py (router BSSID, channel, IP) */
    ESP_LOGI(TAG, "HAVEN_JOINED ssid=\"%s\" channel=%d rssi=%d router_bssid=" MACSTR_FMT " ip=" IPSTR " gw=" IPSTR,
             (const char *)ap.ssid, ap.primary, ap.rssi, MAC_ARGS(ap.bssid), IP2STR(&ip.ip), IP2STR(&ip.gw));
    ping_gateway(&ip);
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    node_config_load();
    led_init(g_cfg.node_id);

    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    const char *mode = g_cfg.stream == (STREAM_UDP | STREAM_SERIAL) ? "udp+serial"
                       : g_cfg.stream == STREAM_SERIAL               ? "serial"
                                                                     : "udp";
    ESP_LOGI(TAG, "Haven CSI node %s | node %u | mac " MACSTR_FMT " | ssid \"%s\" | host %s:%u | stream %s | peers %u",
             esp_app_get_description()->version, g_cfg.node_id, MAC_ARGS(mac), g_cfg.ssid,
             g_cfg.target_ip[0] ? g_cfg.target_ip : "-", g_cfg.target_port, mode, g_cfg.n_peers);
    for (int i = 0; i < g_cfg.n_peers; i++) {
        ESP_LOGI(TAG, "  peer %d: " MACSTR_FMT, i + 1, MAC_ARGS(g_cfg.peers[i]));
    }

    if (!g_cfg.ssid[0]) {
        led_set(LED_NO_CONFIG);
        for (;;) {
            ESP_LOGW(TAG, "not provisioned: run  python tools/haven_fw.py provision  (board MAC " MACSTR_FMT ")", MAC_ARGS(mac));
            vTaskDelay(pdMS_TO_TICKS(10000));
        }
    }

    s_events = xEventGroupCreate();
    csi_init();
    led_set(LED_CONNECTING);
    wifi_start();
    xEventGroupWaitBits(s_events, GOT_IP_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
    announce_connection();
    stream_start(mac);
    csi_start();
    led_set(LED_STREAMING);

    /* Every 5 s: one status line ("yield=" = CSI frames/s kept), LED state, reconnect bookkeeping. */
    csi_stats_t a, b;
    stream_stats_t sa, sb;
    csi_get_stats(&a);
    stream_get_stats(&sa);
    bool connected = true;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        bool now_connected = xEventGroupGetBits(s_events) & GOT_IP_BIT;
        if (now_connected && !connected) announce_connection();
        connected = now_connected;
        csi_get_stats(&b);
        stream_get_stats(&sb);
        uint32_t kept = 0, peers = 0;
        for (int i = 0; i < SRC_SLOTS; i++) kept += b.kept[i] - a.kept[i];
        for (int i = 1; i <= CONFIG_HAVEN_MAX_PEERS; i++) peers += b.kept[i] - a.kept[i];
        ESP_LOGI(TAG, "yield=%.1f/s (router %.1f, peers %.1f) | heard %.0f/s, foreign %.0f/s, rate-limited %.0f/s, "
                      "queue-full %lu | udp %.1f/s fail %lu | serial %.1f/s | heap %lu",
                 kept / 5.0, (b.kept[SRC_AP] - a.kept[SRC_AP]) / 5.0, peers / 5.0,
                 (b.callbacks - a.callbacks) / 5.0, (b.foreign - a.foreign) / 5.0,
                 (b.rate_limited - a.rate_limited) / 5.0, (unsigned long)(b.queue_full - a.queue_full),
                 (sb.udp_sent - sa.udp_sent) / 5.0, (unsigned long)(sb.udp_failed - sa.udp_failed),
                 (sb.serial_sent - sa.serial_sent) / 5.0, (unsigned long)esp_get_free_heap_size());
        if (connected) led_set(kept ? LED_STREAMING : LED_NO_CSI);
        a = b;
        sa = sb;
    }
}
