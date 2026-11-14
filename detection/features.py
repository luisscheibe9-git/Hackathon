"""Window features and hand-made motion scores for CSI amplitude windows.

All functions take `amp`: (n_frames, n_subcarriers) amplitudes for ONE window from ONE
receiver. Features use means/medians, not sums, so they do not depend much on frame rate
(the recording is ~12 frames/s, the live stream ~30 frames/s).
"""
from __future__ import annotations

import numpy as np

EPS = 1e-6


# ---- hand-made motion scores (no training) -------------------------------------------

def turbulence(amp: np.ndarray) -> np.ndarray:
    """ESPectre-style per-frame 'spatial turbulence': std/mean of amplitude across
    subcarriers. Ratio cancels AGC gain changes. Shape (n_frames,)."""
    return amp.std(axis=1) / (amp.mean(axis=1) + EPS)


def espectre_score(amp: np.ndarray) -> float:
    """ESPectre-style motion score: variance of turbulence over the window, scaled to
    readable numbers. (ESPectre's default detector also uses lag-1 autocorrelation and
    relative IQR of turbulence; those are features below.) Our own re-implementation from
    their docs, no ESPectre code (GPLv3) copied."""
    return float(np.var(turbulence(amp)) * 1e4)


def team_change_score(amp: np.ndarray) -> float:
    """The team's original score from tools/Measure-CsiMotion.ps1: median over frames of
    the L1 distance between consecutive sum-normalised amplitude vectors."""
    norm = amp / (amp.sum(axis=1, keepdims=True) + EPS)
    if len(norm) < 2:
        return 0.0
    return float(np.median(np.abs(np.diff(norm, axis=0)).sum(axis=1)))


def espcsi_wander_jitter(amp: np.ndarray) -> tuple[float, float]:
    """esp-csi-style presence/motion pair. Espressif's exact esp-radar formulas are not
    published in the repo, so this is an approximation of the idea:
    wander = 1 - mean correlation of each frame with the window's mean frame (how much the
    channel shape drifts), jitter = mean (1 - correlation) between consecutive frames."""
    if len(amp) < 2:
        return 0.0, 0.0
    z = amp - amp.mean(axis=1, keepdims=True)
    z /= np.linalg.norm(z, axis=1, keepdims=True) + EPS
    ref = z.mean(axis=0)
    ref /= np.linalg.norm(ref) + EPS
    wander = float(1.0 - np.mean(z @ ref))
    jitter = float(np.mean(1.0 - np.sum(z[1:] * z[:-1], axis=1)))
    return wander, jitter


# ---- feature vector for the learned classifier ---------------------------------------

FEATURE_NAMES = [
    "team_change", "espectre_var", "wander", "jitter",
    "turb_mean", "turb_lag1_autocorr", "turb_rel_iqr",
    "sc_cv_mean", "sc_cv_p90", "amp_mean", "amp_lowband_ratio",
    "rssi_mean", "rssi_std",
]


def window_features(amp: np.ndarray, rssi: np.ndarray | None = None) -> np.ndarray:
    turb = turbulence(amp)
    if len(turb) > 2 and turb.std() > EPS:
        lag1 = float(np.corrcoef(turb[:-1], turb[1:])[0, 1])
    else:
        lag1 = 0.0
    q75, q25 = np.percentile(turb, [75, 25])
    sc_cv = amp.std(axis=0) / (amp.mean(axis=0) + EPS)  # temporal variation per subcarrier
    half = amp.shape[1] // 2
    wander, jitter = espcsi_wander_jitter(amp)
    if rssi is None or len(rssi) == 0:
        rssi = np.array([0.0])
    return np.array([
        team_change_score(amp),
        espectre_score(amp),
        wander,
        jitter,
        float(turb.mean()),
        lag1,
        float((q75 - q25) / (np.median(turb) + EPS)),
        float(sc_cv.mean()),
        float(np.percentile(sc_cv, 90)),
        float(amp.mean()),
        float(amp[:, :half].mean() / (amp[:, half:].mean() + EPS)),
        float(np.mean(rssi)),
        float(np.std(rssi)),
    ])


def windows(t_s: np.ndarray, win_s: float = 1.0, step_s: float = 0.5, min_frames: int = 6):
    """Yield index arrays for sliding time windows over one continuous segment."""
    start = t_s[0]
    while start + win_s <= t_s[-1] + 1e-9:
        idx = np.where((t_s >= start) & (t_s < start + win_s))[0]
        if len(idx) >= min_frames:
            yield idx
        start += step_s
