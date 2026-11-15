# Haven: Wi-Fi fall detection for senior living

Camera-free fall detection for elder care. A small plug-in ESP32 sensor in each room measures how a person disturbs the building's Wi-Fi signal (CSI). A model taught by a webcam during training only, then running on Wi-Fi alone, spots a fall and the stillness after, and alerts staff with the room, the time and the minutes without movement.

**Live website: https://haven-public-ten.vercel.app**

## Where everything is

Everything we built at the hackathon is in this repository, with its full commit history.

| What | Where |
|---|---|
| Website (live site above) | [`website`](https://github.com/luisscheibe9-git/Hackathon/tree/website) branch, site files in `safer/public/`. Deployed by Vercel from [Aouzzo/Haven](https://github.com/Aouzzo/Haven); the `website` branch mirrors it. |
| Live demo: gateway, demo screen, phone alerts, calibration | `main`: [`esp32/`](esp32/) |
| ESP32 firmware and webcam-taught host | `main`: [`esp32/`](esp32/), [`firmware/`](firmware/) (first built on the [`esp32-wroom-firmware`](https://github.com/luisscheibe9-git/Hackathon/tree/esp32-wroom-firmware) branch) |
| Detection models and test results | [`claude/detector-compare-54380c`](https://github.com/luisscheibe9-git/Hackathon/tree/claude/detector-compare-54380c) branch, `detection/` |
| Live CSI capture and replay tools | [`stillpoint-live-csi`](https://github.com/luisscheibe9-git/Hackathon/tree/stillpoint-live-csi) branch |
| Sensor enclosure: Blender model and exploded view | [`exploded-view`](https://github.com/luisscheibe9-git/Hackathon/tree/exploded-view) branch, `hardware/esp32-case/` |
| Research: market, competitors, approach, sources, rules | [`research/`](research/), and the [`research`](https://github.com/luisscheibe9-git/Hackathon/tree/research) branch |
| Team notes and decisions | [NOTES.md](NOTES.md) |

## AI tools we used

- **OpenAI Codex**: research on Wi-Fi sensing and the market, and a coding agent in this repository (see [AGENTS.md](AGENTS.md)).
- **Claude Code**: ESP32 firmware, detection-model comparison, the website and its 3D scene.
- **Google MediaPipe Pose** (open source, Apache-2.0): image recognition during training only, to label the Wi-Fi data.

Prototype. Not a medical device.
