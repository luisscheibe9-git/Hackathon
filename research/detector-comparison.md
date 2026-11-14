# Open-source CSI detectors vs our boards (2026-11-14)

Our setup: original ESP32 (ESP32-WROOM-32U, U.FL antenna), Arduino-core firmware printing
esp-csi-style CSI, L-LTF only (64 subcarriers, int8 I/Q in `lltf_hex`), 12-30 frames/s per
receiver, 2-3 receivers, processing in Python on a laptop.

Checked from READMEs/docs on GitHub (algorithm source files were not audited line by line).

## Primary reference: ESP32-WiFi-CSI-Human-Sensing

[everythingfreee/ESP32-WiFi-CSI-Human-Sensing](https://github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing),
**MIT License, Copyright (c) 2026 Sanaullah Shaheer.** Credit: our `detection/humansensing_port.py`
re-implements its preprocessing, features, models and movement heuristic.

- **Hardware match: best of all candidates.** Two classic ESP32 DevKit V1 (ESP-WROOM-32): one AP + traffic
  generator, one CSI receiver over USB serial. Arduino core 2.0.17 with direct `esp_wifi_set_csi*` calls,
  HT20 channel 6, 60 Hz traffic. Same 128-byte L-LTF I/Q payload and `first_word_invalid` quirk as ours.
- **Detects:** presence (person / empty), movement (moving / static), and a 1-D position 0..1 along the
  link. Single person. Without trained models it falls back to "motion = presence".
- **Pipeline:** drop the 4 invalid bytes, amplitude on 54 listed subcarriers, EMA smoothing (alpha 0.25),
  optional Butterworth low-pass, reset on >0.5 s gaps. Windows of 64 samples (~1 s at 60 Hz), stride 8,
  Hampel filter (3.5 MAD). 180 features: per-subcarrier mean/std/mean-abs-diff (162), aggregate stats,
  temporal std/diff/energy/slope, 4 FFT band energies, RSSI mean/std/last, relative activity.
- **Models:** KNN (k=7, distance-weighted, scaled) and random forest (200 trees, leaf 2, balanced) for
  presence; same families for position; optional PyTorch MLP (64-32). Movement = sigmoid of
  `move_rel_activity` around 1.5 x the empty-room calibration baseline. Splits by session, not by row.
- **Reported accuracy: none on real data.** The README says real dataset collection and training are
  not done; only synthetic tests exist.
- **On our recording (LOTO, `detection/results/humansensing_port.md`):**

| Their method, our data | Window | Moving vs still | Empty vs occupied | Empty vs standing still | 3-class |
|---|---|---|---|---|---|
| Random forest | 64 samples (~5 s at our 12 Hz) | **0.93** (0.90 / 0.92 / 0.98) | 0.67 | 0.48 | 0.62 |
| KNN | 64 samples | 0.89 (0.87 / 0.86 / 0.96) | 0.42 | 0.21 | 0.43 |
| Movement heuristic | 64 samples | 0.66 (misses nearly all walking) | — | — | — |
| Random forest | 12 samples (~1 s) | 0.45 | 0.64 | 0.37 | 0.34 |
| KNN | 12 samples (~1 s) | 0.65 | 0.54 | 0.25 | 0.38 |

  Per-fold values in parentheses (held-out trial 1 / 2 / 3). The 1 s variant fails because their EMA at
  our 12 Hz smooths motion away and the 162 per-subcarrier features fit the drifting static profile.
  At ~5 s windows their RF is close to our 13-feature model (0.96 at 1 s). Effort to adopt: **low**
  (same chip, same payload, MIT, Python); retune EMA/window for our frame rate.

## Other candidates

| Project | Runs on our ESP32 data? | Input it needs | Detects | License | Effort to adapt |
|---|---|---|---|---|---|
| [ESP32-WiFi-CSI-Human-Sensing](https://github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing) | **Yes** (classic ESP32, Arduino) | L-LTF amplitude, 54 subcarriers, ~60 Hz | Presence, movement, 1-D position | MIT | **Low**, ported (see above) |
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
| Random forest, 9 motion features (**saved model**) | 0.96 (1 s; folds 0.97 / 0.94 / 0.98), 0.97 (2 s) | 0.53 |
| ESP32-WiFi-CSI-Human-Sensing RF, ~5 s windows | 0.93 (folds 0.90 / 0.92 / 0.98) | 0.67 |

**Empty vs standing still:** no method separates them reliably. All motion scores, our models and the
reference port are at chance or worse (0.21-0.53). Distance to a same-session empty calibration reaches
balanced accuracy 0.86 (folds 0.57 / 1.00 / 1.00) but is confounded with channel drift; breathing-band
power (0.1-0.5 Hz, 6 s windows) is 0.58-0.68 and inconsistent. See `detection/results/presence_study.md`.

## Recommendation
1. **Use a Python detector on our existing firmware.** ESP32-WiFi-CSI-Human-Sensing is the closest
   match (same chip, MIT) and its RF reaches 0.93 on our data with ~5 s windows; our leaner 13-feature RF
   reaches 0.96 at 1 s, which reacts faster, so it stays the default. None of the projects gives a ready
   fall detector for original ESP32.
2. **Motion detector = random forest on esp-csi/ESPectre-style window features**
   (`detection/models/csi_motion_model.joblib`, 1 s windows). It matches the best single
   threshold and visibly puts a learned model in the pipeline. Keep the wander threshold as the
   fallback if the model misbehaves live.
3. **Presence of a still person cannot come from one receiver's CSI here** (empty vs standing is
   at chance). To try: interleaved empty/stand recordings to test same-session calibration distance
   against drift, 20-30 s still windows at ~30 fps for the breathing band, more receivers. Keep the decided state machine: latch "present" from motion, and treat
   "burst of motion then stillness" as fall suspected. This is exactly why the state machine matters.
4. **Falls:** borrow RuView's structure (impact threshold + debounce + cooldown) on amplitude
   motion score instead of phase, and train on our own controlled-fall recordings.
5. Retrain at the venue: CSI models do not transfer between rooms.
