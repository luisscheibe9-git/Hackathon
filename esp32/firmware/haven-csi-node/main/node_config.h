/** Haven CSI node: per-board settings stored in NVS namespace "csi_cfg" (written by haven_fw.py provision).
 *  Key names match RuView's provision.py where the meaning is the same (ssid, password, target_ip,
 *  target_port, node_id), so a RuView-provisioned NVS also boots this firmware. */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "sdkconfig.h"

#define STREAM_UDP 0x01
#define STREAM_SERIAL 0x02

typedef struct {
    char ssid[33];
    char password[65];
    char target_ip[16];      /* host computer; empty = no UDP */
    uint16_t target_port;
    uint8_t node_id;
    uint8_t ping_hz;         /* gateway ping rate */
    uint8_t link_hz;         /* max frames/s kept per transmitter */
    uint8_t stream;          /* STREAM_UDP | STREAM_SERIAL */
    uint8_t tx_qdbm;         /* max TX power in 0.25 dBm (8..84), 0 = driver default */
    bool accept_all;         /* debug: keep frames from every transmitter, not only AP + peers */
    uint8_t n_peers;
    uint8_t peers[CONFIG_HAVEN_MAX_PEERS][6];  /* other Haven boards' station MACs */
} node_config_t;

extern node_config_t g_cfg;

/** Load g_cfg from NVS (defaults where a key is missing). Call after nvs_flash_init(). */
void node_config_load(void);
