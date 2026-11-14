"""Port of the ESP32-WiFi-CSI-Human-Sensing pipeline, run on our recording with
leave-one-trial-out.

Reference: https://github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing
(classic ESP32, Arduino core, presence + movement + 1-D position).
Original code: MIT License, Copyright (c) 2026 Sanaullah Shaheer. The preprocessing
(first-word trim, valid-subcarrier list, EMA smoothing), the Hampel filter, the
180-dim feature vector and the KNN / random-forest presence candidates below follow
their python/preprocessing.py, python/feature_extraction.py and
python/models/baseline_model.py (config.yaml defaults), re-written as plain functions.
Their movement heuristic (python/inference.py MovementDetector: sigmoid of
move_rel_activity around 1.5 x empty-room baseline) is ported too.

What we changed: their window is 64 samples at 60 Hz (~1 s). Our recording is ~12 Hz,
so we test both a time-equivalent window (12 samples ~1 s, stride 2) and their literal
64-sample window (~5 s, stride 8).

    python detection/humansensing_port.py
Writes detection/results/humansensing_port.md (+ .json).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CSV = ROOT / "data" / "csi-motion-20261114-105805.csv"

# config.yaml csi.valid_subcarriers_20mhz, indices AFTER trimming the 4 invalid bytes
VALID = np.r_[0:27, 32:59]
EMA_ALPHA = 0.25
HAMPEL_T = 3.5
BANDS = 4
STAGES = ["empty", "standing", "walking"]


# ---- their preprocessing ---------------------------------------------------------
def frame_amplitude(lltf_hex: str) -> np.ndarray:
    raw = np.frombuffer(bytes.fromhex(lltf_hex), dtype=np.int8)[4:].astype(np.float64)
    return np.hypot(raw[0::2], raw[1::2])[VALID]


def ema(amp: np.ndarray, alpha: float = EMA_ALPHA) -> np.ndarray:
    out = np.empty_like(amp)
    state = amp[0]
    for i, a in enumerate(amp):
        state = alpha * a + (1 - alpha) * state
        out[i] = state
    return out


def hampel(window: np.ndarray, threshold: float = HAMPEL_T) -> np.ndarray:
    med = np.median(window, axis=0, keepdims=True)
    dev = np.abs(window - med)
    mad = np.median(dev, axis=0, keepdims=True) * 1.4826
    return np.where(dev > threshold * np.where(mad > 0, mad, np.inf), med, window)


# ---- their 180-dim feature vector ----------------------------------------------------
def features(window: np.ndarray, rssi: np.ndarray) -> np.ndarray:
    w = hampel(window)
    curve = w.mean(axis=1)
    v = list(w.mean(0)) + list(w.std(0)) + list(np.abs(np.diff(w, axis=0)).mean(0))
    v += [curve.mean(), curve.std(), curve.max() - curve.min(), curve.min(), curve.max()]
    dcurve = np.abs(np.diff(curve))
    slope = np.polyfit(np.arange(len(curve)), curve, 1)[0]
    v += [curve.std(), dcurve.mean(), (curve ** 2).mean(), slope]
    spec = np.abs(np.fft.rfft(curve - curve.mean()))
    spec[0] = 0.0
    edges = np.linspace(0, len(spec), BANDS + 1, dtype=int)
    for i in range(BANDS):
        lo, hi = edges[i], max(edges[i + 1], edges[i] + 1)
        v.append(float((spec[lo:hi] ** 2).sum()))
    v += [rssi.mean(), rssi.std(), rssi[-1]]
    rel = dcurve / (curve[:-1].mean() + 1e-9)
    v += [rel.mean(), rel.max()]
    return np.nan_to_num(np.asarray(v, dtype=np.float64))


N_SUB = len(VALID)
NAMES = ([f"sub_mean_{i}" for i in range(N_SUB)] + [f"sub_std_{i}" for i in range(N_SUB)]
         + [f"sub_diff_{i}" for i in range(N_SUB)]
         + ["agg_mean", "agg_std", "agg_range", "agg_min", "agg_max",
            "temp_std", "temp_mean_abs_diff", "temp_energy", "temp_slope"]
         + [f"spec_band_{i}" for i in range(BANDS)]
         + ["rssi_mean", "rssi_std", "rssi_last", "move_rel_activity", "move_peak_rel_diff"])
REL = NAMES.index("move_rel_activity")


def load_segments(path=CSV):
    segs = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            k = (int(r["trial"]), r["stage"])
            s = segs.setdefault(k, {"amp": [], "rssi": []})
            s["amp"].append(frame_amplitude(r["lltf_hex"]))
            s["rssi"].append(float(r["rssi_dbm"]))
    return {k: (ema(np.array(s["amp"])), np.array(s["rssi"])) for k, s in segs.items()}


def build(segs, win, stride, trim=12):
    X, y, t = [], [], []
    for (trial, stage), (amp, rssi) in segs.items():
        amp, rssi = amp[trim:], rssi[trim:]  # drop ~1 s settle-in (also lets EMA settle)
        for end in range(win, len(amp) + 1, stride):
            X.append(features(amp[end - win:end], rssi[end - win:end]))
            y.append(stage)
            t.append(trial)
    return np.array(X), np.array(y), np.array(t)


# ---- their models --------------------------------------------------------------------
def candidates():
    return {
        "knn": lambda: Pipeline([("scaler", StandardScaler()),
                                 ("knn", KNeighborsClassifier(n_neighbors=7, weights="distance"))]),
        "random_forest": lambda: RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                                        class_weight="balanced", n_jobs=-1, random_state=42),
    }


def movement_heuristic_prob(act, threshold):
    """Their MovementDetector without the cross-window EMA (windows are scored alone)."""
    scale = max(threshold, 1e-6)
    return 1.0 / (1.0 + np.exp(-(act - threshold) / (0.5 * scale)))


def loto(X, y, trial, labels, fit_predict):
    pred = np.empty_like(y)
    per = {}
    for t in np.unique(trial):
        tr, te = trial != t, trial == t
        pred[te] = fit_predict(X[tr], y[tr], X[te])
        per[int(t)] = round(float((pred[te] == y[te]).mean()), 3)
    return round(float((pred == y).mean()), 3), per, confusion_matrix(y, pred, labels=labels).tolist()


def main():
    segs = load_segments()
    res = {}
    md = ["# ESP32-WiFi-CSI-Human-Sensing port: leave-one-trial-out\n\n",
          "Port of github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing (MIT, (c) 2026 Sanaullah Shaheer): "
          "EMA preprocessing, Hampel filter, their 180-dim features, KNN(k=7) and RF(200 trees) candidates, and "
          "their movement heuristic (threshold = 1.5 x mean empty-room move_rel_activity, taken from the training "
          "trials). Folds = held-out trial.\n"]
    for wname, win, stride in (("1 s (12 samples, stride 2)", 12, 2), ("~5 s (their literal 64 samples, stride 8)", 64, 8)):
        X, y, trial = build(segs, win, stride)
        md.append(f"\n## Window {wname}\n\nWindows per class: "
                  + ", ".join(f"{s} {(y == s).sum()}" for s in STAGES) + "\n\n")
        md.append("| method | task | LOTO acc | per held-out trial | confusion (rows=true) |\n|---|---|---|---|---|\n")
        ym = np.where(y == "walking", "moving", "still")
        yb = np.where(y == "empty", "empty", "occupied")
        es = y != "walking"  # empty vs standing only

        def heur(Xtr, ytr, Xte, pos="moving", neg="still", empty_label=None):
            base = Xtr[(ytr == neg) if empty_label is None else (ytr == empty_label), REL].mean()
            return np.where(movement_heuristic_prob(Xte[:, REL], 1.5 * base) >= 0.5, pos, neg)

        acc, per, cm = loto(X, ym, trial, ["still", "moving"], heur)
        res[f"{wname}|heuristic|moving vs still"] = (acc, per, cm)
        md.append(f"| movement heuristic | moving vs still | {acc} | {per} | {cm} |\n")
        for mname, mk in candidates().items():
            fp = lambda Xtr, ytr, Xte, mk=mk: mk().fit(Xtr, ytr).predict(Xte)
            for tname, yy, labels, mask in (("moving vs still", ym, ["still", "moving"], slice(None)),
                                             ("empty vs occupied", yb, ["empty", "occupied"], slice(None)),
                                             ("empty vs standing still", y, ["empty", "standing"], es),
                                             ("3-class", y, STAGES, slice(None))):
                acc, per, cm = loto(X[mask], yy[mask], trial[mask], labels, fp)
                res[f"{wname}|{mname}|{tname}"] = (acc, per, cm)
                md.append(f"| {mname} | {tname} | {acc} | {per} | {cm} |\n")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "humansensing_port.md").write_text("".join(md), encoding="utf-8")
    (HERE / "results" / "humansensing_port.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("".join(md))


if __name__ == "__main__":
    sys.exit(main())
