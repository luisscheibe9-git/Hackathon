# Leave-one-trial-out results
Recording `csi-motion-20261114-105805.csv`, one receiver, one room. Windows 1 s, step 0.5 s, first 1 s of each stage dropped. Windows per class: {'empty': 101, 'standing': 101, 'walking': 102}. Each fold trains on 2 trials and tests on the third (3 folds). Overlapping windows never cross the train/test split because splits are by trial.
## 1. Threshold on a single motion score (threshold fitted on training trials)
| score | task | LOTO acc | per held-out trial |
|---|---|---|---|
| team_change | motion (walking vs empty+standing) | 0.76 | {1: 0.7830188679245284, 2: 0.7714285714285715, 3: 0.7204301075268817} |
| team_change | occupied (walking+standing vs empty) | 0.51 | {1: 0.5283018867924528, 2: 0.49523809523809526, 3: 0.5053763440860215} |
| espectre_var | motion (walking vs empty+standing) | 0.81 | {1: 0.9339622641509434, 2: 0.8952380952380953, 3: 0.5698924731182796} |
| espectre_var | occupied (walking+standing vs empty) | 0.53 | {1: 0.6132075471698113, 2: 0.4380952380952381, 3: 0.5483870967741935} |
| jitter | motion (walking vs empty+standing) | 0.89 | {1: 0.9245283018867925, 2: 0.9047619047619048, 3: 0.8387096774193549} |
| jitter | occupied (walking+standing vs empty) | 0.62 | {1: 0.6132075471698113, 2: 0.5333333333333333, 3: 0.7096774193548387} |
| wander | motion (walking vs empty+standing) | 0.93 | {1: 0.9433962264150944, 2: 0.9142857142857143, 3: 0.9247311827956989} |
| wander | occupied (walking+standing vs empty) | 0.61 | {1: 0.6132075471698113, 2: 0.5428571428571428, 3: 0.6774193548387096} |

Per-class medians of each score (all trials):

| score | empty | standing | walking |
|---|---|---|---|
| team_change | 0.1016 | 0.08814 | 0.1945 |
| espectre_var | 8.406 | 7.185 | 26.63 |
| jitter | 0.0507 | 0.04411 | 0.1043 |
| wander | 0.02204 | 0.01933 | 0.05356 |

## 2. Learned classifiers on window features
| model | features | task | LOTO acc | per held-out trial |
|---|---|---|---|---|
| logreg | all | moving vs still (empty+standing) | 0.98 | {1: 0.9905660377358491, 2: 0.9619047619047619, 3: 0.989247311827957} |
| logreg | all | empty vs occupied | 0.59 | {1: 0.7169811320754716, 2: 0.5333333333333333, 3: 0.5161290322580645} |
| logreg | all | 3-class | 0.61 | {1: 0.6981132075471698, 2: 0.6095238095238096, 3: 0.4946236559139785} |
| logreg | motion-only | moving vs still (empty+standing) | 0.96 | {1: 0.9716981132075472, 2: 0.9619047619047619, 3: 0.956989247311828} |
| logreg | motion-only | empty vs occupied | 0.50 | {1: 0.6415094339622641, 2: 0.44761904761904764, 3: 0.40860215053763443} |
| logreg | motion-only | 3-class | 0.57 | {1: 0.6886792452830188, 2: 0.638095238095238, 3: 0.3655913978494624} |
| random_forest | all | moving vs still (empty+standing) | 0.97 | {1: 0.9622641509433962, 2: 0.9523809523809523, 3: 1.0} |
| random_forest | all | empty vs occupied | 0.65 | {1: 0.6698113207547169, 2: 0.5904761904761905, 3: 0.7096774193548387} |
| random_forest | all | 3-class | 0.67 | {1: 0.7169811320754716, 2: 0.6666666666666666, 3: 0.6344086021505376} |
| random_forest | motion-only | moving vs still (empty+standing) | 0.96 | {1: 0.9716981132075472, 2: 0.9428571428571428, 3: 0.978494623655914} |
| random_forest | motion-only | empty vs occupied | 0.53 | {1: 0.660377358490566, 2: 0.5142857142857142, 3: 0.3870967741935484} |
| random_forest | motion-only | 3-class | 0.57 | {1: 0.660377358490566, 2: 0.5714285714285714, 3: 0.4731182795698925} |

### Confusion matrices (summed over the 3 held-out folds)

**logreg|all|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 201 | 1 |
| moving | 5 | 97 |

**logreg|all|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 38 | 63 |
| occupied | 61 | 142 |

**logreg|all|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 47 | 50 | 4 |
| standing | 60 | 41 | 0 |
| walking | 5 | 1 | 96 |

**logreg|motion-only|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 197 | 5 |
| moving | 6 | 96 |

**logreg|motion-only|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 17 | 84 |
| occupied | 67 | 136 |

**logreg|motion-only|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 28 | 65 | 8 |
| standing | 52 | 49 | 0 |
| walking | 5 | 0 | 97 |

**random_forest|all|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 199 | 3 |
| moving | 6 | 96 |

**random_forest|all|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 36 | 65 |
| occupied | 40 | 163 |

**random_forest|all|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 62 | 37 | 2 |
| standing | 56 | 43 | 2 |
| walking | 1 | 1 | 100 |

**random_forest|motion-only|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 196 | 6 |
| moving | 5 | 97 |

**random_forest|motion-only|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 26 | 75 |
| occupied | 69 | 134 |

**random_forest|motion-only|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 49 | 46 | 6 |
| standing | 72 | 29 | 0 |
| walking | 6 | 0 | 96 |

## 3. Saved models (random forest, motion-only features, trained on all 3 trials)

- `models/csi_motion_model.joblib` labels ['moving', 'still']. Importances: wander 0.37, espectre_var 0.20, jitter 0.19, sc_cv_mean 0.09, sc_cv_p90 0.07, team_change 0.03, turb_rel_iqr 0.02, turb_mean 0.02, turb_lag1_autocorr 0.01

- `models/csi_3class_model.joblib` labels ['empty', 'standing', 'walking']. Importances: wander 0.24, sc_cv_p90 0.19, espectre_var 0.14, jitter 0.13, sc_cv_mean 0.11, turb_mean 0.07, team_change 0.04, turb_rel_iqr 0.04, turb_lag1_autocorr 0.03
