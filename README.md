# Hackathon: Wi-Fi fall detection

Camera-free fall detection for elder care. Three ESP32 boards measure how a person disturbs Wi-Fi signals (CSI) in a room; a laptop detects falls and shows when and in which zone they happened.

## Repo layout

- [research/](research/) — viability, technical approach, sources, open questions. Start with [research/README.md](research/README.md).
- [NOTES.md](NOTES.md) — current state and next steps (for teammates and AI agents).

- [firmware/csi_link_check/](firmware/csi_link_check/) streams the first 128 CSI bytes (the legacy training field) from the associated access point. Upload as **ESP32 Dev Module** using Arduino IDE. It accepts the 2.4 GHz SSID and password as two newline-terminated serial lines at 460800 baud.
- [tools/Measure-CsiMotion.ps1](tools/Measure-CsiMotion.ps1) runs the first motion experiment in PowerShell 7. Close any serial monitor, then run `./tools/Measure-CsiMotion.ps1 -Port COM4 -Network attinternet` from the repo folder. It uses the saved Windows network profile or prompts for the password, generates Wi-Fi traffic, and records three rounds of empty room, walking and standing still. Use `-Verify -Trials 1 -Seconds 6` for a short capture check. Raw CSI CSVs go into `data/` by default.
- [tools/Start-CsiVisualizer.ps1](tools/Start-CsiVisualizer.ps1) opens the live chart. With Python 3 and pyserial 3.5 installed, run `./tools/Start-CsiVisualizer.ps1` for COM4 and COM5. Use `-Ports COM4` for one board or `-Python` to select an installed Python executable. Close the chart before running the capture tool to free the serial ports.

Planned: `detection/` (Python pipeline), `dashboard/` (web UI).

## Live Observatory

Use **Calibrate empty room**, leave during the seven-second countdown, and wait for twelve seconds of quiet readings. The viewer then compares each receiver with its own baseline and reports motion. Stationary presence and fall detection still need validation.

Add `-Observatory` to the Windows visualizer launcher to open the browser view. It serves the dashboard on localhost and plots CSI change along the router-to-receiver paths. The layout is schematic. Use the terminal to stop the local capture service. On macOS with Python 3 and pyserial installed, the same viewer can be started with `python3 tools/csi-visualizer.py <ssid> /dev/cu.<device> --observatory`. It reads the Wi-Fi password from stdin and expects the serial format emitted by this repo's Arduino sketch. Espressif's `CSI_DATA` example uses a different serial format.

The 3D floor reuses the MIT-licensed [RuView Observatory floor renderer](https://github.com/ruvnet/RuView/blob/3bae24a1231e0d9809e84eb35edba7231b8d1913/ui/observatory/js/presence-cartography.js) and Three.js 0.160.0. Both licenses are included under `tools/observatory/vendor/`.

Offline replay of a saved CSV (no boards needed): `python detection/replay.py` opens the Observatory with `?replay=1`. See `detection/README.md`.

## Three ESP32s without a router

Upload `firmware/csi_transmitter/csi_transmitter.ino` to the third board as **ESP32 Dev Module**. It creates the `Stillpoint-CSI` test network on channel 6 and sends packets when a receiver joins. Power the transmitter via USB. Keep the two receivers connected to the PC over USB and running `csi_link_check.ino`. Restart the viewer with `./tools/Start-CsiVisualizer.ps1 -Standalone` (add the applicable `-Ports` and `-Python` options). The PC can stay on its current network. On macOS, add `--external-traffic` to the viewer command, use SSID `Stillpoint-CSI`, and pass the demo password `stillpoint-demo` over stdin.

The receivers send UDP probes over the private ESP32 network and the transmitter replies to each receiver directly. The [classic ESP32 human sensing project](https://github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing) demonstrates a similar probe-and-echo setup and is a reference for approximate position after calibration.

### One USB cable to the laptop

Flash the current transmitter/gateway sketch to the board that stays connected to the laptop. Flash the current receiver sketch to both other boards, then power them from individual USB chargers or power banks. After a short wait for optional serial configuration, each receiver joins the gateway's private network and relays CSI readings to it over Wi-Fi. The gateway forwards both streams to the laptop over its single USB serial port.

On Windows, launch with `./tools/Start-CsiVisualizer.ps1 -GatewayPort COM6` using the gateway's actual COM number. The Observatory labels each receiver by the last six digits of its Wi-Fi MAC address. Keep antennas attached to all boards.
