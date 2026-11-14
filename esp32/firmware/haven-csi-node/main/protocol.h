/**
 * Haven CSI node: UDP wire format.
 *
 * Byte-compatible with RuView esp32-csi-node (ADR-018 CSI frame, 32-byte vitals packet) and with the
 * wifi-sensing-kit extension that appends the transmitter MAC, so the same host software can read
 * frames from ESP32-S3 boards running RuView and from these classic-ESP32 boards.
 *
 * CSI frame (magic 0xC5110001), little endian:
 *   [0..3]   magic
 *   [4]      node id
 *   [5]      antennas (always 1)
 *   [6..7]   subcarrier count = csi_len / 2
 *   [8..11]  channel centre frequency, MHz
 *   [12..15] sequence number (per node, counts frames sent)
 *   [16]     RSSI, dBm (int8)
 *   [17]     noise floor, dBm (int8)
 *   [18]     PPDU type: 0 = non-HT / HT
 *   [19]     flags, see CSI_FLAG_*
 *   [20..]   raw CSI bytes from ESP-IDF: int8 pairs (imaginary, real), LLTF first (64 subcarriers,
 *            order 0..31 then -32..-1), then HT-LTF / STBC-HT-LTF when the packet had them
 *   [last 6] transmitter MAC, present when CSI_FLAG_TX_MAC is set (wifi-sensing-kit extension)
 *
 * Vitals / status packet (magic 0xC5110002), 32 bytes, sent once per second:
 *   [4] node id  [5] flags (bit0 presence, bit1 fall (never set here), bit2 motion)
 *   [6..7] breathing x100 (0: not computed)  [8..11] heart rate x10000 (0: not computed)
 *   [12] RSSI  [13] persons (0: not computed)  [14..15] own MAC bytes 0-1 (Haven extension)
 *   [16..19] motion energy (float)  [20..23] presence score (float)  [24..27] uptime ms
 *   [28..31] own MAC bytes 2-5 (Haven extension; RuView sends zeros here)
 */
#pragma once

#include <stdint.h>

#define CSI_MAGIC 0xC5110001u
#define VITALS_MAGIC 0xC5110002u
#define CSI_HEADER_SIZE 20

/* byte 19 flags */
#define CSI_FLAG_BW40 0x01            /* RuView: 40 MHz packet */
#define CSI_FLAG_STBC 0x04            /* RuView: STBC packet */
#define CSI_FLAG_FROM_AP 0x20         /* Haven: transmitter is the access point this node joined */
#define CSI_FLAG_FIRST_WORD_BAD 0x40  /* Haven: ESP32 hardware marked the first 4 CSI bytes invalid */
#define CSI_FLAG_TX_MAC 0x80          /* wifi-sensing-kit: 6-byte transmitter MAC after the CSI bytes */

/* Classic ESP32, 20 MHz: LLTF 128 + HT-LTF 128 + STBC-HT-LTF 128 bytes. 40 MHz packets can carry up to
 * 128 + 256 + 256. Anything longer is truncated. */
#define CSI_MAX_LEN 640
#define CSI_FRAME_MAX (CSI_HEADER_SIZE + CSI_MAX_LEN + 6)

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint8_t node_id;
    uint8_t flags;
    uint16_t breathing_x100;
    uint32_t heart_x10000;
    int8_t rssi;
    uint8_t n_persons;
    uint8_t mac01[2];
    float motion_energy;
    float presence_score;
    uint32_t uptime_ms;
    uint8_t mac25[4];
} vitals_pkt_t;

_Static_assert(sizeof(vitals_pkt_t) == 32, "vitals packet must be 32 bytes");
