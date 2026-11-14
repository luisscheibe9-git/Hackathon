# ESP32 CSI setup on this Mac

> **New:** Haven's own firmware for the ESP32-WROOM-32U boards (RuView / wifi-sensing-kit compatible,
> board-to-board links) and the webcam-taught training host are in [HAVEN_SENSING.md](HAVEN_SENSING.md).
> The notes below cover the earlier Espressif `csi_recv_router` test.

This reproduces the router-to-ESP32 capture and three-round motion experiment
described in the supplied roommate history. It is **not an exact copy** of the
roommate's Arduino firmware or Stillpoint viewer: those files were not present
on either GitHub branch when checked on November 14, 2026. This capture tool
reads the official Espressif 25-column `CSI_DATA` format instead.

## Hardware and tools verified

- Chip identified over USB: ESP32-D0WD-V3, revision 3.1; target `esp32`.
- USB bridge: Silicon Labs CP2102, VID:PID `10C4:EA60`.
- Initially detected port: `/dev/cu.usbserial-0001`.
- ESP-IDF: v5.5.6, `/Users/anthonyouzounian/esp/esp-idf`.
- Arduino ESP32 core: 3.3.12 (available, not used by this firmware).
- Espressif source: `/Users/anthonyouzounian/esp32-tools/esp-csi`.
- Existing binaries found for `csi_recv_router`, `csi_send`, and `csi_recv`
  under that source's `examples/get-started/` directories. Finding those
  artifacts does not independently verify the sender/receiver behavior.

The existing router configuration names `attinternet-2.4G`. A local copy at
`.local/csi_recv_router` changes the SSID to the user-confirmed `attinternet`
and retains the previously configured password without displaying it.
This isolated router build passed with ESP-IDF v5.5.6 for `esp32`.
Credentials and firmware build outputs stay under Git-ignored `.local/`.
Do not share or commit that directory; firmware binaries can contain credentials.

## Capture and motion test

Once compatible firmware is connected to Wi-Fi, a short capture is:

```sh
/Users/anthonyouzounian/esp32-tools/venv/bin/python /Users/anthonyouzounian/Documents/Hackathon/esp32/tools/csi_capture.py --seconds 20
```

Double-click **Start Motion Test.command** for the experiment. Keep the board
and router stationary and spread them across the room. The script prompts for
empty room, walking across the link, and standing still, three times each.
Each trial has a six-second preparation delay and a 20-second recording.
CSV rows and JSON summaries are saved to Git-ignored `data/`.

The default serial rate is **921600 baud**, matching the existing Espressif
build. The script automatically selects a single CP2102, or accepts `--port`.
Close other serial monitors first. It reports failure when no valid CSI rows
arrive; a serial port alone is not evidence of sensing.

The change score compares RMS-normalized LLTF amplitudes between nearby frames
of the same packet format and channel. DC/guard tones and potentially invalid
first samples are excluded. It is a motion experiment, not a calibrated fall
detector or a reliable stationary-person detector. Its scores are not directly
comparable to the roommate's numbers because the original algorithm is absent.

## USB connection blocker

After initial chip identification, the CP2102 disappeared. A subsequent macOS
USB inventory showed no attached USB devices, even after the user reseated/reset
the board. Try a known-good USB data cable and adapter or a direct connection.
A power LED can illuminate even when the data connection is unavailable.

No firmware has been overwritten in this session. The attempted backup could
not run because the port was absent. Live CSI has not been verified. Once USB
returns, back up the original flash, confirm the replacement firmware, flash
the prepared build, and verify the Wi-Fi IP plus actual CSI rows.

Reference: [Espressif router CSI example](https://github.com/espressif/esp-csi/tree/master/examples/get-started/csi_recv_router).
