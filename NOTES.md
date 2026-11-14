# NOTES

## Goal
Hackathon project: 3x ESP32 Wi-Fi CSI sensing to detect falls of elderly residents and report when and in which room zone they happened. No cameras, no wearables.

## Team / repo
- Repo: https://github.com/luisscheibe9-git/Hackathon (private). Collaborators with write access: Aouzzo, jbj4poly-dotcom.
- Default branch `main`. Research added on branch `research`.

## Current state (2026-11-13)
- Research done: see `research/` (viability verdict, approach, sources, open questions).
- [Wi-Fi sensing demo](research/wifi-sensing.md) records reported ESP32-S3 results and reproduction steps.
- [Fall detection survey](research/fall-detection-survey.md) compares ESP32 Wi-Fi sensing and radar. Recommended prototype: height-capable radar for position and posture if available, ESP32 CSI for independent motion evidence, and a held-out test with fall-like daily activities.
- [HumanRadar video research](research/HUMANRADAR.md) documents the radar and AR demo as a reference for our CSI fall-alert dashboard.
- Nov 14 hardware milestone: after attaching the U.FL antenna, the ESP32-WROOM-32U found 12 networks, joined the 2.4 GHz network on channel 6, and captured 107 access-point CSI frames across eight one-second intervals. The Arduino diagnostic is in `firmware/csi_link_check/`.
- First motion experiment is ready in `tools/Measure-CsiMotion.ps1`. Verified 52 raw CSI frames in six seconds on COM4. The guided capture records 20 seconds each of empty room, walking and standing still across three trials. See README for setup and CSV location.
- One receiver distinguished walking in all three trials. Walking medians were 0.188–0.200, empty 0.097–0.100, and standing 0.085–0.098. Raw data is in `data/csi-motion-20261114-105805.csv`.
- Both ESP32-WROOM-32U receivers (COM4 and COM5) streamed together on channel 1. The desktop visualizer plots live CSI change by receiver. Next, place the second board at a different angle and compare responses along both paths.
- The local browser Observatory reuses RuView's 3D floor and shows CSI changes along a schematic of the receiver paths. Start it with the visualizer launcher's `-Observatory` flag. See README for Windows and macOS usage.
- The Observatory can calibrate a quiet baseline per receiver and show motion above it. The indicator still needs an in-room test.
- Router-free mode uses a third ESP32 as a dedicated access point and transmitter. See README for the `-Standalone` launch. The three-board live test is pending the third board.
- Replacement board (ESP32 MAC ending 9F:1D:98) worked on COM4. Saved the original flash regions affected by the upload in `%LOCALAPPDATA%/Stillpoint/firmware-backups/`, flashed at 230400 baud, and verified about 29.5 frames/sec in the Observatory. Higher-speed backup transfers failed. The other board previously showed USB descriptor errors.
- Nov 14 detector study (branch `claude/detector-compare-54380c`): `research/detector-comparison.md` compares esp-csi, ESPectre, RuView, wifi-sensing-kit, SenseFi, WiFall against our boards; none gives a ready original-ESP32 fall detector. `detection/` has a Python pipeline and a saved random-forest motion model (`detection/models/csi_motion_model.joblib`, API `CsiMotionDetector.predict(frames) -> (label, p_moving)`). Leave-one-trial-out on the motion recording: moving vs still 0.96 (RF) / 0.93 (wander threshold); empty vs standing-still is at chance, so presence must be latched by the state machine. Rerun: `python detection/train_eval.py`. Next data to record: sit, lie down, controlled fall onto a mat, a second receiver at another angle, ideally at ~30 fps.
- `test.txt` and `jack.test` are leftover push-access tests and can be deleted.

- Team to-do list with owners and deadlines (presentation, hardware, software/AI, dashboard, website, submission): Google Doc "Hackathon ideas", https://docs.google.com/document/d/1upIEmQUVUbZdIuxvN-gHEJgOShMZMWAb9dQ6_YxRwJs/edit (To DO LIST section). Keep tasks there, not in the repo.
- Shared Google Drive folder "Hackathon" (editors: Anthony, Jack): https://drive.google.com/drive/folders/1IWIpqnB7UojHoDrU4_enAqYaaRD2JUB3

## Decisions
- Luis authorized flashing the hackathon ESP32 boards as needed without asking again.
- Goal is a product to sell to nursing homes; the hackathon is the first demo. See `research/product.md` (market, competitors, product requirements).
- Event rules, deadlines and judging rubric summarized in `research/hackathon-rules.md`. Key dates: project link Sat 2 PM, Sunday commit + live link Sat 8 PM, submissions close Sun 12 PM, demo is 4 min live + 3 min Q&A. 45/100 points are problem + path to customers, so talk to real caregivers this weekend.
- Scope: fall detection + zone-level location. Not precise tracking or room mapping.
- Use CSI, not RSSI.
- Hardware: 3x ESP32-U (original ESP32, external antenna). RuView doesn't support it → base is espressif/esp-csi + own Python pipeline.
- Presence state machine to stop "person lying still" from reading as "empty room".

## Next steps
1. Answer `research/open-questions.md` (board model first).
2. Create `firmware/`, `detection/`, `dashboard/` skeletons.
3. Validate the motion indicator and run the three-board standalone mode at the venue.
4. Record training data; build threshold fall detector; dashboard.

## Gotchas
- CSI models don't transfer between rooms: retrain at the venue.
- RuView does not support original ESP32 or ESP32-C3.
