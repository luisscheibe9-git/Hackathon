# detection/

Offline CSI person/motion detector built from `data/csi-motion-20261114-105805.csv`
(one ESP32-WROOM-32U receiver, one room, 3 trials x {empty, walking, standing} x 20 s, ~12 frames/s).

## Files
| file | what |
|---|---|
| `csi.py` | parse `lltf_hex` (64 subcarriers x int8 I/Q, order 0..31,-32..-1) into amplitudes over 51 usable subcarriers (2..26, 38..63) |
| `features.py` | hand-made motion scores (team median-change, ESPectre-style turbulence variance, esp-csi-style wander/jitter) and the 13-feature window vector |
| `train_eval.py` | leave-one-trial-out (LOTO) evaluation + trains and saves the final models |
| `detector.py` | live interface `CsiMotionDetector.predict(frames) -> (label, score)` |
| `models/csi_motion_model.joblib` | random forest, moving vs still, 1 s windows (**use this one**) |
| `models/csi_3class_model.joblib` | random forest, empty/standing/walking (empty vs standing is at chance, see results) |
| `results/loto_results_1s.md`, `_2s.md` | full LOTO tables and confusion matrices |
| `humansensing_port.py` | port of [ESP32-WiFi-CSI-Human-Sensing](https://github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing) (MIT, (c) 2026 Sanaullah Shaheer): EMA + Hampel preprocessing, their 180-dim features, KNN/RF, movement heuristic; results in `results/humansensing_port.md` |
| `presence_study.py` | empty vs standing-still study (breathing band 0.1-0.5 Hz, 6 s windows, same-session calibration); results in `results/presence_study.md` |
| `replay.py` | offline movement replay in the Observatory (`tools/observatory/`), N receivers |
| `results/replay-screenshot*.jpg` | replay screenshots (real 1-receiver data; synthetic 3-receiver test) |

## Rerun
```bash
pip install -r detection/requirements.txt
python detection/train_eval.py              # 1 s windows (default), writes results + models
python detection/train_eval.py --win 2      # 2 s windows (also overwrites models/)
python detection/detector.py                # smoke test on the recording
python detection/train_eval.py --csv data/<new-recording>.csv   # retrain on venue data
python detection/humansensing_port.py       # reference-repo port, LOTO
python detection/presence_study.py          # empty vs standing-still study
```
Note: running `train_eval.py` always overwrites `models/` with the window length you passed. The committed models use 1 s.

## Results (LOTO: train on 2 trials, test on the 3rd)
| detector | task | 1 s windows | 2 s windows |
|---|---|---|---|
| wander threshold (no ML) | moving vs still | 0.93 | 0.97 |
| jitter threshold | moving vs still | 0.89 | 0.88 |
| ESPectre-style turbulence variance | moving vs still | 0.81 | — |
| team median-change score | moving vs still | 0.76 | — |
| random forest, motion-only features | moving vs still | 0.96 | 0.97 |
| logistic regression, all features | moving vs still | 0.98 | 0.99 |
| random forest, all features | empty vs occupied | 0.65 | 0.71 |
| random forest, all features | 3-class | 0.67 | 0.67 |
| any single score | empty vs occupied | 0.51-0.62 | 0.61-0.65 |

Per held-out trial, saved model (RF, motion-only, 1 s, moving vs still): trial 1 0.97, trial 2 0.94, trial 3 0.98.
Reference-repo port (`humansensing_port.py`): their RF on their literal 64-sample (~5 s) window gets
0.93 moving vs still (trials 0.90 / 0.92 / 0.98); on 1 s windows it fails (0.45-0.67) because their
EMA smoothing (alpha 0.25) at our 12 Hz washes out short motion and their 162 per-subcarrier
level features overfit the drifting channel profile. Empty vs standing still: 0.21-0.48 (chance or worse).

**Empty vs standing still: no method separates them reliably.** Every motion score, both
learned models and the reference port are at chance or below. The only signal is the distance
to a same-session empty-room calibration (`presence_study.py`, balanced acc 0.86, trials
0.57 / 1.00 / 1.00), but it is confounded with drift (standing was always recorded ~40 s after
empty) and fails on trial 1. Breathing-band power (0.1-0.5 Hz) is weak (0.58-0.68) and
inconsistent across trials. What would help: an interleaved recording (empty, stand, empty, stand)
to test calibration distance against drift; longer still windows (20-30 s) at ~30 fps for the
breathing band; more receivers / paths; and, regardless, the presence state machine holding
"present" until the doorway path fires on exit.

**Reading it honestly:** walking is detected reliably. Empty vs a person standing still is
near chance (3-class confusion: walking 100/102 right, empty and standing mixed ~50/50).
The "all features" models get a bit above chance on empty-vs-occupied mostly through RSSI and
absolute amplitude, which drift over time and are not trustworthy. The empty-room channel
profile itself drifts a lot between trials (profile distance empty-vs-empty across trials
0.29-0.72 vs within-trial 0.002-0.05), so a static "empty baseline" cannot catch a still person
with this one-receiver, AP-traffic setup. Tiny dataset: 3 trials, ~100 windows per class,
one room, one person, one receiver, 12 frames/s. Expect lower numbers in a new room; retrain there.

## Plug into the live stream
```python
from detection.detector import CsiMotionDetector
det = CsiMotionDetector()
label, p_moving = det.predict(last_1s_lltf_hex)   # per receiver, >= 6 frames
```
Per receiver keep a ring buffer of the last 1 s of frames, call `predict` every 0.25-0.5 s,
take the max `p_moving` across receivers. Feed that into the presence state machine:
- empty -> present: motion seen (p_moving > 0.5 for 2 consecutive windows).
- present stays present while still (CSI cannot see a still person, so presence is latched
  until an exit is inferred, e.g. motion near the door then a long quiet period, or a caregiver reset).
- present -> fall suspected: a short burst of strong motion followed by stillness
  (needs fall recordings to tune; not trained yet).
- fall suspected -> fall alert: still for N seconds (e.g. 20-30 s).

## Offline movement replay (Observatory)
```bash
python detection/replay.py                                  # opens http://127.0.0.1:<port>/?replay=1
python detection/replay.py --csv data/<recording>.csv --speed 2 --port 8791 --no-browser
```
`replay.py` steps through a saved CSV in scaled real time and serves the same `/live` JSON as
`tools/csi-visualizer.py`, so the Observatory renders it unchanged; `?replay=1` adds a replay bar
(play/pause, seek, speed, recorded trial/stage as ground truth). Per path it shows the motion
model's P(moving) and the verdict: **"Likely movement near path X"** (P >= 0.7), **"No movement
detected"** (all <= 0.3), otherwise **"Unknown (low confidence)"**. It never draws a person marker:
an x/y position would need location validation we have not done. The existing calibrate button
works in replay too (the recording starts with 20 s of empty room).

N receivers: add a `receiver` (or `port`) column to the CSV; every distinct value becomes its own
path (first two at the live layout positions, more on an arc). The current recording has no such
column, so it replays as one path, `receiver-1`. A synthetic 3-receiver CSV was used only to test
the layout (`results/replay-screenshot-3rx-synthetic.jpg`). Live mode (`Start-CsiVisualizer.ps1 -Observatory`)
is unchanged: the replay bar is hidden without `?replay=1`.

## Person marker and presence state machine (Observatory)
`tools/observatory/person-marker.js` (hooked into `observatory.js` with a few lines) draws a glowing
~1.7 m figure with a floor halo and a side panel (presence state, motion score, P(moving), RSSI,
active path, confidence, fall-rule status). It works in live mode, `?replay=1` and `?demo=fall`.

- **Position is an estimated zone, not a measured spot.** 1 path: midpoint of the most disturbed
  path. N paths: disturbance-weighted blend of the disturbed paths' midpoints, smoothed over ~1 s.
  Halo radius is the uncertainty: about 1.1 m with one path, smaller as more paths agree. The caption
  says "estimated zone".
- **Driven by the presence state machine, not raw motion:** EMPTY (hidden) -> PRESENT after 2
  moving ticks. PRESENT and moving: bright with a gentle pulse. PRESENT and still: stays at the last
  zone, dimmer, slow pulse. Standing still never clears presence. It returns to EMPTY only after the
  doorway path (`?door=<receiver port>`) fires and the room stays quiet for 15 s, or after
  `?emptyAfter=<s>` of no motion (default 900 s).
- **Fall rule** (RuView-style: strong burst, then >= 2 s still -> FALL_SUSPECTED, amber, figure tips
  over; still for 20 s -> FALL_ALERT, red, banner with zone and time). It is untested on real
  falls, so it is **off** in live and replay unless you add `?fall=1`.
- **No heart-rate or respiration numbers.** `?breathing=1` only adds the words "breathing band:
  experimental".
- `?demo=fall` plays a scripted sequence (walk in, stand still, fall, alert after 6 s; 60 s loop)
  on two simulated paths. It is labelled SIMULATED in the header, scene and panel, and needs no data:
  ```bash
  python detection/replay.py --no-browser --port 8791      # any server for tools/observatory works
  # open http://127.0.0.1:8791/?demo=fall
  python -m http.server 8792 -d tools/observatory           # alternative static server
  # open http://127.0.0.1:8792/?demo=fall
  ```
- In replay and demo the live "Calibration needed" panel is hidden. Live mode is unchanged apart
  from the added figure and panel.

Screenshots (`detection/results/`): `person-marker-moving-replay.jpg` and
`person-marker-still-replay.jpg` (real recording: trial 1 walking, then standing, still PRESENT),
`person-marker-moving-sim.jpg`, `person-marker-still-sim.jpg`, `person-marker-fall-alert-sim.jpg`
(simulated demo).
