# Haven sensing: ESP32-WROOM-32U firmware + webcam-taught model

Haven's sensing stack for our **classic ESP32 (ESP32-WROOM-32U) dev boards with external U.FL antennas**.
It recreates what [RuView](https://github.com/ruvnet/RuView) and
[wifi-sensing-kit](https://github.com/andrisgauracs/wifi-sensing-kit) do on ESP32-S3 boards:

- **Firmware** (`firmware/haven-csi-node/`, ESP-IDF): joins the 2.4 GHz network, pings the router ~50×/s,
  captures CSI from the router **and from the other Haven boards** (board-to-board links), and streams it
  to the laptop over UDP (or USB serial).
- **Host** (`host/server.py`): receives the CSI, learns activities with the **webcam as the teacher**, and
  runs a WiFi-only fall / long-lie detector with a live page and a JSON API for the caregiver dashboard.

It is new code, not a fork: RuView does not support the original ESP32, and its firmware is ~12k lines of
S3/C6-specific features. The **UDP packets are byte-compatible** with RuView + the kit's patch, so S3 boards
running that firmware can join the same host.

```
 router ─────▶ node 1 ◀──── node 2        every node: CSI of frames from the router + the other nodes
   │  ╲          ▲  ╲        ▲             links: R>1, R>2, R>3, 2>1, 3>1, 1>2, ...
   │   ╲         │   ╲       │
   └────▶ node 3 ─────────────┘
            │ UDP 5005 (or USB serial)
            ▼
   laptop: host/server.py ── /train.html   webcam (MediaPipe Pose, in-browser) labels → WiFi features
                         └── /  and /api/live   WiFi-only activity + fall state machine
```

## What differs from the ESP32-S3 originals

| | RuView / wifi-sensing-kit (ESP32-S3) | Haven node (classic ESP32, WROOM-32U) |
|---|---|---|
| Target | `esp32s3`, 8 MB flash | `esp32`, fits 2 MB+ (WROOM-32U has 4 MB) |
| Antenna | PCB | external U.FL: **attach it before powering**, or range is a few cm |
| CSI config | S3 / C6 structs | ESP32 legacy `wifi_csi_config_t`; subcarrier 1 flagged when the hardware marks the first word invalid |
| Link filter | compile-time MAC list (`kit_config.h`, rebuild after finding the router) | router BSSID learned at connect; peer MACs in NVS, so no rebuild |
| Rate limiting | one 50 Hz gate shared by all senders | token bucket **per transmitter** (default 50/s) + total cap, so the router can't crowd out board-to-board links |
| Router tag | host config `router_bssid` | firmware flags router frames (byte 19 bit 5) |
| Status packet | breathing / heart rate / presence (S3 DSP) | coarse motion + presence only; breathing and heart rate are **not** computed (sent as 0) |
| Credentials | in the firmware build (kit) / NVS (RuView) | NVS only; firmware binaries contain no Wi-Fi password |
| LED | WS2812 colour per board | GPIO 2 blue LED blinks the node id |
| Transport | UDP | UDP, or serial lines `CSIB:<base64>` at 921600 baud when the network blocks device-to-laptop traffic |

## Setup (once)

Uses the existing tools venv and ESP-IDF 5.5.6 on this Mac.

```bash
cd ~/Documents/Hackathon/esp32
```

```bash
/Users/anthonyouzounian/esp32-tools/venv/bin/python host/install.py
```

```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml`: Wi-Fi name (2.4 GHz), room number, detection timing. Put the Wi-Fi password alone in
`~/.haven-wifi-pass` and `chmod 600` it. Below, `PY` means `/Users/anthonyouzounian/esp32-tools/venv/bin/python`.

## Flash the boards

1. **Attach the antennas.** Plug all three boards in with USB **data** cables.
2. `PY tools/haven_fw.py discover` lists each board's MAC. Paste the `boards:` list into `config.yaml`
   and give each a location name.
3. `PY tools/haven_fw.py build` compiles the firmware (about a minute the first time).
4. `PY tools/haven_fw.py flash` flashes every configured board, writes its Wi-Fi/node settings, resets it
   and reports, for example: `node 1 joined "attinternet" ch 6 RSSI -48 dBm, ip 192.168.1.71, router …, CSI yield 92/s (router 46, peers 46)`.
5. Later changes: `flash --app-only` after a rebuild (keeps settings); `provision` after editing
   `config.yaml` (no reflash); `check` to re-read each board's status; `monitor --reset` for the full log.

The blue LED: fast blink = connecting, blinks the node id = streaming, slow blink = connected but no CSI,
double blink = not provisioned.

**Placement:** spread the boards around the room at about chest height, antennas vertical, nothing metal
in between, and **don't move them after training** (the model is tied to the room and positions).
If the laptop's IP changes, run `provision` again (it is the UDP target).

## Train with the webcam

```bash
/Users/anthonyouzounian/esp32-tools/venv/bin/python host/server.py
```

Open <http://127.0.0.1:8940/train.html>:

1. **Start camera**, frame head to feet with floor visible, **Calibrate standing**.
2. **Record training (3 rounds)**: spoken prompts walk you through *leave the room, stand, walk, sit, lie on
   the mat, fall onto the mat ×2* (about 8 minutes). The camera labels each half-second; a label is kept
   only if it fits the prompt (e.g. "walking" while asked to sit is discarded).
3. **Record test (1 round)**: a separate session; its score is the honest number.
4. Cover the camera and watch "WiFi only" follow you.
5. `PY host/evaluate.py` prints test accuracy, confusion, each link alone, and a motion-only baseline,
   and writes `data/model_metrics.json`.

Falls: only onto a thick mat, knees first, protect the head. Skip the fall steps if anyone is unsure.
The detector also catches a fast *active → lying* transition, so lying down quickly on the mat during
training will (correctly) trigger the alert path.

## Live detection

<http://127.0.0.1:8940/> shows the room state from WiFi alone (no camera): empty / person moving /
lying / **possible fall** / **FALL ALERT** with an on-the-floor timer and an acknowledge button.

`GET http://127.0.0.1:8940/api/live` (CORS open) returns what the caregiver dashboard needs:

```json
{"mode": "LIVE", "room": "Room 104", "state": "alert", "activity": "lying", "confidence": 0.86,
 "on_floor_s": 14.5, "fall_time": 1794695391.4, "acknowledged": false, "long_lie_s": 10, "events": [...]}
```

`mode` is `LIVE` only while real CSI frames arrive (otherwise `NO_SIGNAL`), so the dashboard can badge it honestly.

State machine: a possible fall is a *fall* prediction or an *active → lying* change faster than
`drop_seconds`; it becomes an alert after `long_lie_seconds` on the floor. While someone is on the floor,
"empty" predictions are read as "lying" (a person can't leave without getting up). Standing or walking for
`recover_seconds` ends the episode.

## Files

| Path | What |
|---|---|
| `firmware/haven-csi-node/main/protocol.h` | wire format (CSI frame + 32-byte status packet) |
| `firmware/haven-csi-node/main/csi.c` | CSI callback, allow-list, per-transmitter rate limit, serialization |
| `firmware/haven-csi-node/main/stream.c` | UDP / serial sender task, ENOMEM back-off, 1 Hz status packet |
| `firmware/haven-csi-node/main/main.c` | boot, Wi-Fi, gateway ping, status log (`yield=`) |
| `firmware/haven-csi-node/main/node_config.c` | NVS settings (`csi_cfg` namespace, RuView-compatible key names) |
| `tools/haven_fw.py` | discover / build / flash / provision / check / monitor |
| `host/server.py` | receiver, features, dataset, kNN model, fall state machine, web + API |
| `host/web/train.html` | webcam teacher (MediaPipe Pose in the browser) |
| `host/web/index.html` | live, camera-free room view |
| `host/evaluate.py` | offline honest evaluation |

`data/` (recordings, metrics), `config.yaml`, `host/web/vendor/` and firmware `build/` are git-ignored.

## Status

- Firmware **builds** with ESP-IDF v5.5.6 for `esp32` (app 0xBA640 bytes, 51% of the partition free).
  It has **not yet run on a board**: no ESP32 was connected while it was written. First flash: check the
  `CSI yield` reported by `flash` / `check`.
- Host pipeline tested end to end with synthetic packets in the Haven format (parsing, link naming, MAC
  learning from status packets, recording, training, test scoring, fall state machine, both pages).
  Synthetic accuracy means nothing; real accuracy comes only from `evaluate.py` on recorded sessions.
- The webcam posture/fall rules have not yet been tuned on real footage. Watch the "Camera" label while
  standing, walking, sitting, lying and doing a test fall before recording.

## Credits

- [RuView](https://github.com/ruvnet/RuView) `esp32-csi-node` (MIT): ADR-018 frame and vitals packet
  layout, gateway-ping traffic source, ENOMEM back-off, NVS key names. No code copied verbatim.
- [wifi-sensing-kit](https://github.com/andrisgauracs/wifi-sensing-kit) (MIT): transmitter-MAC extension,
  board-to-board links, per-link features (mean shape, spread, frame-to-frame change), kNN model,
  camera-as-teacher method and honest test-session scoring.
- [Espressif esp-csi](https://github.com/espressif/esp-csi) and ESP-IDF (Apache-2.0): CSI API and router-ping example.
- Google [MediaPipe](https://developers.google.com/mediapipe) Tasks Vision 0.10.14 + Pose Landmarker (Apache-2.0),
  downloaded by `host/install.py`.
- Written with Claude Code (Anthropic) during the hackathon.

Prototype. Not a medical device.
