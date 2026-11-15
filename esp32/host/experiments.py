#!/usr/bin/env python3
"""Offline model experiments on the saved raw CSI logs (no boards needed, live system untouched).

    python host/experiments.py            # needs numpy + scikit-learn (system Python has both)

Uses the 4-class run on the current board positions (3 training rounds + 1 test round, Nov 14
~17:08-17:19). Labels come from the guided prompt (first SETTLE_S s of each step skipped).
For every variant (window length x features x model x paths) it reports:
  LORO   leave-one-round-out on the 3 training rounds (train 2, score the 3rd), balanced accuracy
  TEST   trained on all 3 training rounds, scored on the separate test round, balanced accuracy
  lying  recall of lying windows on the test round
  falseA non-lying steps (test + LORO) whose 3 s-smoothed prediction stays "lying" >= 3 s (= false alert)
  missA  lying steps (test + LORO) that never reach a 3 s smoothed lying run (= missed alert)
Writes data/experiments.md.
"""
import csv
import glob
import os
import sys
from collections import defaultdict

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RAW = os.path.join(DATA, "raw")
TRAIN = ["raw-train-r1-20261114-170855.csv", "raw-train-r2-20261114-171131.csv", "raw-train-r3-20261114-171407.csv"]
TEST = ["raw-test-r1-20261114-171705.csv"]
if os.environ.get("EXP_TRAIN"):                     # e.g. EXP_TRAIN="a.csv b.csv c.csv" EXP_TEST="t.csv"
    TRAIN, TEST = os.environ["EXP_TRAIN"].split(), os.environ["EXP_TEST"].split()
LABELS = ["empty", "standing", "walking", "lying"]
VALID = np.r_[1:27, 38:64]
SETTLE_S, HOP = 2.0, 0.5
# board MACs (config.yaml): gateway #1, #2, #3. RELAY = CSI of #1's frames at the reporting board; PEER = #2's frames at #3
MAC2 = "6809479f27f4"
MAC3 = "6809471a80ac"


def link_of(kind, mac):
    if kind == "RELAY":
        return {"6809479f27f4": "1>2", "6809471a80ac": "1>3"}.get(mac)
    if kind == "PEER" and mac == MAC3:
        return "2>3"
    return None


def load_raw(name):
    """-> frames {link: (t[], amp[n,52])}, steps [(label, start, end)]"""
    fr = defaultdict(lambda: ([], []))
    steps, cur = [], None
    with open(os.path.join(RAW, name), newline="") as fh:
        for r in csv.DictReader(fh):
            t = float(r["t"])
            paused = r["paused"] == "1"
            if not paused and (cur is None or cur[0] != r["prompt"] or cur[3]):
                if cur and not cur[3]:
                    steps.append((cur[0], cur[1], cur[2]))
                cur = [r["prompt"], t, t, False]
            if cur and not paused:
                cur[2] = t
            if paused and cur and not cur[3]:
                steps.append((cur[0], cur[1], cur[2])); cur[3] = True
            k = link_of(r["kind"], r["receiver_mac"])
            if not k:
                continue
            b = bytes.fromhex(r["lltf_hex_centered"])
            b = b[64:] + b[:64]                               # centred -> 0..31,-32..-1 (as server.py)
            iq = np.frombuffer(b, np.int8).astype(np.float32)
            amp = np.hypot(iq[0::2], iq[1::2])[VALID]
            amp = amp / (amp.mean() + 1e-6) * 20.0
            fr[k][0].append(t); fr[k][1].append(amp)
    if cur and not cur[3]:
        steps.append((cur[0], cur[1], cur[2]))
    frames = {k: (np.array(v[0]), np.array(v[1])) for k, v in fr.items()}
    return frames, [s for s in steps if s[0] in LABELS]


def feats(w, kind):
    """w: (n, 52) amplitudes of one link in one window."""
    mean, std = w.mean(0), w.std(0)
    mad = np.abs(np.diff(w, axis=0)).mean(0)
    if kind == "haven":                 # what server.py uses today
        return np.concatenate([mean, std, mad])
    if kind == "motion":                # drop the drift-prone static shape
        return np.concatenate([std / (mean + 1e-3), mad / (mean + 1e-3)])
    if kind == "haven+summary":         # + a few robust per-link scalars
        cv = std / (mean + 1e-3)
        turb = w.std(1) / (w.mean(1) + 1e-3)
        s = [cv.mean(), cv.max(), np.median(cv), (mad / (mean + 1e-3)).mean(), turb.mean(), turb.std(),
             np.percentile(w, 90) - np.percentile(w, 10)]
        return np.concatenate([mean, std, mad, s])
    if kind == "shape-smooth":          # coarse shape (8 bands) + motion: fewer, more robust numbers
        bands = np.array_split(np.arange(52), 8)
        m8 = np.array([mean[b].mean() for b in bands]); s8 = np.array([std[b].mean() for b in bands])
        d8 = np.array([mad[b].mean() for b in bands])
        return np.concatenate([m8, s8, d8, [std.mean() / (mean.mean() + 1e-3)]])
    raise ValueError(kind)


def windows(frames, steps, links, win, kind, rnd):
    X, y, take, t = [], [], [], []
    for si, (lab, a, b) in enumerate(steps):
        te = a + SETTLE_S + win
        while te <= b:
            parts = []
            for k in links:
                tt, aa = frames[k]
                m = (tt > te - win) & (tt <= te)
                if m.sum() < 4:
                    parts = None; break
                parts.append(feats(aa[m], kind))
            if parts is not None:
                X.append(np.concatenate(parts)); y.append(lab); take.append(rnd * 100 + si); t.append(te)
            te += HOP
    return np.array(X), np.array(y), np.array(take), np.array(t)


def balanced_idx(y, cap=2.0, seed=0):
    labs, cnt = np.unique(y, return_counts=True)
    lim = int(cap * cnt.min()); rng = np.random.default_rng(seed); keep = []
    for l in labs:
        i = np.where(y == l)[0]
        keep.append(i if len(i) <= lim else rng.choice(i, lim, replace=False))
    return np.sort(np.concatenate(keep))


MODELS = {
    "kNN7 (live)": lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(7)),
    "ExtraTrees": lambda: ExtraTreesClassifier(400, min_samples_leaf=2, random_state=0, n_jobs=-1),
    "SVM-RBF": lambda: make_pipeline(StandardScaler(), SVC(C=3, gamma="scale", probability=True, random_state=0)),
    "LogReg": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000)),
    "MLP (neural net)": lambda: make_pipeline(StandardScaler(), MLPClassifier((64, 32), alpha=1e-2, max_iter=1500, early_stopping=True, random_state=0)),
}


def fit_predict(mk, Xtr, ytr, Xte):
    i = balanced_idx(ytr)
    m = mk().fit(Xtr[i], ytr[i])
    P = m.predict_proba(Xte)
    cls = list(m.classes_)
    P = np.column_stack([P[:, cls.index(c)] if c in cls else np.zeros(len(Xte)) for c in LABELS])
    return P


def alerts(P, y, take, t):
    """false alerts / missed alerts per step with the server's 3 s smoothing + 3 s lying rule."""
    fa = ma = nl = ly = 0
    li = LABELS.index("lying")
    for k in np.unique(take):
        i = np.where(take == k)[0]; i = i[np.argsort(t[i])]
        best = [int(P[i[max(0, j - 5):j + 1]].mean(0).argmax()) for j in range(len(i))]
        run = mx = 0
        for b in best:
            run = run + 1 if b == li else 0; mx = max(mx, run)
        alert = mx * HOP >= 3.0
        if y[i][0] == "lying":
            ly += 1; ma += not alert
        else:
            nl += 1; fa += alert
    return fa, nl, ma, ly


def bal_acc(y, p):
    return float(np.mean([np.mean(p[y == c] == c) for c in LABELS if (y == c).any()]))


def main():
    rounds = [load_raw(f) for f in TRAIN]
    test = load_raw(TEST[0])
    all_links = sorted(set.intersection(*[set(r[0]) for r in rounds + [test]]))
    print("links", all_links, "| steps per round", [len(r[1]) for r in rounds], len(test[1]), flush=True)
    rows = []
    grid = []
    for win in (1.0, 2.0, 3.0):
        for kind in ("haven", "motion", "haven+summary", "shape-smooth"):
            grid.append((win, kind, tuple(all_links)))
    for pair in (("1>2", "1>3"), ("1>2", "2>3"), ("1>3", "2>3")):
        grid.append((2.0, "haven", pair))
    for win, kind, links in grid:
        R = [windows(f, s, links, win, kind, n) for n, (f, s) in enumerate(rounds, 1)]
        Te = windows(test[0], test[1], links, win, kind, 9)
        for mname, mk in MODELS.items():
            if len(links) < 3 and mname != "kNN7 (live)":
                continue
            # LORO
            yl, pl, Pl, kl, tl = [], [], [], [], []
            for h in range(3):
                Xtr = np.concatenate([R[j][0] for j in range(3) if j != h]); ytr = np.concatenate([R[j][1] for j in range(3) if j != h])
                P = fit_predict(mk, Xtr, ytr, R[h][0])
                yl.append(R[h][1]); Pl.append(P); kl.append(R[h][2]); tl.append(R[h][3])
            yl, Pl, kl, tl = map(np.concatenate, (yl, Pl, kl, tl))
            pl = np.array(LABELS)[Pl.argmax(1)]
            # train all 3 -> test
            Xtr = np.concatenate([r[0] for r in R]); ytr = np.concatenate([r[1] for r in R])
            P = fit_predict(mk, Xtr, ytr, Te[0]); pt = np.array(LABELS)[P.argmax(1)]
            fa1, nl1, ma1, ly1 = alerts(P, Te[1], Te[2], Te[3])
            fa2, nl2, ma2, ly2 = alerts(Pl, yl, kl, tl)
            row = dict(win=win, feat=kind, links="+".join(links), model=mname,
                       loro=bal_acc(yl, pl), test=bal_acc(Te[1], pt), lying=float(np.mean(pt[Te[1] == "lying"] == "lying")),
                       per={c: float(np.mean(pt[Te[1] == c] == c)) for c in LABELS},
                       fa=fa1 + fa2, nl=nl1 + nl2, ma=ma1 + ma2, ly=ly1 + ly2)
            rows.append(row)
            print(f"{win:.0f}s {kind:14s} {row['links']:12s} {mname:17s} LORO {row['loro']:.2f} TEST {row['test']:.2f} "
                  f"lying {row['lying']:.2f} falseA {row['fa']}/{row['nl']} missA {row['ma']}/{row['ly']}", flush=True)

    # rank: fewest false alerts, then fewest missed alerts, then mean of LORO and TEST
    rows.sort(key=lambda r: (r["fa"], r["ma"], -(r["loro"] + r["test"]) / 2))
    base = next(r for r in rows if r["win"] == 2.0 and r["feat"] == "haven" and r["model"] == "kNN7 (live)" and r["links"].count("+") == 2)
    out = ["# Offline model experiments (Nov 14, current board positions)\n\n",
           "Data: 3 training rounds + 1 separate test round of the 4-class routine, labelled by the guided prompt "
           f"(first {SETTLE_S:g} s of each step skipped). Balanced training (no class above 2x the smallest).\n\n",
           "- **LORO**: balanced accuracy, train on 2 training rounds, score the 3rd (3 folds).\n"
           "- **TEST**: balanced accuracy, train on all 3, score the separate test round.\n"
           "- **false alerts / missed alerts**: per step, using the live rule (3 s smoothing, alert after 3 s lying), over LORO folds + test.\n\n",
           f"Current live setup (2 s, Haven features, kNN7, all paths): LORO {base['loro']:.2f}, TEST {base['test']:.2f}, "
           f"false alerts {base['fa']}/{base['nl']}, missed alerts {base['ma']}/{base['ly']}.\n\n",
           "| rank | window | features | paths | model | LORO | TEST | lying recall (test) | false alerts | missed alerts |\n|---|---|---|---|---|---|---|---|---|---|\n"]
    for i, r in enumerate(rows, 1):
        out.append(f"| {i} | {r['win']:.0f} s | {r['feat']} | {r['links']} | {r['model']} | {r['loro']:.2f} | {r['test']:.2f} | "
                   f"{r['lying']:.2f} | {r['fa']}/{r['nl']} | {r['ma']}/{r['ly']} |\n")
    open(os.path.join(DATA, os.environ.get("EXP_OUT", "experiments.md")), "w", encoding="utf-8").write("".join(out))
    print("\nwrote data/experiments.md")


if __name__ == "__main__":
    main()
