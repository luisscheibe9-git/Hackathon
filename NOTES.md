# NOTES

## Goal
Build accurate person tracking and fall detection within the triangle formed by three ESP32 boards, using Wi-Fi CSI with only board #1 connected to the laptop. Accuracy must be measured against labeled positions and separate fall/activity trials.

## Team / repo
- Repo: https://github.com/luisscheibe9-git/Hackathon (private). Collaborators with write access: Aouzzo, jbj4poly-dotcom.
- Default branch `main`. Research added on branch `research`.

## Current state (2026-11-13)
- Research done: see `research/` (viability verdict, approach, sources, open questions).
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
- Three-board empty-room baseline verified with #1 on COM4 as the only USB data connection. #2 and #3 streamed over the private Wi-Fi network in all 20 snapshots, averaging 54.0 and 51.8 frames/sec respectively. Median CSI change was 0.1287 on #2 and 0.0416 on #3, so calibrate each link separately. Boards #2 and #3 were about 12 ft apart and each was about 10 ft from #1. Data is in `data/empty-room-three-board-20261114-125539.csv`. Board #2's power bank initially shut off and needed a steady power source.
- Live motion model integrated in the `%LOCALAPPDATA%/Stillpoint/three-board-test` checkout. Launch the gateway viewer with `-MotionModel` to score both receivers every half second using windows sampled at approximately 12 Hz. The browser uses those scores to drive the estimated person marker and displays the physical labels #1, #2 and #3. Local viewer at http://127.0.0.1:54832/. During a prompted walk, both receivers streamed across all 40 snapshots. On samples 17–21, high motion scores first appeared on #2 and then on #3. Peak scores were 0.988 and 1.000. This capture had no time-aligned ground truth for walking or position. Scores are in `data/three-board-walk-model-20261114-130134.csv`.
- For a moving person marker, fix all three antenna positions, tag several marked spots and walking routes in the triangle, then test a position model on separate walking passes. The current two sensing paths report motion. Evaluate a third receiver-to-receiver path if locations remain ambiguous.
- Replacement board (ESP32 MAC ending 9F:1D:98) worked on COM4. Saved the original flash regions affected by the upload in `%LOCALAPPDATA%/Stillpoint/firmware-backups/`, flashed at 230400 baud, and verified about 29.5 frames/sec in the Observatory. Higher-speed backup transfers failed. The other board previously showed USB descriptor errors.
- `test.txt` and `jack.test` are leftover push-access tests and can be deleted.

- Live Observatory refreshes about three times per second. With the trained model enabled, the top status and highlighted path follow the latest motion score, each receiver shows its score, and the person marker shows an estimated zone from the two paths. The live UI changes are in the checkout above (under `tools/observatory/`). Verified the browser showed both live receivers and their changing scores at `http://127.0.0.1:54832/`.

- The live checkout now has a browser-based **Start path check** for #1→#2 and #1→#3. It measures the share of motion threshold crossings in a quiet baseline and each prompted crossing. The person marker now interpolates between path zones on every animation frame, even after a short score burst ends. Browser verified with both real receivers; the path-check verdict was verified with simulated separate and overlapping scores. A guided physical walk is still needed to validate the placement.

- Direct #2 → #3 is live at http://127.0.0.1:49367/ from `%LOCALAPPDATA%/Stillpoint/three-board-test`. #2 sends same-channel ESP-NOW probes to #3, which reports their CSI to #1 for USB relay. Both Arduino ESP32 builds and all three flash uploads verified. With #1 on COM4 and #2/#3 on steady USB power, the HTTP feed measured 35.0 (#1 → #2), 45.5 (#1 → #3) and 23.0 (#2 → #3) CSI frames per second. The Observatory drew all three sides with synthetic input. Launch with `-GatewayPort COM4 -MotionModel` and use the new URL it prints. The firmware sketches are also under `firmware/` in the main project folder. Next: validate each path against physical crossings and collect labeled zone walks.

## Decisions
- Physical board labels are permanent. Windows COM numbers can change.
  - **#1** is on COM4, with Wi-Fi MAC ending 9F:1D:98. Reflashed and verified as the transmitter and USB gateway for the three-board room test.
  - **#2** was flashed and verified on COM4 as a wireless receiver for the room test. Its Wi-Fi MAC ends in 9F:27:F4.
  - **#3** was flashed and verified as the second wireless receiver. Its Wi-Fi MAC ends in 1A:80:AC.
- Luis authorized flashing the hackathon ESP32 boards as needed without asking again.
- Scope: accurate person tracking and fall detection throughout the three-board triangle. Zone estimates are the current prototype stage.
- Use CSI, not RSSI.
- Base: RuView if boards are ESP32-S3/C6, otherwise espressif/esp-csi + own Python pipeline.
- Presence state machine to stop "person lying still" from reading as "empty room".

## Next steps
1. Answer `research/open-questions.md` (board model first).
2. Create `firmware/`, `detection/`, `dashboard/` skeletons.
3. Run the one-link motion experiment and compare CSI variation across each trial before adding a receiver.
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

## Downloaded teammate training stack
- Downloaded esp32/ from origin/esp32-wroom-firmware commit 76aa09c into this project on November 14. Original archive is also in Downloads/haven-training-76aa09c.zip. Python syntax compilation passed. Setup guide is esp32/HAVEN_SENSING.md.
- This is new Haven code inspired by wifi-sensing-kit. Its host expects UDP binary packets or CSIB base64 serial at 921600 baud. Our live gateway emits RELAY/PEER hex rows at 460800 baud. A transport adapter or firmware migration is required before live training. Dependencies and webcam model assets have not been installed, and no training has run. Current three-link firmware remains operational.
- Nov 14 ~3:45 PM (Claude, continuing Codex): live training works on the existing three-link firmware via a gateway adapter in `esp32/host/server.py` (`parse_gateway_line`). Start it with `esp32/.venv/Scripts/python.exe -u esp32/host/server.py --gateway COM4` (from `esp32/`), open http://127.0.0.1:8940/train.html. The Observatory (`tools/csi-visualizer.py`) must be stopped first: only one program can hold COM4.
  - Adapter maps RELAY from #2/#3 to links 1>2 / 1>3 and PEER from #3 to 2>3. Verified live: 3 links, RSSI -60 to -65 dBm.
  - The Arduino receivers send L-LTF tones in centred order (-32..31); the adapter swaps the halves to Haven's 0..31,-32..-1 order and does not set F_FIRST_BAD. Before this fix 8 zero guard tones were used as features and 10 real tones dropped.
  - Live packet rates were only ~4.5-7.5/s per path (NOTES earlier said 23-46/s), so the link-active threshold was lowered from 5 to 3 packets/s (server + train.html badge). Low rate limits accuracy; check receiver power/placement.
  - train.html: falls are now the core of training (on by default, untick if no mat): per round 'lie down slowly' (the negative) plus fall forward, fall sideways, slide off chair. If the camera's fast-drop rule misses a prompted fall but the person is lying 4 s after 'Now', the first 3.5 s after 'Now' are labelled 'fall'.
  - Fixed 'Record training' failing with 'no links are streaming': the gateway serial reader stalled after ~15 s. Fix: 1 MB serial RX buffer (Windows default 4 KB mangled lines), a 5 s silence watchdog that reopens the port, and a 10 s log line with matched/unmatched gateway lines. Feature window widened 1.5 -> 2.0 s for the low packet rates.
  - ~4:00 PM: the first training run lost everything after round 1 standing: blocking `readline()` hung mid-session. Replaced with a non-blocking reader (short timeout + manual line split, like `tools/csi-visualizer.py`) and a watchdog thread that force-closes a silent port. With it, rates are 33-43 packets/s per path (117 lines/s total): **the earlier 3-8/s was the old reader dropping data, not the boards.** The 62 low-rate windows were cleared (backup `esp32/data/haven_dataset-partial-1543.npz`). train.html now shows a red warning when a recorded link goes silent.
  - ~4:15 PM: fall-focused run evaluated on a separate test round: 41% over 5 classes, **0/8 fall windows**, moving vs still ~74%. Saved as `esp32/data/haven_dataset-fallrun-1615.npz`.
  - ~4:30 PM PIVOT (team decision): classes are empty, standing, walking, sitting/squatting, lying; **lying down = fall alert** (`config.yaml`: `alert_on_any_lying: true`, `long_lie_seconds: 5`). train.html routine per round: leave, stand, walk, sit, squat (label sitting), lie on floor, leave again; 3 training rounds + 1 test. Fall steps hidden. Raw CSI is now logged during recordings to `esp32/data/raw/raw-<session>-r<round>-<time>.csv` for re-analysis.
  - ~4:50 PM posture run (3 train rounds + 1 test, dataset `esp32/data/haven_dataset.npz`, backup `haven_dataset-posture-1648.npz`, raw CSV in `esp32/data/raw/`). Sitting and squatting are one class: `training_label()` now counts camera 'standing' under the sit/squat prompt as sitting. Test session: **67.5%** over 5 classes (guessing 20%); empty and walking 100%, lying recall 38% with 0 false lying predictions, standing 27%. Path 2>3 alone scored 75% / lying 28/29 on the test round, but only 46% lying recall across training rounds, so that choice is not yet trustworthy.
  - ~5:10 PM: boards were moved, so all earlier models are invalid (old dataset kept as `haven_dataset-posture-oldsetup.npz`). New 4-class routine (empty, standing, walking, lying): per round 10 s empty, 12 s standing, 12 s walking, then 5 lying steps of 15 s (back, side, face down, another spot, still with small moves). Under the lying prompt a camera 'sitting' also counts as lying. Alert: lying = possible fall, FALL ALERT after 3 s (`long_lie_seconds: 3`). Live predictions logged to `esp32/data/live-log-<date>.csv` every 0.5 s.
  - ~5:30 PM 4-class result (new board positions; backup `esp32/data/haven_dataset-4class-1730.npz`): separate test round **94.1%** (balanced ~85%; lying is 70% of windows). Lying caught 118/118. Non-lying windows read as lying: 10/51 raw, but with the server's 3 s smoothing the longest false 'lying' run was 2.0 s (standing), below the 3 s alert, so no false alert on the test round. Leave-one-round-out 84.5%. Each path alone: 1>2 82%, 1>3 85%, 2>3 72%.
  - ~5:45 PM camera vs WiFi: the webcam teacher missed ~24% of the test round's lying time (never stored or scored). New `esp32/host/retrain_from_raw.py` rebuilds the dataset from the raw CSI logs labelled by the guided PROMPT (skipping each step's first 2 s), `--save` writes it as the live dataset (camera-labelled one backed up as `haven_dataset-camera-labels-1724.npz`). With prompt labels the unbalanced kNN read standing as lying for 4 s (false alert), so `Dataset.train()` now caps every class at 2x the smallest (`balanced()`). Server's balanced model on the test round: 89.5%, empty 100%, standing 94%, walking 100%, lying 86%; 3 s-smoothed replay: no false lying run in empty/standing/walking, all 5 lying steps reach the 3 s alert (the 'small moves' step only for 4 s, then reads walking). A FALL ALERT now stays until staff acknowledge it (no auto-clear). Note: `evaluate.py` still scores an unbalanced model.
  - ~5:45 PM demo screen for filming: http://127.0.0.1:8940/demo.html (`esp32/host/web/demo.html`, linked from the live page). Full-screen dark layout, big status (Room empty / Person standing / Person walking / Possible fall with 3 s progress bar / FALL DETECTED with on-floor timer), activity bars, sensing-path schematic (schematic sensor positions in `NODES`, to be replaced by the measured room). On FALL DETECTED a caregiver card animates: fall detected -> message sent -> delivered -> waiting; acknowledge button or key A. The card says 'Demo: notification shown on screen, no SMS is sent' (no real messaging exists). Acknowledge stale alerts before filming.
  - ~7:20 PM offline experiments (`esp32/host/experiments.py`, results `esp32/data/experiments.md`; data backup `Downloads/haven-data-backup-20261114-1919.zip`): window 1/2/3 s x 4 feature sets x kNN/ExtraTrees/SVM/LogReg/MLP x path subsets, scored by LORO + separate test + simulated false/missed alerts. Findings: current live (2 s, Haven features, kNN7) LORO 0.86, test 0.95, 0 false alerts/12, 2 missed/20. Best: **3 s window, same features, kNN7**: LORO 0.85, test 1.00, 0 false/12, 1 missed/20 (costs ~1 s more latency). Neural net (MLP) worse (LORO 0.66-0.80); motion-only features much worse (the static shape carries posture); SVM/ExtraTrees catch more lying but give 1-3 false alerts; all 3 paths beat any pair. Not applied to the live server yet.

## Goal
Hackathon project: 3x ESP32 Wi-Fi CSI sensing to detect falls of elderly residents and report when and in which room zone they happened. No cameras, no wearables.

## Team / repo
- Repo: https://github.com/luisscheibe9-git/Hackathon (private). Collaborators with write access: Aouzzo, jbj4poly-dotcom.
- Default branch `main`. Research added on branch `research`.

## Current state (2026-11-13)
- Research done: see `research/` (viability verdict, approach, sources, open questions).
- [Wi-Fi sensing demo](research/wifi-sensing.md) records reported ESP32-S3 results and reproduction steps.
- No code yet. `test.txt` and `jack.test` are leftover push-access tests and can be deleted.

- Team to-do list with owners and deadlines (presentation, hardware, software/AI, dashboard, website, submission): Google Doc "Hackathon ideas", https://docs.google.com/document/d/1upIEmQUVUbZdIuxvN-gHEJgOShMZMWAb9dQ6_YxRwJs/edit (To DO LIST section). Keep tasks there, not in the repo.

## Decisions
- Product name: **Haven** (chosen 2026-11-14). Camera-free privacy goes in the tagline, e.g. "Camera-free safety at home."
- Bulk hardware cost estimate: ~$6-13 per node, ~$18-39 per 3-node kit, wall-powered (batteries last ~1 day with CSI). See `research/bom-cost.md`.
- Goal is a product to sell to nursing homes; the hackathon is the first demo. See `research/product.md` (market, competitors, product requirements).
- Event rules, deadlines and judging rubric summarized in `research/hackathon-rules.md`. Key dates: project link Sat 2 PM, Sunday commit + live link Sat 8 PM, submissions close Sun 12 PM, demo is 4 min live + 3 min Q&A. 45/100 points are problem + path to customers, so talk to real caregivers this weekend.
- Scope: fall detection + zone-level location. Not precise tracking or room mapping.
- Use CSI, not RSSI.
- Hardware: 3x ESP32-U (original ESP32, external antenna). RuView doesn't support it → base is espressif/esp-csi + own Python pipeline.
- Presence state machine to stop "person lying still" from reading as "empty room".

## Next steps
1. Answer `research/open-questions.md` (board model first).
2. Create `firmware/`, `detection/`, `dashboard/` skeletons.
3. Get CSI streaming from one board to a laptop.
4. Record training data; build threshold fall detector; dashboard.

## Gotchas
- CSI models don't transfer between rooms: retrain at the venue.
- RuView does not support original ESP32 or ESP32-C3.
## Nov 14 ~23:15 — setup 4 (boards moved again)
- Hardware gotchas found: gateway's first USB cable dropped data ("device not functioning"); #3's original charger was too weak (swapped power with #2 → fixed). After any gateway reset/freeze, press EN on #2 and #3 too (receivers do not rejoin on their own).
- Old setup data backed up: `esp32/data/haven_dataset-setup3-prompt-2230.npz` (+ `experiments-setup3.md`).
- New rounds: raw-train-r1..r3 230141/230418/230654, raw-test 231012 (clean, 30–49 pkt/s/path, no gaps).
- Live model = prompt-labelled balanced kNN (2 s): test 74% (empty 38, standing 100, walking 100, lying 70), LORO 67%. Much worse than setup 3 (95%). Main error: lying still ↔ empty.
- `experiments.py` now takes `EXP_TRAIN`/`EXP_TEST`/`EXP_OUT` env vars; setup-4 grid in `esp32/data/experiments-setup4.md`: best ~0.77–0.79 TEST, 3 s window no help.
- 3 s window: keep in mind (helped on setup 3), not switched.
- ~23:30: empty room read as 100% lying live. Fix: recorded 65 s extra empty via API (`raw-train-r4-20261114-232511.csv`, prompt "empty"), retrained with `retrain_from_raw.py --train r1 r2 r3 r4 --test ... --save`, and raised `balanced()` cap 2→4 (`host/cap_sweep.py` compares caps). Server test now 80% (empty 100, standing 94, walking 100, lying 73); empty room reads empty live.
- demo.html: Start button (Enter/Space), Reset (R) and Stop (Esc); caregiver card removed (old version in `esp32/data/demo-caregiver-version.html`). New `/api/reset` endpoint → `Detector.reset()` clears a fall in progress (ack alone did not).
- Phone push (Nov 14 ~23:45): `push_phone()` in server.py posts to ntfy.sh topic `notify.ntfy_topic` in `esp32/config.yaml` (git-ignored) when the detector enters "alert". Title "Fall detected in Room 1", body "Check on patient." Only armed after demo Start (`/api/reset`), disarmed by Stop (`/api/disarm`). Test: demo "Test phone" button / key T → `/api/notify_test`. Room renamed to "Room 1". Phone: install ntfy app, subscribe to the topic in config.yaml.
- Open issue: empty room drifts back toward "lying" (64% after restart) — re-record empty or retrain if false alerts appear while filming.
- Calibrate empty room (Nov 15 ~00:00): demo button "Calibrate empty room" (key C) → `/api/calibrate` → `Dataset.calibrate_empty()`: 5 s countdown, 20 s live recording labelled empty (session train, round 99), replaces the previous calibration, saves + retrains. Status in `/api/state` → `calibration`; full-screen countdown overlay on demo.html. Note: `retrain_from_raw.py --save` rebuilds from raw logs and drops calibration windows (just recalibrate after).
- Nov 14 23:49 full retrain started: old dataset backed up `esp32/data/haven_dataset-setup4-final-2349.npz`, dataset cleared. train.html routine is now demo-focused (empty 20 s, stand, walk the demo path, stand at fall spot, fall and stay down, side, still with small moves); 4 training rounds + 1 test. Old routine saved in `esp32/data/train-routine-setup4.html`. After recording: `retrain_from_raw.py --train <4 newest raw-train> --test <newest raw-test> --save` (prompt labels), restart server, then Calibrate empty room.
- Nov 15 00:15 setup 5 model: 4 demo-routine rounds (raw 235351/235606/235821/000036, test 000301), prompt labels. Standing re-recorded alone (bad spot first time): stripped standing from npz (backup `haven_dataset-setup5-with-standing.npz`), then `/api/calibrate` with `{"label":"standing","seconds":60,"round":98}` + test `{"session":"test","round":97,"seconds":15}`. `/api/calibrate` now records any single label. Server test 99% (standing 100, lying 100, empty 100, walking 91) — standing test taken right after training, so optimistic. Grid: `esp32/data/experiments-setup5.md` (SVM 3 s best before the fix). Do NOT run retrain_from_raw --save now: it would drop the re-recorded standing.
- Nov 15 ~00:30 DEMO MODEL = 3 classes (empty / walking / lying). The standing re-record was bogus (nobody stood; it recorded the room) → removed all standing windows (backup `haven_dataset-setup5-bad-standing.npz`). Real held-out test round: 98% (empty 100, lying 100, walking 91), LORO 94%. demo.html shows any movement as "Person walking". Caveat: no standing class → standing still or sitting reads as lying → alert. Demo script: empty → walk in → fall → stay down; keep moving otherwise.
- Nov 15 ~00:45 per-state calibration: demo.html top-bar ▾ arrow (nearly invisible) opens menu: Calibrate Empty room / Standing / Walking / Lying down (20 s each, countdown, full-screen instructions) + Test phone. Server: `Dataset.CAL_ROUNDS` (empty 99, standing 96, walking 95, lying 94), each calibration replaces that state's last one; calibration windows weighted 3x (`CAL_WEIGHT`) and not balanced away. Standing exists again only via calibration.
- Nov 15 ~00:55: calibration now REPLACES a state's training data (old windows of a calibrated state are dropped); all old calibrations cleared. Calibrate all 4 states → model is calibration-only.
