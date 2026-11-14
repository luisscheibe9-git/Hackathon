"""Offline movement replay in the Stillpoint Observatory.

Steps through a saved CSI CSV in (scaled) real time and serves the same `/live` JSON the
live capture serves, so `tools/observatory/` renders it unchanged. With `?replay=1` the page
also shows a replay bar: time, ground-truth stage, play/pause/seek/speed, and the detector
verdict per receiver path:
  - "Likely movement near path X"  when the motion model's P(moving) >= 0.7 on path X
  - "No movement detected"          when every path is <= 0.3
  - "Unknown (low confidence)"      otherwise
No person marker is drawn: a dot at an x/y position would need location validation we
have not done.

N receivers: add a `receiver` (or `port`) column to the CSV; each distinct value becomes a
path. The current recording has no such column, so it replays as one path ("receiver-1").

    python detection/replay.py                                   # default recording
    python detection/replay.py --csv data/other.csv --speed 2
    python detection/replay.py --no-browser --port 8765           # fixed port, no auto-open
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from csi import amplitude_from_hex  # noqa: E402
from detector import CsiMotionDetector  # noqa: E402

HIGH, LOW = 0.7, 0.3
STEP_S = 0.25  # detector evaluated every 0.25 s of recording time
STAGE_GAP_S = 1.0  # elapsed_ms restarts per stage; stages are laid end to end with this gap


def load(csv_path: Path):
    """Return {receiver: dict(t, change, rssi, amp)}, stage spans, total duration."""
    rows = {}
    spans = []
    offset, last_key, last_t = 0.0, None, 0.0
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            key = (r.get("trial", ""), r.get("stage", ""))
            t_local = int(r["elapsed_ms"]) / 1000.0
            if key != last_key:
                if last_key is not None:
                    offset = last_t + STAGE_GAP_S
                spans.append({"trial": key[0], "stage": key[1], "start": offset, "end": offset})
                last_key = key
            t = offset + t_local
            last_t = t
            spans[-1]["end"] = t
            rec = r.get("receiver") or r.get("port") or "receiver-1"
            d = rows.setdefault(rec, {"t": [], "amp": [], "rssi": []})
            d["t"].append(t)
            d["amp"].append(amplitude_from_hex(r["lltf_hex"]))
            d["rssi"].append(int(float(r["rssi_dbm"])))
    out = {}
    for rec, d in sorted(rows.items()):
        amp = np.array(d["amp"])
        norm = amp / (amp.sum(1, keepdims=True) + 1e-9)
        change = np.r_[0.0, np.abs(np.diff(norm, axis=0)).sum(1)]  # same score as live /live "motion"
        out[rec] = {"t": np.array(d["t"]), "amp": amp, "rssi": np.array(d["rssi"]), "change": change}
    return out, spans, max(s["end"] for s in spans)


def precompute_scores(receivers, duration, det: CsiMotionDetector):
    grid = np.arange(det.win_s, duration + STEP_S, STEP_S)
    for d in receivers.values():
        p = np.full(len(grid), np.nan)
        for i, end in enumerate(grid):
            idx = np.where((d["t"] > end - det.win_s) & (d["t"] <= end))[0]
            if len(idx) >= 6 and d["t"][idx[-1]] - d["t"][idx[0]] < det.win_s + 0.5:
                p[i] = det.predict(d["amp"][idx])[1]
        d["p_grid"] = p
    return grid


class Replay:
    def __init__(self, receivers, spans, duration, grid, speed):
        self.receivers, self.spans, self.duration, self.grid = receivers, spans, duration, grid
        self.speed, self.playing = speed, True
        self.t0, self.wall0 = 0.0, time.monotonic()
        self.lock = threading.Lock()

    def now(self):
        with self.lock:
            t = self.t0 + ((time.monotonic() - self.wall0) * self.speed if self.playing else 0.0)
            if t > self.duration:  # loop
                self.t0, self.wall0, t = 0.0, time.monotonic(), 0.0
            return t

    def control(self, q):
        t = self.now()
        with self.lock:
            cmd = q.get("cmd", [""])[0]
            if cmd == "pause":
                self.playing = False
            elif cmd == "play":
                self.playing = True
            elif cmd == "seek":
                t = min(max(float(q.get("t", ["0"])[0]), 0.0), self.duration)
            if "speed" in q:
                self.speed = min(max(float(q["speed"][0]), 0.25), 16.0)
            self.t0, self.wall0 = t, time.monotonic()

    def live(self):
        """Same shape as tools/csi-visualizer.py /live, plus detector fields."""
        t = self.now()
        out = []
        for rec, d in self.receivers.items():
            past = d["t"] <= t
            hist = past & (d["t"] >= t - 30)
            recent = past & (d["t"] >= t - 2)
            motion = float(statistics.median(d["change"][recent])) if recent.sum() > 1 else None
            gi = int(np.searchsorted(self.grid, t, side="right")) - 1
            p = None if gi < 0 or np.isnan(d["p_grid"][gi]) else float(d["p_grid"][gi])
            label = "unknown" if p is None else ("moving" if p >= HIGH else "still" if p <= LOW else "unknown")
            out.append({
                "port": rec, "motion": motion,
                "rssi": int(d["rssi"][recent][-1]) if recent.any() else None,
                "rate": float(recent.sum() / 2), "status": "Replay" if recent.any() else "Replay gap",
                "samples": [[round(t - tt, 2), round(float(c), 4)] for tt, c in zip(d["t"][hist], d["change"][hist])],
                "p_moving": p, "label": label,
            })
        return out

    def state(self):
        t = self.now()
        live = self.live()
        span = next((s for s in self.spans if s["start"] <= t <= s["end"] + STAGE_GAP_S), None)
        scored = [r for r in live if r["p_moving"] is not None]
        top = max(scored, key=lambda r: r["p_moving"], default=None)
        if top is None:
            verdict = "Unknown (no data)"
        elif top["p_moving"] >= HIGH:
            verdict = f"Likely movement near path {top['port']}"
        elif all(r["p_moving"] <= LOW for r in scored):
            verdict = "No movement detected"
        else:
            verdict = "Unknown (low confidence)"
        return {"t": round(t, 2), "duration": round(self.duration, 2), "speed": self.speed,
                "playing": self.playing, "truth": span and f"trial {span['trial']} · {span['stage']}",
                "verdict": verdict, "top": top and top["port"],
                "paths": [{"port": r["port"], "p_moving": r["p_moving"], "label": r["label"]} for r in live]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data" / "csi-motion-20261114-105805.csv"))
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    receivers, spans, duration = load(Path(args.csv))
    det = CsiMotionDetector()
    grid = precompute_scores(receivers, duration, det)
    replay = Replay(receivers, spans, duration, grid, args.speed)

    class Handler(SimpleHTTPRequestHandler):
        def send_json(self, obj):
            payload = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/live":
                self.send_json(replay.live())
            elif url.path == "/replay/state":
                self.send_json(replay.state())
            elif url.path == "/replay/control":
                replay.control(parse_qs(url.query))
                self.send_json(replay.state())
            else:
                super().do_GET()

        def log_message(self, *_):
            pass

    assets = ROOT / "tools" / "observatory"
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(assets))) as server:
        url = f"http://127.0.0.1:{server.server_port}/?replay=1"
        print(f"Replaying {Path(args.csv).name}: {len(receivers)} receiver path(s), {duration:.0f} s. Open {url}", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
