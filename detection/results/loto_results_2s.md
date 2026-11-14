# Leave-one-trial-out results
Recording `csi-motion-20261114-105805.csv`, one receiver, one room. Windows 2 s, step 0.5 s, first 1 s of each stage dropped. Windows per class: {'empty': 102, 'standing': 102, 'walking': 101}. Each fold trains on 2 trials and tests on the third (3 folds). Overlapping windows never cross the train/test split because splits are by trial.
## 1. Threshold on a single motion score (threshold fitted on training trials)
| score | task | LOTO acc | per held-out trial |
|---|---|---|---|
| team_change | motion (walking vs empty+standing) | 0.82 | {1: 0.8431372549019608, 2: 0.8712871287128713, 3: 0.7352941176470589} |
| team_change | occupied (walking+standing vs empty) | 0.66 | {1: 0.7254901960784313, 2: 0.5742574257425742, 3: 0.6862745098039216} |
| espectre_var | motion (walking vs empty+standing) | 0.89 | {1: 0.9607843137254902, 2: 0.8712871287128713, 3: 0.8431372549019608} |
| espectre_var | occupied (walking+standing vs empty) | 0.58 | {1: 0.6568627450980392, 2: 0.5247524752475248, 3: 0.5588235294117647} |
| jitter | motion (walking vs empty+standing) | 0.88 | {1: 0.9313725490196079, 2: 0.9306930693069307, 3: 0.7843137254901961} |
| jitter | occupied (walking+standing vs empty) | 0.65 | {1: 0.5980392156862745, 2: 0.594059405940594, 3: 0.7549019607843137} |
| wander | motion (walking vs empty+standing) | 0.97 | {1: 0.9705882352941176, 2: 0.9603960396039604, 3: 0.9803921568627451} |
| wander | occupied (walking+standing vs empty) | 0.61 | {1: 0.6372549019607843, 2: 0.5445544554455446, 3: 0.6470588235294118} |

Per-class medians of each score (all trials):

| score | empty | standing | walking |
|---|---|---|---|
| team_change | 0.09655 | 0.09277 | 0.1977 |
| espectre_var | 9.715 | 8.097 | 33.63 |
| jitter | 0.04664 | 0.04451 | 0.104 |
| wander | 0.0227 | 0.02254 | 0.05526 |

## 2. Learned classifiers on window features
| model | features | task | LOTO acc | per held-out trial |
|---|---|---|---|---|
| logreg | all | moving vs still (empty+standing) | 0.99 | {1: 1.0, 2: 0.9702970297029703, 3: 0.9901960784313726} |
| logreg | all | empty vs occupied | 0.60 | {1: 0.6862745098039216, 2: 0.5841584158415841, 3: 0.5196078431372549} |
| logreg | all | 3-class | 0.61 | {1: 0.7058823529411765, 2: 0.594059405940594, 3: 0.5392156862745098} |
| logreg | motion-only | moving vs still (empty+standing) | 0.95 | {1: 0.9803921568627451, 2: 0.9603960396039604, 3: 0.9215686274509803} |
| logreg | motion-only | empty vs occupied | 0.55 | {1: 0.6568627450980392, 2: 0.5445544554455446, 3: 0.45098039215686275} |
| logreg | motion-only | 3-class | 0.58 | {1: 0.7058823529411765, 2: 0.6138613861386139, 3: 0.4215686274509804} |
| random_forest | all | moving vs still (empty+standing) | 0.98 | {1: 0.9705882352941176, 2: 0.9801980198019802, 3: 0.9901960784313726} |
| random_forest | all | empty vs occupied | 0.71 | {1: 0.7254901960784313, 2: 0.6138613861386139, 3: 0.803921568627451} |
| random_forest | all | 3-class | 0.67 | {1: 0.7254901960784313, 2: 0.6633663366336634, 3: 0.6176470588235294} |
| random_forest | motion-only | moving vs still (empty+standing) | 0.97 | {1: 0.9509803921568627, 2: 0.9801980198019802, 3: 0.9901960784313726} |
| random_forest | motion-only | empty vs occupied | 0.54 | {1: 0.6568627450980392, 2: 0.4752475247524752, 3: 0.4803921568627451} |
| random_forest | motion-only | 3-class | 0.61 | {1: 0.6666666666666666, 2: 0.5643564356435643, 3: 0.5882352941176471} |

### Confusion matrices (summed over the 3 held-out folds)

**logreg|all|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 204 | 0 |
| moving | 4 | 97 |

**logreg|all|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 40 | 62 |
| occupied | 61 | 142 |

**logreg|all|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 52 | 48 | 2 |
| standing | 61 | 41 | 0 |
| walking | 7 | 0 | 94 |

**logreg|motion-only|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 195 | 9 |
| moving | 5 | 96 |

**logreg|motion-only|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 30 | 72 |
| occupied | 65 | 138 |

**logreg|motion-only|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 38 | 57 | 7 |
| standing | 59 | 42 | 1 |
| walking | 4 | 0 | 97 |

**random_forest|all|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 202 | 2 |
| moving | 4 | 97 |

**random_forest|all|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 52 | 50 |
| occupied | 37 | 166 |

**random_forest|all|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 70 | 28 | 4 |
| standing | 64 | 38 | 0 |
| walking | 5 | 0 | 96 |

**random_forest|motion-only|moving vs still (empty+standing)**

| true \ pred | still | moving |
|---|---|---|
| still | 201 | 3 |
| moving | 5 | 96 |

**random_forest|motion-only|empty vs occupied**

| true \ pred | empty | occupied |
|---|---|---|
| empty | 34 | 68 |
| occupied | 73 | 130 |

**random_forest|motion-only|3-class**

| true \ pred | empty | standing | walking |
|---|---|---|---|
| empty | 58 | 39 | 5 |
| standing | 71 | 31 | 0 |
| walking | 5 | 0 | 96 |

## 3. Saved models (random forest, motion-only features, trained on all 3 trials)

- `models/csi_motion_model.joblib` labels [np.str_('moving'), np.str_('still')]. Importances: wander 0.37, espectre_var 0.22, jitter 0.15, sc_cv_mean 0.12, team_change 0.05, turb_rel_iqr 0.03, sc_cv_p90 0.03, turb_lag1_autocorr 0.01, turb_mean 0.01

- `models/csi_3class_model.joblib` labels [np.str_('empty'), np.str_('standing'), np.str_('walking')]. Importances: wander 0.24, sc_cv_p90 0.18, espectre_var 0.15, jitter 0.13, sc_cv_mean 0.11, turb_mean 0.08, team_change 0.05, turb_rel_iqr 0.04, turb_lag1_autocorr 0.03
