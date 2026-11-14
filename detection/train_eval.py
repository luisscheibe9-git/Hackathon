"""Leave-one-trial-out evaluation of motion scores and a small learned classifier, then
train the final model on all trials and save it.

    python detection/train_eval.py                       # default recording
    python detection/train_eval.py --csv data/other.csv  # another Measure-CsiMotion CSV

Writes detection/results/loto_results_<win>s.md (+ .json) and detection/models/*.joblib.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from csi import load_recording  # noqa: E402
from features import FEATURE_NAMES, window_features, windows  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STAGES = ["empty", "standing", "walking"]
# Features that only describe *change* inside the window. The others (absolute amplitude
# level, RSSI) can pick up slow drift between recording stages, which would not generalise.
MOTION_ONLY = ["team_change", "espectre_var", "wander", "jitter", "turb_mean",
               "turb_lag1_autocorr", "turb_rel_iqr", "sc_cv_mean", "sc_cv_p90"]
SCORES = ["team_change", "espectre_var", "jitter", "wander"]


def build_dataset(csv_path, win_s, step_s, trim_s):
    X, y, trial = [], [], []
    for seg in load_recording(csv_path):
        keep = seg["t_s"] >= seg["t_s"][0] + trim_s  # drop the settle-in second
        t, amp, rssi = seg["t_s"][keep], seg["amp"][keep], seg["rssi"][keep]
        for idx in windows(t, win_s, step_s):
            X.append(window_features(amp[idx], rssi[idx]))
            y.append(seg["stage"])
            trial.append(seg["trial"])
    return np.array(X), np.array(y), np.array(trial)


def fit_threshold(score, positive):
    """Pick the threshold (and direction) that maximises balanced accuracy on train."""
    best = (-1, 0.0, 1)
    for thr in np.unique(score):
        for sign in (1, -1):
            pred = sign * score > sign * thr
            tpr = pred[positive].mean() if positive.any() else 0
            tnr = (~pred[~positive]).mean() if (~positive).any() else 0
            bal = (tpr + tnr) / 2
            if bal > best[0]:
                best = (bal, thr, sign)
    return best[1], best[2]


def cm_to_md(cm, labels):
    head = "| true \\ pred | " + " | ".join(labels) + " |\n|---|" + "---|" * len(labels) + "\n"
    rows = "".join(f"| {lab} | " + " | ".join(str(v) for v in row) + " |\n" for lab, row in zip(labels, cm))
    return head + rows


def make_models():
    return {
        "logreg": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)),
        "random_forest": lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=0),
    }


def loto(X, y, trial, labels, model_fn):
    preds = np.empty_like(y)
    per_trial = {}
    for t in np.unique(trial):
        tr, te = trial != t, trial == t
        m = model_fn().fit(X[tr], y[tr])
        preds[te] = m.predict(X[te])
        per_trial[int(t)] = float((preds[te] == y[te]).mean())
    acc = float((preds == y).mean())
    return acc, per_trial, confusion_matrix(y, preds, labels=labels)


def loto_threshold(score, positive, trial):
    pred = np.zeros_like(positive)
    per_trial = {}
    for t in np.unique(trial):
        tr, te = trial != t, trial == t
        thr, sign = fit_threshold(score[tr], positive[tr])
        pred[te] = sign * score[te] > sign * thr
        per_trial[int(t)] = float((pred[te] == positive[te]).mean())
    return float((pred == positive).mean()), per_trial, confusion_matrix(positive, pred, labels=[False, True])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data" / "csi-motion-20261114-105805.csv"))
    ap.add_argument("--win", type=float, default=1.0, help="window length in seconds")
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--trim", type=float, default=1.0, help="seconds dropped at start of each stage")
    args = ap.parse_args()

    X, y, trial = build_dataset(args.csv, args.win, args.step, args.trim)
    fi = {n: i for i, n in enumerate(FEATURE_NAMES)}
    mo = [fi[n] for n in MOTION_ONLY]
    res = {"csv": Path(args.csv).name, "win_s": args.win, "step_s": args.step, "trim_s": args.trim,
           "n_windows": {s: int((y == s).sum()) for s in STAGES}, "thresholds": {}, "learned": {}}
    md = [f"# Leave-one-trial-out results\n",
          f"Recording `{res['csv']}`, one receiver, one room. Windows {args.win:g} s, step {args.step:g} s, "
          f"first {args.trim:g} s of each stage dropped. Windows per class: {res['n_windows']}. "
          "Each fold trains on 2 trials and tests on the third (3 folds). Overlapping windows "
          "never cross the train/test split because splits are by trial.\n"]

    # ---- 1. hand-made scores with a threshold fitted on the 2 training trials ----------
    tasks = {"motion (walking vs empty+standing)": y == "walking",
             "occupied (walking+standing vs empty)": y != "empty"}
    md.append("## 1. Threshold on a single motion score (threshold fitted on training trials)\n")
    md.append("| score | task | LOTO acc | per held-out trial |\n|---|---|---|---|\n")
    for s in SCORES:
        for tname, pos in tasks.items():
            acc, per, cm = loto_threshold(X[:, fi[s]], pos, trial)
            res["thresholds"][f"{s}|{tname}"] = {"acc": acc, "per_trial": per, "cm": cm.tolist()}
            md.append(f"| {s} | {tname} | {acc:.2f} | {per} |\n")
    md.append("\nPer-class medians of each score (all trials):\n\n| score | " + " | ".join(STAGES) + " |\n|---|---|---|---|\n")
    for s in SCORES:
        md.append(f"| {s} | " + " | ".join(f"{np.median(X[y == c, fi[s]]):.4g}" for c in STAGES) + " |\n")

    # ---- 2. learned classifiers -----------------------------------------------------
    md.append("\n## 2. Learned classifiers on window features\n")
    md.append("| model | features | task | LOTO acc | per held-out trial |\n|---|---|---|---|---|\n")
    cms = []
    yb = np.where(y == "empty", "empty", "occupied")
    ym = np.where(y == "walking", "moving", "still")
    for mname, mfn in make_models().items():
        for fset_name, cols in (("all", list(range(len(FEATURE_NAMES)))), ("motion-only", mo)):
            for tname, yy, labels in (("moving vs still (empty+standing)", ym, ["still", "moving"]),
                                      ("empty vs occupied", yb, ["empty", "occupied"]),
                                      ("3-class", y, STAGES)):
                acc, per, cm = loto(X[:, cols], yy, trial, labels, mfn)
                key = f"{mname}|{fset_name}|{tname}"
                res["learned"][key] = {"acc": acc, "per_trial": per, "cm": cm.tolist(), "labels": labels}
                md.append(f"| {mname} | {fset_name} | {tname} | {acc:.2f} | {per} |\n")
                cms.append((key, cm, labels))
    md.append("\n### Confusion matrices (summed over the 3 held-out folds)\n")
    for key, cm, labels in cms:
        md.append(f"\n**{key}**\n\n" + cm_to_md(cm, labels))

    # ---- 3. final models: random forest, motion-only features, trained on all trials ---
    (HERE / "models").mkdir(exist_ok=True)
    md.append("\n## 3. Saved models (random forest, motion-only features, trained on all 3 trials)\n")
    for fname, yy in (("csi_motion_model.joblib", ym), ("csi_3class_model.joblib", y)):
        final = make_models()["random_forest"]().fit(X[:, mo], yy)
        imp = sorted(zip(MOTION_ONLY, final.feature_importances_), key=lambda p: -p[1])
        md.append(f"\n- `models/{fname}` labels {[str(c) for c in final.classes_]}. Importances: "
                  + ", ".join(f"{n} {v:.2f}" for n, v in imp) + "\n")
        joblib.dump({"model": final, "features": MOTION_ONLY, "labels": [str(c) for c in final.classes_],
                     "win_s": args.win, "trained_on": res["csv"]}, HERE / "models" / fname)

    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"loto_results_{args.win:g}s.md").write_text("".join(md), encoding="utf-8")
    (HERE / "results" / f"loto_results_{args.win:g}s.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("".join(md))


if __name__ == "__main__":
    main()
