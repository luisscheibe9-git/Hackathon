"""Parse esp-csi-style L-LTF CSI (the `lltf_hex` column) into amplitudes.

Frame layout (original ESP32, L-LTF only): 64 subcarriers x (I, Q) as int8 = 128 bytes.
Order is subcarrier 0..31 then -32..-1. With first_word_invalid=1 the first 4 bytes
(subcarriers 0 and 1) are garbage. Indices 28..36 are the null guard band, 27 and 37 are
near-zero edges. We keep 2..26 and 38..63 = 51 usable subcarriers.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

USABLE = np.r_[2:27, 38:64]  # 51 subcarriers


def amplitude_from_hex(lltf_hex: str) -> np.ndarray:
    """One frame of `lltf_hex` -> amplitude vector over the usable subcarriers (float32)."""
    iq = np.frombuffer(bytes.fromhex(lltf_hex), dtype=np.int8).reshape(-1, 2).astype(np.float32)
    amp = np.hypot(iq[:, 0], iq[:, 1])
    return amp[USABLE]


def amplitudes(hex_frames) -> np.ndarray:
    """Iterable of hex strings -> (n_frames, 51) amplitude matrix."""
    return np.stack([amplitude_from_hex(h) for h in hex_frames])


def load_recording(path: str | Path):
    """Load a Measure-CsiMotion CSV. Returns a list of segments, one per (trial, stage):
    dict(trial, stage, t_s, amp (n,51), rssi (n,))."""
    segments: dict[tuple[int, str], dict] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = (int(row["trial"]), row["stage"])
            seg = segments.setdefault(key, {"trial": key[0], "stage": key[1], "t": [], "hex": [], "rssi": []})
            seg["t"].append(int(row["elapsed_ms"]) / 1000.0)
            seg["hex"].append(row["lltf_hex"])
            seg["rssi"].append(float(row["rssi_dbm"]))
    out = []
    for seg in segments.values():
        out.append({
            "trial": seg["trial"],
            "stage": seg["stage"],
            "t_s": np.asarray(seg["t"]),
            "amp": amplitudes(seg["hex"]),
            "rssi": np.asarray(seg["rssi"]),
        })
    return out
