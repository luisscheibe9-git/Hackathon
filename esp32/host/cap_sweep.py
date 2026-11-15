"""Try different class-balance caps on the saved dataset (same kNN as server.py). Usage: python host/cap_sweep.py"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import server
d = np.load(os.path.join(server.DATA, "haven_dataset.npz"), allow_pickle=True)
X, sess = d["X"], d["sess"]
y = np.array([server.training_label(c, p) for c, p in zip(d["cam"], d["prompt"])], dtype=object)
ok = np.array([v is not None for v in y])
tr0, te = ok & (sess == "train"), ok & (sess == "test")
for cap in (1, 1.5, 2, 4, 99):
    tr = server.balanced(tr0, y, cap=cap)
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
    Ztr, Zte, ytr = (X[tr] - mu) / sd, (X[te] - mu) / sd, y[tr]
    pred = []
    for z in Zte:
        nn = ytr[np.argsort(((Ztr - z) ** 2).sum(1))[:7]]
        v, c = np.unique(nn, return_counts=True); pred.append(v[c.argmax()])
    pred, yt = np.array(pred), y[te]
    pc = {l: round(float((pred[yt == l] == l).mean()), 2) for l in sorted(set(yt))}
    print(f"cap {cap:>2}: acc {np.mean(pred == yt):.2f}  {pc}  train counts {dict(zip(*np.unique(ytr, return_counts=True)))}")
