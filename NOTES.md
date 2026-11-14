# NOTES

## Goal
Build accurate person tracking and fall detection within the triangle formed by three ESP32 boards, using Wi-Fi CSI with only board #1 connected to the laptop. Accuracy must be measured against labeled positions and separate fall/activity trials.

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
- Router-free mode is verified with COM6 transmitting and COM4 receiving about 20 CSI frames/sec. COM5 was unplugged during the test and still needs the updated receiver firmware and a simultaneous capture. See README for the `-Standalone` launch.
- One-USB gateway mode verified CSI relaying from receiver 9F1D98 to COM6. The laptop opened only COM6. Receiver 9F1D98 still drew power from laptop USB during this test. COM5 needs flashing and a simultaneous test.
- For a moving person marker, fix all three antenna positions, tag several marked spots and walking routes in the triangle, then test a position model on separate walking passes. The current two sensing paths report motion. Evaluate a third receiver-to-receiver path if locations remain ambiguous.
- Replacement board (ESP32 MAC ending 9F:1D:98) worked on COM4. Saved the original flash regions affected by the upload in `%LOCALAPPDATA%/Stillpoint/firmware-backups/`, flashed at 230400 baud, and verified about 29.5 frames/sec in the Observatory. Higher-speed backup transfers failed. The other board previously showed USB descriptor errors.
- Nov 14 detector study (branch `claude/detector-compare-54380c`): `research/detector-comparison.md` compares esp-csi, ESPectre, RuView, wifi-sensing-kit, SenseFi, WiFall against our boards; none gives a ready original-ESP32 fall detector. `detection/` has a Python pipeline and a saved random-forest motion model (`detection/models/csi_motion_model.joblib`, API `CsiMotionDetector.predict(frames) -> (label, p_moving)`). Leave-one-trial-out on the motion recording: moving vs still 0.96 (RF) / 0.93 (wander threshold); empty vs standing-still is at chance, so presence must be latched by the state machine. Rerun: `python detection/train_eval.py`. Follow-up: ported the closest open-source match, ESP32-WiFi-CSI-Human-Sensing (classic ESP32, MIT): its RF gets 0.93 moving vs still on ~5 s windows. No method separates empty from standing still (all at chance; same-session calibration distance looks promising but is confounded with drift), see `detection/results/presence_study.md`. Offline movement replay in the Observatory: `python detection/replay.py` (`?replay=1`, N receivers via a `receiver` CSV column, shows 'likely movement near path X' / 'unknown', no person marker). Next data to record: sit, lie down (and interleaved empty/stand), controlled fall onto a mat, a second receiver at another angle, ideally at ~30 fps.
- Observatory person marker (branch `claude/detector-compare-54380c`): `tools/observatory/person-marker.js` adds a glowing figure on an estimated zone, driven by the presence state machine (EMPTY / PRESENT moving / PRESENT still / FALL_SUSPECTED / FALL_ALERT) and a side panel. Still people stay present. The fall rule is off unless `?fall=1` (no real fall data). `?demo=fall` is a labelled simulated sequence. No heart rate or respiration shown. See `detection/README.md`.
- `test.txt` and `jack.test` are leftover push-access tests and can be deleted.

- Team to-do list with owners and deadlines (presentation, hardware, software/AI, dashboard, website, submission): Google Doc "Hackathon ideas", https://docs.google.com/document/d/1upIEmQUVUbZdIuxvN-gHEJgOShMZMWAb9dQ6_YxRwJs/edit (To DO LIST section). Keep tasks there, not in the repo.
- Shared Google Drive folder "Hackathon" (editors: Anthony, Jack): https://drive.google.com/drive/folders/1IWIpqnB7UojHoDrU4_enAqYaaRD2JUB3

## Decisions
- Luis authorized flashing the hackathon ESP32 boards as needed without asking again.
- Goal is a product to sell to nursing homes; the hackathon is the first demo. See `research/product.md` (market, competitors, product requirements).
- Event rules, deadlines and judging rubric summarized in `research/hackathon-rules.md`. Key dates: project link Sat 2 PM, Sunday commit + live link Sat 8 PM, submissions close Sun 12 PM, demo is 4 min live + 3 min Q&A. 45/100 points are problem + path to customers, so talk to real caregivers this weekend.
- Scope: accurate person tracking and fall detection throughout the three-board triangle. Zone estimates are the current prototype stage.
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


## Latest verified hardware milestone — November 14, 2026
- All three boards flashed and upload hashes verified using Arduino ESP32 core 3.3.12, target esp32:esp32:esp32.
- Permanent board identities: #1 gateway 68:09:47:9f:1d:98, #2 receiver/probe sender 68:09:47:9f:27:f4, #3 receiver 68:09:47:1a:80:ac. COM ports may change.
- Router-free CSI streams #1 → #2, #1 → #3 and #2 → #3 verified simultaneously. Only #1 needs laptop USB. #2 and #3 need steady power.
- #2 sends ESP-NOW probes on the gateway channel. #3 forwards peer CSI using a separate PEER record. Observed rates were about 35, 46 and 23 frames/s respectively. Browser verification showed 3 sensing paths live.
- Live motion model scores all three paths. Physical board labels, a guided two-path check, and animated path-zone marker are integrated. User reports substantially improved response after adding the third path.
- Current marker blends fixed path midpoints based on motion scores. Accurate position tracking remains the next development goal. Fall detection is unvalidated and the fall rule is off by default.
- Run tools/Start-CsiVisualizer.ps1 with -GatewayPort COM4 -MotionModel from this checkout. Open the URL printed at startup. Last verified URL was http://127.0.0.1:49367/ and changes on restart.
- Active local checkout: C:/Users/lscheibe/AppData/Local/Stillpoint/three-board-test, branch claude/detector-compare-54380c. Main Desktop checkout is older and has separate uncommitted work.
- Validation completed: both firmware builds, all three hardware uploads, simultaneous live CSI, parser test distinguishing three streams, JavaScript/Python syntax checks, browser rendering with real and synthetic streams.

## Next calibration and detection work
1. Measure board coordinates and heights, fix antenna placement, and capture a quiet baseline for each path.
2. Add a labeled raw-CSI recording workflow for seven marked locations, including standing and small movements in different orientations. Repeat locations in a different order.
3. Train a location model using all three streams, then measure distance error and zone confusion on separate walking passes. Position accuracy is currently unmeasured.
4. Collect controlled fall-like movements and ordinary activities with labels. Evaluate missed detections and false alarms on separate trials before enabling a fall alert.
