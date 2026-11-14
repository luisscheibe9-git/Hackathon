# Empty room vs person standing still

6 s windows, 1 s step, amplitude resampled to 12 Hz. Empty windows: 21 (only after each trial's calibration span), standing windows: 39. LOTO: threshold/model fitted on 2 trials, scored on the 3rd. Scores are **balanced accuracy** (mean recall of the two classes), chance = 0.5.

| feature | median empty | median standing | LOTO balanced acc (threshold) | per held-out trial |
|---|---|---|---|---|
| breath_ratio_med | 0.3497 | 0.2718 | 0.58 | {1: 0.55, 2: 0.86, 3: 0.34} |
| breath_ratio_p90 | 0.5814 | 0.4816 | 0.68 | {1: 0.68, 2: 0.81, 3: 0.54} |
| dist_to_session_empty | 0.03085 | 0.4193 | 0.86 | {1: 0.57, 2: 1.0, 3: 1.0} |
| wander | 0.01803 | 0.01522 | 0.23 | {1: 0.47, 2: 0.07, 3: 0.14} |
| jitter | 0.01957 | 0.01819 | 0.43 | {1: 0.58, 2: 0.22, 3: 0.48} |
| espectre_var | 14.77 | 5.976 | 0.64 | {1: 0.57, 2: 0.85, 3: 0.5} |

Per-trial medians (empty / standing):

| feature | trial 1 | trial 2 | trial 3 |
|---|---|---|---|
| breath_ratio_med | 0.3497 / 0.2857 | 0.4487 / 0.233 | 0.3253 / 0.4025 |
| breath_ratio_p90 | 0.5053 / 0.4413 | 0.6341 / 0.4549 | 0.602 / 0.6263 |
| dist_to_session_empty | 0.07665 / 0.1065 | 0.03085 / 0.454 | 0.00267 / 0.4193 |
| wander | 0.01803 / 0.01486 | 0.02585 / 0.009903 | 0.01606 / 0.02608 |
| jitter | 0.0197 / 0.01953 | 0.02426 / 0.01416 | 0.01857 / 0.01916 |
| espectre_var | 11.2 / 5.432 | 21.27 / 5.444 | 15.63 / 11.76 |

Logistic regression on all six features: LOTO balanced acc 0.73, per trial {1: 0.5, 2: 0.93, 3: 0.77}.

**Caveat on dist_to_session_empty:** each trial was recorded empty -> walking -> standing, so the standing windows are ~40 s further from the calibration than the scored empty windows. The empty-room profile drifts by a similar amount between trials (empty-vs-empty distance 0.29-0.72 across trials), so this result can be drift, not the person. It needs an interleaved recording (empty, stand, empty, stand, ~20 s each, re-checked a few minutes later) before we trust it.
