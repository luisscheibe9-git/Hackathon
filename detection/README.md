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

## Rerun
```bash
pip install -r detection/requirements.txt
python detection/train_eval.py              # 1 s windows (default), writes results + models
python detection/train_eval.py --win 2      # 2 s windows (also overwrites models/)
python detection/detector.py                # smoke test on the recording
python detection/train_eval.py --csv data/<new-recording>.csv   # retrain on venue data
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
