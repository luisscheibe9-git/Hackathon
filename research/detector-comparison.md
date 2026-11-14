# Open-source CSI detectors vs our boards (2026-11-14)

Our setup: original ESP32 (ESP32-WROOM-32U, U.FL antenna), Arduino-core firmware printing
esp-csi-style CSI, L-LTF only (64 subcarriers, int8 I/Q in `lltf_hex`), 12-30 frames/s per
receiver, 2-3 receivers, processing in Python on a laptop.

Checked from READMEs/docs on GitHub (algorithm source files were not audited line by line).

| Project | Runs on our ESP32 data? | Input it needs | Detects | License | Effort to adapt |
|---|---|---|---|---|---|
| [espressif/esp-csi](https://github.com/espressif/esp-csi) + [esp-radar](https://components.espressif.com/components/espressif/esp-radar) | Chip yes (ESP32 listed), but runs as ESP-IDF firmware, not Arduino | Its own firmware's CSI, ~10+ s empty-room calibration | Presence ("wander") + motion ("jitter") thresholds | Apache-2.0 | High to use as-is (swap firmware); **low to copy the idea** in Python. Exact formulas not in the repo (esp-radar is a separate component) |
| [ESPectre](https://github.com/francescopace/espectre) | Yes (classic ESP32 listed), designed for ~100 pkt/s | Per-packet amplitude, 12 fixed subcarriers; handles the 0..31,-32..-1 L-LTF order | Motion vs idle only (a still person reads as idle); optional 529-parameter MLP | GPLv3 (+ commercial) | **Medium**: features (turbulence = std/mean across subcarriers, lag-1 autocorr, relative IQR, Hampel filter) are documented; window/filter constants need retuning for 12-30 fps; GPL if we copy code |
| [RuView](https://github.com/ruvnet/RuView) | No: firmware is S3 (C6 research); README says original ESP32 unsupported | 56-subcarrier stream, phase | Presence, motion, fall (phase-acceleration threshold + 3-frame debounce + 5 s cooldown), vitals | MIT | High: Rust core, phase-based (ESP32 phase is noisy). Fall rule is a reusable *idea* |
| [andrisgauracs/wifi-sensing-kit](https://github.com/andrisgauracs/wifi-sensing-kit) | No: 3x ESP32-S3 on patched RuView firmware | CSI + webcam (MediaPipe labels) | 7-8 activities incl. empty; 79.5 % same room/person/afternoon | MIT | High. Reusable idea: webcam-supervised labelling |
| [SenseFi](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark) | No: datasets from Intel 5300 / Atheros (90 or 342 features) | UT-HAR 1x250x90, NTU-Fi 3x114x500, Widar BVP | HAR incl. a "fall" class; model zoo (MLP, CNN, LSTM, ViT) | MIT | High: only the training code is reusable; models too large for our ~300 windows |
| [WiFall](https://huggingface.co/datasets/RS2002/WiFall) / [KNN-MMD](https://github.com/RS2002/KNN-MMD) | Partly: ESP32-S3, 52 subcarriers, ~100 Hz | 60 s CSVs, 10 people, fall/jump/sit/stand/walk | Fall + 4 activities | None stated (unclear reuse) | Medium: could sanity-check or pretrain a fall feature; resample + subcarrier mapping needed |
| [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool) | Yes | — | Capture only, no detector | MIT | n/a |
| CSI-Bench, wisense (PyPI) | Unverified | — | Fall among tasks | Unverified | Not worth it before the demo (wisense says untested on hardware) |

## Tested on our recording
Implemented in `detection/` and evaluated leave-one-trial-out on
`data/csi-motion-20261114-105805.csv` (details: `detection/results/loto_results_1s.md`).

| Detector | Moving vs still | Empty vs occupied |
|---|---|---|
| esp-csi-style wander (1 - correlation to window-mean profile), threshold | 0.93 (1 s), 0.97 (2 s) | 0.61 |
| esp-csi-style jitter (consecutive-frame decorrelation) | 0.89 | 0.62 |
| ESPectre-style turbulence variance | 0.81 | 0.53 |
| Team median-change score | 0.76 | 0.51 |
| Random forest, 9 motion features (**saved model**) | 0.96 (1 s), 0.97 (2 s) | 0.53 |

## Recommendation
1. **Use our own Python detector, not someone's firmware.** None of the projects gives a
   ready fall detector for original ESP32; the ones with the best logic need S3 or ESP-IDF.
2. **Motion detector = random forest on esp-csi/ESPectre-style window features**
   (`detection/models/csi_motion_model.joblib`, 1 s windows). It matches the best single
   threshold and visibly puts a learned model in the pipeline. Keep the wander threshold as the
   fallback if the model misbehaves live.
3. **Presence of a still person cannot come from one receiver's CSI here** (empty vs standing is
   at chance). Keep the decided state machine: latch "present" from motion, and treat
   "burst of motion then stillness" as fall suspected. This is exactly why the state machine matters.
4. **Falls:** borrow RuView's structure (impact threshold + debounce + cooldown) on amplitude
   motion score instead of phase, and train on our own controlled-fall recordings.
5. Retrain at the venue: CSI models do not transfer between rooms.
