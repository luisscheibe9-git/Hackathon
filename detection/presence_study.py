"""Can anything separate an EMPTY room from a person STANDING STILL in our recording?

Tests, all leave-one-trial-out (threshold / model fitted on 2 trials, scored on the 3rd):
  A. breathing-band features on long windows: per-subcarrier power in 0.1-0.5 Hz relative
     to 0.1-3 Hz, on 6 s windows (amplitude resampled to a uniform 12 Hz grid);
  B. same-session calibration: profile distance (1 - correlation of the window's mean
     amplitude profile) to THAT trial's first 6 s of empty room, as the live system would
     calibrate right before use. Only empty windows after the calibration span are scored.
     Caveat: standing was recorded ~40 s after empty, so drift over time is a confound.
  C. a logistic regression on A + B + the motion features.

    python detection/presence_study.py
Writes detection/results/presence_study.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from csi import load_recording  # noqa: E402
from features import espcsi_wander_jitter, espectre_score  # noqa: E402

FS = 12.0
WIN_S, STEP_S, CAL_S = 6.0, 1.0, 6.0


def resample(t, amp, fs=FS):
    grid = np.arange(t[0], t[-1], 1 / fs)
    return grid, np.stack([np.interp(grid, t, amp[:, k]) for k in range(amp.shape[1])], axis=1)


def breathing_ratio(win, fs=FS):
    x = win - win.mean(axis=0)
    x = x * np.hanning(len(x))[:, None]
    p = np.abs(np.fft.rfft(x, axis=0)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    br = p[(f >= 0.1) & (f <= 0.5)].sum(0) / (p[(f >= 0.1) & (f <= 3.0)].sum(0) + 1e-9)
    return float(np.median(br)), float(np.percentile(br, 90))


def profile_dist(a, b):
    a, b = a - a.mean(), b - b.mean()
    return float(1 - a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def build():
    segs = {(s["trial"], s["stage"]): s for s in load_recording(HERE.parent / "data" / "csi-motion-20261114-105805.csv")}
    rows = []
    for (trial, stage), s in segs.items():
        if stage == "walking":
            continue
        cal_t, cal_amp = resample(*[segs[(trial, "empty")][k] for k in ("t_s", "amp")])
        cal_profile = cal_amp[(cal_t >= cal_t[0] + 1) & (cal_t < cal_t[0] + 1 + CAL_S)].mean(0)
        g, amp = resample(s["t_s"], s["amp"])
        start = g[0] + (1 + CAL_S if stage == "empty" else 1.0)  # empty: score only after calibration span
        while start + WIN_S <= g[-1]:
            w = amp[(g >= start) & (g < start + WIN_S)]
            bmed, b90 = breathing_ratio(w)
            wander, jitter = espcsi_wander_jitter(w)
            rows.append((trial, stage, bmed, b90, profile_dist(w.mean(0), cal_profile), wander, jitter, espectre_score(w)))
            start += STEP_S
    return rows


NAMES = ["breath_ratio_med", "breath_ratio_p90", "dist_to_session_empty", "wander", "jitter", "espectre_var"]


def bacc(pred, pos):
    """Balanced accuracy: mean of per-class recall (classes are imbalanced here)."""
    return round(float((pred[pos].mean() + (~pred[~pos]).mean()) / 2), 2)


def loto_threshold(x, pos, trial):
    pred = np.zeros_like(pos)
    per = {}
    for t in np.unique(trial):
        tr, te = trial != t, trial == t
        best = (-1, 0, 1)
        for thr in np.unique(x[tr]):
            for sg in (1, -1):
                p = sg * x[tr] > sg * thr
                bal = (p[pos[tr]].mean() + (~p[~pos[tr]]).mean()) / 2
                best = max(best, (bal, thr, sg))
        pred[te] = best[2] * x[te] > best[2] * best[1]
        per[int(t)] = bacc(pred[te], pos[te])
    return bacc(pred, pos), per


def main():
    rows = build()
    trial = np.array([r[0] for r in rows])
    pos = np.array([r[1] == "standing" for r in rows])
    X = np.array([r[2:] for r in rows], dtype=float)
    md = ["# Empty room vs person standing still\n\n",
          f"{WIN_S:g} s windows, 1 s step, amplitude resampled to {FS:g} Hz. Empty windows: {int((~pos).sum())} "
          f"(only after each trial's calibration span), standing windows: {int(pos.sum())}. "
          "LOTO: threshold/model fitted on 2 trials, scored on the 3rd. Scores are **balanced accuracy** (mean recall of the two classes), chance = 0.5.\n\n",
          "| feature | median empty | median standing | LOTO balanced acc (threshold) | per held-out trial |\n|---|---|---|---|---|\n"]
    for i, n in enumerate(NAMES):
        acc, per = loto_threshold(X[:, i], pos, trial)
        md.append(f"| {n} | {np.median(X[~pos, i]):.4g} | {np.median(X[pos, i]):.4g} | {acc} | {per} |\n")
    md.append("\nPer-trial medians (empty / standing):\n\n| feature | trial 1 | trial 2 | trial 3 |\n|---|---|---|---|\n")
    for i, n in enumerate(NAMES):
        md.append(f"| {n} | " + " | ".join(
            f"{np.median(X[(trial == t) & ~pos, i]):.4g} / {np.median(X[(trial == t) & pos, i]):.4g}" for t in (1, 2, 3)) + " |\n")
    pred = np.zeros_like(pos)
    per = {}
    for t in (1, 2, 3):
        m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X[trial != t], pos[trial != t])
        pred[trial == t] = m.predict(X[trial == t])
        per[t] = bacc(pred[trial == t], pos[trial == t])
    md.append(f"\nLogistic regression on all six features: LOTO balanced acc {bacc(pred, pos)}, per trial {per}.\n")
    md.append("\n**Caveat on dist_to_session_empty:** each trial was recorded empty -> walking -> standing, so the "
              "standing windows are ~40 s further from the calibration than the scored empty windows. The empty-room "
              "profile drifts by a similar amount between trials (empty-vs-empty distance 0.29-0.72 across trials), "
              "so this result can be drift, not the person. It needs an interleaved recording "
              "(empty, stand, empty, stand, ~20 s each, re-checked a few minutes later) before we trust it.\n")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "presence_study.md").write_text("".join(md), encoding="utf-8")
    print("".join(md))


if __name__ == "__main__":
    main()
