#!/usr/bin/env python3
"""Rebuild the training dataset from the raw CSI logs, labelled by the guided PROMPT instead of the
camera, and score it on the separate test round.

Why: on Nov 14 the webcam teacher missed or mislabelled many lying moments (about 24% of the test
round's lying time had no confident camera label, so those windows were never stored or scored).
The prompt is reliable once the person has settled, so each step's first SETTLE_S seconds are
skipped (moving into position) and the rest is labelled with the prompt.

    python host/retrain_from_raw.py                    # newest 3 train + 1 test raw logs
    python host/retrain_from_raw.py --save             # also write data/haven_dataset.npz (backs up the old one)
    python host/retrain_from_raw.py --train a.csv b.csv --test c.csv

Uses the same parser, links and features as server.py, so the saved dataset trains the live model.
"""
import argparse
import csv
import glob
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import havenconfig  # noqa: E402
import server  # noqa: E402

SETTLE_S = 2.0
LABELS = ["empty", "standing", "walking", "lying"]


class _Clock:
    now = 0.0


def replay(path, cfg):
    """Feed one raw log through the server's parser with recorded timestamps.
    Returns (windows: list of (t_end, label, take, feature), link ids)."""
    real_time = server.time.time
    server.time.time = lambda: _Clock.now          # Receiver/Link stamp frames with time.time()
    server._last_feat.clear()
    try:
        rx = server.Receiver(cfg)
        out, take, prev_paused, step = [], 0, True, None   # step = (prompt, take, start time)
        next_t = None
        ids = None
        with open(path, newline="") as fh:
            for r in csv.DictReader(fh):
                now = float(r["t"])
                paused = r["paused"] == "1"
                if prev_paused and not paused:
                    take += 1
                    step = (r["prompt"], take, now)
                    next_t = now + SETTLE_S + server.WIN       # first window fully inside the settled step
                if paused:
                    step = None
                # windows are computed as time passes, because each link keeps only ~14 s of frames
                while step and next_t is not None and now >= next_t:
                    ids = ids or (sorted(rx.links) if len(rx.links) >= 3 else None)
                    if ids and step[0] in LABELS:
                        _Clock.now = next_t
                        f = server.feature(rx, ids, next_t)
                        if f is not None:
                            out.append((next_t, step[0], step[1], f))
                    next_t += server.HOP
                prev_paused = paused
                _Clock.now = now
                server.parse_gateway_line(rx, f"{r['kind']},{r['receiver_mac']},{r['rssi_dbm']},{r['lltf_hex_centered']}".encode())
        return out, ids or sorted(rx.links)
    finally:
        server.time.time = real_time


def load(paths, cfg, session):
    X, y, rnd, take, t, ids = [], [], [], [], [], None
    for n, p in enumerate(paths, 1):
        w, ids_p = replay(p, cfg)
        ids = ids or ids_p
        if ids_p != ids:
            raise SystemExit(f"{p}: links {ids_p} differ from {ids}")
        for t_end, lab, tk, f in w:
            X.append(f); y.append(lab); rnd.append(n); take.append(n * 100 + tk); t.append(t_end)
        print(f"{session} {os.path.basename(p)}: {len(w)} windows", flush=True)
    return np.array(X, np.float32), np.array(y), np.array(rnd), np.array(take), np.array(t), ids


def smoothed_runs(P, classes, take, t):
    """Longest run of 'lying' after the server's 3 s probability smoothing, per take."""
    li = classes.index("lying")
    runs = {}
    for k in np.unique(take):
        i = np.where(take == k)[0]
        i = i[np.argsort(t[i])]
        best = [int(P[i[max(0, j - 5):j + 1]].mean(0).argmax()) for j in range(len(i))]
        run = mx = 0
        for b in best:
            run = run + 1 if b == li else 0
            mx = max(mx, run)
        runs[int(k)] = mx * server.HOP
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="*")
    ap.add_argument("--test", nargs="*")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    raw = sorted(glob.glob(os.path.join(server.DATA, "raw", "raw-*.csv")), key=os.path.getmtime)
    train = a.train or [p for p in raw if "raw-train-" in os.path.basename(p)][-3:]
    test = a.test or [p for p in raw if "raw-test-" in os.path.basename(p)][-1:]
    cfg = havenconfig.load(None)
    Xtr, ytr, rtr, ktr, ttr, ids = load(train, cfg, "train")
    Xte, yte, rte, kte, tte, ids_te = load(test, cfg, "test")
    print("links", ids, "| train", dict(zip(*np.unique(ytr, return_counts=True))), "| test", dict(zip(*np.unique(yte, return_counts=True))))

    Z, mu, sd = None, Xtr.mean(0), Xtr.std(0) + 1e-6
    from collections import Counter
    pred, P = [], []
    Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
    classes = sorted(set(ytr))
    for z in Zte:                                  # same k=7 nearest-neighbour vote as server.py
        dist = ((Ztr - z) ** 2).sum(1)
        nn = ytr[np.argsort(dist)[:7]]
        c = Counter(nn)
        P.append([c.get(k, 0) / 7 for k in classes])
        pred.append(c.most_common(1)[0][0])
    pred, P = np.array(pred), np.array(P)
    print(f"\nTEST (prompt labels, settled windows): {np.mean(pred == yte):.1%} on {len(yte)} windows")
    print("           " + "".join(f"{c:>9s}" for c in LABELS) + "   correct")
    for c in LABELS:
        row = [int(((yte == c) & (pred == p)).sum()) for p in LABELS]
        n = max(1, int((yte == c).sum()))
        print(f"{c:>10s} " + "".join(f"{v:9d}" for v in row) + f"   {row[LABELS.index(c)] / n:5.0%}")
    runs = smoothed_runs(P, classes, kte, tte)
    print("\nlongest smoothed 'lying' run per step (alert needs 3 s):")
    for k, r in runs.items():
        lab = yte[kte == k][0]
        print(f"  {lab:9s} {r:4.1f} s" + ("   <-- would alert" if lab != "lying" and r >= 3 else ""))

    if a.save:
        if os.path.exists(server.DATASET):
            bak = server.DATASET.replace(".npz", f"-camera-labels-{time.strftime('%H%M')}.npz")
            shutil.copy(server.DATASET, bak)
            print("backed up camera-labelled dataset to", bak)
        X = np.concatenate([Xtr, Xte]); y = np.concatenate([ytr, yte])
        np.savez(server.DATASET, X=X, cam=y, prompt=y,
                 sess=np.array(["train"] * len(ytr) + ["test"] * len(yte)),
                 rnd=np.concatenate([rtr, rte]).astype(np.int32), take=np.concatenate([ktr, kte + 1000]).astype(np.int32),
                 t=np.concatenate([ttr, tte]), ids=np.array(ids, dtype=str))
        print("saved prompt-labelled dataset to", server.DATASET, "(restart server.py to load it)")


if __name__ == "__main__":
    main()
