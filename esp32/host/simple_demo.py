"""Haven simple demo: two Wi-Fi paths at two heights, one fixed rule.

    top path    #1 -> #2 (board #2 mounted high, ~1.3 m)
    bottom path #1 -> #3 (board #3 on the floor)

    neither path disturbed      -> ROOM EMPTY
    top disturbed (any bottom)  -> PERSON STANDING
    only bottom disturbed       -> PERSON LYING, held 3 s -> FALL DETECTED (+ phone push)

No machine learning, no training data. Calibration is 10 s of empty room (plus an optional 8 s
lying check that sets the top-path threshold above what a lying person causes).

Run from esp32/:
    .venv\\Scripts\\python.exe -u host\\simple_demo.py --gateway COM4
    python host/simple_demo.py --sim          # no hardware: simulated paths for rehearsing the UI
Then open http://127.0.0.1:8950
Keys on the page: C calibrate empty, L check lying, R reset, T test phone.
"""
import argparse
import collections
import json
import os
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
LINE = re.compile(rb"(RELAY|PEER),([0-9a-f]{12}),(-?\d+),([0-9a-f]{256})")
BOARD_MAC = {"2": "6809479f27f4", "3": "6809471a80ac"}   # permanent board labels (NOTES.md)
WINDOW_S, TICK_S, SMOOTH_TICKS = 1.0, 0.25, 4
DEFAULT_THR = 1.5   # x the empty room's own 95th-percentile noise


class Path:
    def __init__(self, name):
        self.name = name
        self.frames = collections.deque()        # (t, raw amplitude vector)
        self.lock = threading.Lock()
        self.base = self.mask = None
        self.noise = (1.0, 1.0)                  # empty-room p95 of (shape, motion)
        self.threshold = DEFAULT_THR
        self.scores = collections.deque(maxlen=SMOOTH_TICKS)

    def add(self, t, amp):
        with self.lock:
            self.frames.append((t, amp))
            while self.frames and t - self.frames[0][0] > 30:
                self.frames.popleft()

    def recent(self, since):
        with self.lock:
            return [a for t, a in self.frames if t >= since]

    def pps(self, now):
        with self.lock:
            return sum(1 for t, _ in self.frames if t >= now - 1.0)

    def norm(self, amps):
        a = np.asarray(amps)[:, self.mask]
        return a / np.sqrt((a ** 2).mean(axis=1, keepdims=True) + 1e-9)

    def raw_score(self, amps):
        """(shape distance from the empty room, frame-to-frame motion) for one window."""
        v = self.norm(amps)
        shape = float(np.sqrt(((v.mean(axis=0) - self.base) ** 2).mean()))
        motion = float(np.sqrt((np.diff(v, axis=0) ** 2).mean())) if len(v) > 1 else 0.0
        return shape, motion

    def calibrate(self, amps):
        a = np.asarray(amps)
        mean = a.mean(axis=0)
        self.mask = mean > 0.2 * np.median(mean)
        self.base = self.norm(a).mean(axis=0)
        n = max(5, int(len(a) / 10))                       # ~1 s windows over the 10 s recording
        stats = np.array([self.raw_score(a[i:i + n]) for i in range(0, len(a) - n, max(1, n // 4))])
        self.noise = tuple(np.maximum(np.percentile(stats, 95, axis=0), 1e-4))
        self.threshold = DEFAULT_THR
        self.scores.clear()

    def score(self, now):
        amps = self.recent(now - WINDOW_S)
        if self.base is None or len(amps) < 5:
            return None
        shape, motion = self.raw_score(amps)
        self.scores.append(max(shape / self.noise[0], motion / self.noise[1]))
        return float(np.median(self.scores))


class Demo:
    def __init__(self, args):
        self.args = args
        self.paths = {"top": Path("top"), "bottom": Path("bottom")}
        self.mac_role = {BOARD_MAC[args.top]: "top", BOARD_MAC[args.bottom]: "bottom"}
        self.state, self.lying_since, self.alert_at, self.pushed = "uncalibrated", None, None, False
        self.cal = {"phase": "idle", "message": "Press C with the room empty to calibrate (10 s)."}
        self.last = {"top": None, "bottom": None}
        self.sim_scene = "empty"
        self.log = None

    # ---------- input ----------
    def feed(self, line, now):
        m = LINE.fullmatch(line.strip())
        if not m or m[1] != b"RELAY":
            return
        role = self.mac_role.get(m[2].decode())
        if role:
            iq = np.frombuffer(bytes.fromhex(m[4].decode()), dtype=np.int8).astype(float).reshape(64, 2)
            self.paths[role].add(now, np.hypot(iq[:, 0], iq[:, 1]))

    def read_gateway(self):
        import serial
        while True:
            try:
                port = serial.Serial(self.args.gateway, 460800, timeout=0.05)
                try:
                    port.set_buffer_size(rx_size=1 << 20)       # Windows default 4 KB mangles lines
                except Exception:
                    pass
                print(f"Gateway {self.args.gateway} open", flush=True)
                buf, last = b"", time.time()
                while True:
                    chunk = port.read(4096)
                    now = time.time()
                    if chunk:
                        last = now
                        buf += chunk
                        *lines, buf = buf.split(b"\n")
                        for line in lines:
                            self.feed(line, now)
                    elif now - last > 5:
                        raise IOError("no data for 5 s")
            except Exception as e:
                print(f"Gateway: {e!r}; reopening in 1 s", flush=True)
                try:
                    port.close()
                except Exception:
                    pass
                time.sleep(1)

    def simulate(self):
        """Fake both paths: a fixed empty-room profile, plus a person on the paths the scene says."""
        rng = np.random.default_rng(1)
        profile = {r: 20 + 10 * rng.random(64) for r in self.paths}
        offset = {r: 6 * rng.standard_normal(64) for r in self.paths}
        while True:
            hit = {"empty": (), "standing": ("top", "bottom"), "lying": ("bottom",)}[self.sim_scene]
            now = time.time()
            for r in self.paths:
                amp = profile[r] + 0.6 * rng.standard_normal(64)
                if r in hit:
                    amp = amp + offset[r] + 1.5 * rng.standard_normal(64)
                self.paths[r].add(now, np.abs(amp))
            time.sleep(1 / 30)

    # ---------- calibration ----------
    def start_cal(self, kind):
        if self.cal["phase"] in ("countdown", "recording"):
            return
        if kind == "lying" and self.paths["top"].base is None:
            self.cal["message"] = "Calibrate the empty room first (C)."
            return
        threading.Thread(target=self._cal, args=(kind,), daemon=True).start()

    def _cal(self, kind):
        secs = 10 if kind == "empty" else 8
        who = "Everyone out of the sensing area" if kind == "empty" else "Lie down on the mat and stay there"
        for i in range(3, 0, -1):
            self.cal = {"phase": "countdown", "message": f"{who}. Starting in {i}..."}
            time.sleep(1)
        t0 = time.time()
        self.cal = {"phase": "recording", "message": f"Recording {kind} for {secs} s. {who}.", "ends": t0 + secs}
        if kind == "empty":
            time.sleep(secs)
            data = {r: p.recent(t0) for r, p in self.paths.items()}
            short = [r for r, a in data.items() if len(a) < 5 * secs]
            if short:
                self.cal = {"phase": "failed", "message": f"Too few packets on the {', '.join(short)} path. "
                            "Check that board's power, wait 15 s, and press C again."}
                return
            for r, p in self.paths.items():
                p.calibrate(data[r])
            self.reset()
            self.cal = {"phase": "done", "message": "Empty room calibrated. Optional: press L to check lying."}
        else:
            seen = {r: [] for r in self.paths}
            while time.time() < t0 + secs:
                for r in self.paths:
                    if self.last[r] is not None:
                        seen[r].append(self.last[r])
                time.sleep(TICK_S)
            top, bottom = self.paths["top"], self.paths["bottom"]
            top_p90 = float(np.percentile(seen["top"], 90)) if seen["top"] else 0
            bottom_med = float(np.median(seen["bottom"])) if seen["bottom"] else 0
            # Top: just above what a lying person causes. Bottom: well below what lying causes.
            top.threshold = round(max(DEFAULT_THR, 1.3 * top_p90), 2)
            bottom.threshold = round(min(max(DEFAULT_THR, 0.6 * bottom_med), 4.0), 2)
            msg = f"Lying check: bottom path {bottom_med:.1f}, top path {top_p90:.1f}. "                   f"Thresholds set: top {top.threshold:.1f}, bottom {bottom.threshold:.1f}."
            if bottom_med < 1.2 * bottom.threshold or top_p90 >= 0.8 * bottom_med:
                msg += " WARNING: lying is not clearly bottom-only. Move the mat closer to board "                        f"#{self.args.bottom}, keep it out from under the top path, then press C and L again."
            self.reset()
            self.cal = {"phase": "done", "message": msg}

    # ---------- detection ----------
    def reset(self):
        self.state, self.lying_since, self.alert_at, self.pushed = "empty", None, None, False

    def tick(self):
        while True:
            now = time.time()
            for r, p in self.paths.items():
                self.last[r] = p.score(now)
            top, bottom = self.last["top"], self.last["bottom"]
            if self.paths["top"].base is None:
                state = "uncalibrated"
            elif top is None or bottom is None:
                state = "no_signal"
            elif self.alert_at:
                state = "alert"
            else:
                up = top > self.paths["top"].threshold
                low = bottom > self.paths["bottom"].threshold
                state = "standing" if up else ("lying" if low else "empty")
            if state == "lying":
                self.lying_since = self.lying_since or now
                if now - self.lying_since >= self.args.lie_seconds:
                    state, self.alert_at = "alert", now
            elif state != "alert":
                self.lying_since = None
            if state == "alert" and not self.pushed:
                self.pushed = True
                self.push("Fall detected in Room 1", "Check on patient.")
            self.state = state
            self.write_log(now)
            time.sleep(TICK_S)

    def push(self, title, body):
        topic = self.args.ntfy
        if not topic:
            return
        def send():
            try:
                req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(),
                                             headers={"Title": title, "Priority": "urgent", "Tags": "rotating_light"})
                urllib.request.urlopen(req, timeout=5).read()
            except Exception as e:
                print(f"Phone push failed: {e!r}", flush=True)
        threading.Thread(target=send, daemon=True).start()

    def write_log(self, now):
        if self.log is None:
            os.makedirs(DATA, exist_ok=True)
            path = os.path.join(DATA, f"simple-demo-log-{time.strftime('%Y%m%d')}.csv")
            new = not os.path.exists(path)
            self.log = open(path, "a", buffering=1)
            if new:
                self.log.write("t,clock,state,top,bottom,top_thr,bottom_thr,top_pps,bottom_pps\n")
        f = lambda v: "" if v is None else f"{v:.2f}"
        self.log.write(f"{now:.2f},{time.strftime('%H:%M:%S')},{self.state},{f(self.last['top'])},"
                       f"{f(self.last['bottom'])},{self.paths['top'].threshold:.2f},"
                       f"{self.paths['bottom'].threshold:.2f},{self.paths['top'].pps(now)},"
                       f"{self.paths['bottom'].pps(now)}\n")

    def snapshot(self):
        now = time.time()
        return {"state": self.state, "cal": self.cal, "sim": self.args.sim, "scene": self.sim_scene,
                "lying_for": now - self.lying_since if self.lying_since else 0, "lie_seconds": self.args.lie_seconds,
                "alert_at": self.alert_at, "phone": bool(self.args.ntfy),
                "paths": {r: {"score": self.last[r], "threshold": p.threshold, "pps": p.pps(now),
                              "board": self.args.top if r == "top" else self.args.bottom}
                          for r, p in self.paths.items()}}


def make_handler(demo):
    page = open(os.path.join(HERE, "web", "simple.html"), "rb").read()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, body, kind="application/json"):
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/state"):
                return self.send(json.dumps(demo.snapshot()).encode())
            return self.send(page, "text/html; charset=utf-8")

        def do_POST(self):
            cmd = self.path.rstrip("/").split("/")[-1]
            if cmd == "calibrate":
                demo.start_cal("empty")
            elif cmd == "lying":
                demo.start_cal("lying")
            elif cmd == "reset":
                demo.reset()
            elif cmd == "phone":
                demo.push("Haven test", "Phone alerts are working.")
            elif cmd in ("empty", "standing", "lying_sim") and demo.args.sim:
                demo.sim_scene = cmd.replace("_sim", "")
            return self.send(json.dumps(demo.snapshot()).encode())
    return H


def ntfy_from_config():
    try:
        text = open(os.path.join(HERE, "..", "config.yaml"), encoding="utf-8").read()
        m = re.search(r"ntfy_topic:\s*['\"]?([A-Za-z0-9_-]+)", text)
        return m[1] if m else ""
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gateway", help="serial port of board #1 (e.g. COM4 or /dev/cu.usbserial-0001)")
    ap.add_argument("--sim", action="store_true", help="no hardware: simulated paths")
    ap.add_argument("--top", default="2", choices=["2", "3"], help="board mounted high (default 2)")
    ap.add_argument("--bottom", default="3", choices=["2", "3"], help="board on the floor (default 3)")
    ap.add_argument("--lie-seconds", type=float, default=3.0, help="lying this long raises FALL DETECTED")
    ap.add_argument("--ntfy", default=None, help="ntfy topic for the phone (default: notify.ntfy_topic in config.yaml)")
    ap.add_argument("--port", type=int, default=8950)
    args = ap.parse_args()
    if not args.sim and not args.gateway:
        ap.error("give --gateway PORT, or --sim to rehearse without boards")
    if args.top == args.bottom:
        ap.error("--top and --bottom must be different boards")
    args.ntfy = ntfy_from_config() if args.ntfy is None else args.ntfy
    demo = Demo(args)
    threading.Thread(target=demo.simulate if args.sim else demo.read_gateway, daemon=True).start()
    threading.Thread(target=demo.tick, daemon=True).start()
    print(f"Open http://127.0.0.1:{args.port}   (phone alerts {'on' if args.ntfy else 'off'})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(demo)).serve_forever()


if __name__ == "__main__":
    main()
