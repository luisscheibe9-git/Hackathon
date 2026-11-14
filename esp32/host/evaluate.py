#!/usr/bin/env python3
"""Honest numbers for the recorded dataset (esp32/data/haven_dataset.npz).

  python host/evaluate.py

- test accuracy: trained on the training session, scored on the separately recorded test session,
  judged by the camera labels (never on windows sampled from the training recordings)
- leave-one-round-out accuracy inside the training session
- per class, confusion table, each link alone, and a "motion only" baseline
Same model as the live server: k-nearest neighbours (k = 7) on standardised features.
Writes esp32/data/model_metrics.json (the same file the server writes after each recording).
"""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import DATASET, N_SC, predict, training_label  # noqa: E402

if __name__ == "__main__":
    if not os.path.exists(DATASET):
        sys.exit("no data/haven_dataset.npz yet: record training and test sessions on /train.html")
    d = np.load(DATASET, allow_pickle=False)
    X = d["X"].astype(np.float64)
    y = np.array([training_label(str(c), str(p)) for c, p in zip(d["cam"], d["prompt"])], dtype=object)
    sess, rnd, ids = d["sess"].astype(str), d["rnd"], [str(i) for i in d["ids"]]
    ok = y != ""
    tr, te = ok & (sess == "train"), ok & (sess == "test")
    print(f"links: {', '.join(ids)}")
    print(f"windows: {len(y)} recorded, {int((~ok).sum())} dropped (camera label not allowed by the prompt)")
    for name, m in (("training", tr), ("test", te)):
        print(f"{name}: {int(m.sum())} ·", ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(y[m].tolist()).items())))
    if tr.sum() < 10:
        sys.exit("\nnot enough training windows yet")
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
    Z = (X - mu) / sd
    labels = sorted(set(y[tr].tolist()))
    rounds = sorted(set(rnd[tr].tolist()))
    if len(rounds) >= 2:
        hits = []
        for r in rounds:
            a, b = tr & (rnd != r), tr & (rnd == r)
            if len(set(y[a])) >= 2 and b.any():
                hits += list(predict(Z[a], y[a], Z[b]) == y[b])
        print(f"\nleave-one-round-out (training session, {len(rounds)} rounds): {100 * np.mean(hits):.1f}%")
    if not te.any():
        sys.exit("\nrecord a test session for the honest score")
    p = predict(Z[tr], y[tr], Z[te])
    acc = float((p == y[te]).mean())
    print(f"\nTEST SESSION: {100 * acc:.1f}%   (guessing: {100 / len(labels):.1f}%, {int(te.sum())} windows)\n")
    w = max(len(l) for l in labels)
    print(" " * (w + 2) + "  ".join(l[:7].rjust(7) for l in labels) + "   correct")
    for l in labels:
        m = y[te] == l
        if m.any():
            print(f"{l:>{w}}  " + "  ".join(str(int(((p == q) & m).sum())).rjust(7) for q in labels) + f"   {100 * (p[m] == l).mean():5.0f}%")
    print("(rows: camera label · columns: WiFi prediction)")
    F = X.shape[1] // len(ids)
    cols = lambda L: np.concatenate([np.arange(i * F, (i + 1) * F) for i in L])
    print("\neach link alone:")
    for i, k in enumerate(ids):
        print(f"  {k}: {100 * (predict(Z[tr][:, cols([i])], y[tr], Z[te][:, cols([i])]) == y[te]).mean():.0f}%")
    R = [i for i, k in enumerate(ids) if k.startswith("R>")]
    B = [i for i, k in enumerate(ids) if not k.startswith("R>")]
    if R and B:
        for name, L in (("router links only", R), ("board-to-board only", B)):
            print(f"  {name}: {100 * (predict(Z[tr][:, cols(L)], y[tr], Z[te][:, cols(L)]) == y[te]).mean():.1f}%")
    motion = np.concatenate([np.arange(i * F + N_SC, (i + 1) * F) for i in range(len(ids))])
    pm = predict(Z[tr][:, motion], y[tr], Z[te][:, motion])
    print(f"\nmotion only (no subcarrier shape): {100 * (pm == y[te]).mean():.1f}%")
