"""Live-stream interface for the trained CSI window model.

    from detection.detector import CsiMotionDetector
    det = CsiMotionDetector()                 # loads models/csi_motion_model.joblib
    label, score = det.predict(frames)        # frames: last ~1 s of lltf_hex strings
                                              # (or an (n, 51) amplitude array) from ONE receiver

`label` is "moving" or "still"; `score` is P(moving) in [0, 1]. With several receivers, call
predict per receiver and take the max score (any path that sees motion).

Smoke test on the recording:  python detection/detector.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from csi import amplitudes  # noqa: E402
from features import FEATURE_NAMES, window_features  # noqa: E402


class CsiMotionDetector:
    def __init__(self, model_path: str | Path = HERE / "models" / "csi_motion_model.joblib"):
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.labels = bundle["labels"]
        self.win_s = bundle["win_s"]
        self.cols = [FEATURE_NAMES.index(n) for n in bundle["features"]]
        self.pos = self.labels.index("moving") if "moving" in self.labels else None

    def predict(self, frames, rssi=None) -> tuple[str, float]:
        """frames: list of lltf_hex strings or (n_frames, 51) amplitudes, covering ~win_s
        seconds (>= 6 frames). Returns (label, score)."""
        amp = amplitudes(frames) if isinstance(frames[0], str) else np.asarray(frames, dtype=float)
        x = window_features(amp, None if rssi is None else np.asarray(rssi, dtype=float))[self.cols]
        proba = self.model.predict_proba(x[None, :])[0]
        i = int(np.argmax(proba))
        score = float(proba[self.pos]) if self.pos is not None else float(proba[i])
        return str(self.labels[i]), score


if __name__ == "__main__":
    from csi import load_recording
    det = CsiMotionDetector()
    for seg in load_recording(HERE.parent / "data" / "csi-motion-20261114-105805.csv"):
        mid = np.searchsorted(seg["t_s"], 10.0)
        idx = np.where((seg["t_s"] >= seg["t_s"][mid]) & (seg["t_s"] < seg["t_s"][mid] + det.win_s))[0]
        label, score = det.predict(seg["amp"][idx])
        print(f"trial {seg['trial']} {seg['stage']:9s} -> {label:6s} P(moving)={score:.2f}  (in-sample)")
