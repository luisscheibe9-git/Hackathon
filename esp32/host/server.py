#!/usr/bin/env python3
"""Haven host: receives CSI from the ESP32 nodes, learns activities with the webcam as teacher, and runs
the live fall / long-lie detector.

  python host/server.py                      ->  http://127.0.0.1:8940  (live view)  ·  /train.html (webcam teacher)
  python host/server.py --serial /dev/cu.usbserial-0001   (also read a node streaming over USB)

Input (UDP, default port 5005; or serial lines "CSIB:<base64>"), see firmware/haven-csi-node/main/protocol.h:
  0xC5110001  CSI frame  [20-byte header][int8 CSI][6-byte transmitter MAC if byte 19 bit 7]
  0xC5110002  status     32 bytes, once per second per node (motion score, node MAC)
Frames from ESP32-S3 boards running RuView + wifi-sensing-kit use the same format and also work.

A "link" is one transmitter -> receiver pair: "R>1" = router to node 1, "2>1" = node 2 to node 1.
Every 0.5 s each link gives a feature vector over the last 1.5 s: mean subcarrier shape, per-subcarrier
spread, and mean frame-to-frame change (same features as wifi-sensing-kit). A k-nearest-neighbour model
maps the vector to an activity. During training the browser page runs MediaPipe Pose on the webcam and
sends only a label ("sitting") to this server; video never leaves the browser and nothing is stored but
WiFi features + labels. The camera is a training tool only; the live detector uses WiFi alone.

Everything is saved under esp32/data/ (git-ignored).
"""
import argparse
import base64
import json
import os
import re
import socket
import struct
import sys
import threading
import time
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import havenconfig  # noqa: E402

WEB = os.path.join(HERE, "web")
DATA = os.path.join(os.path.dirname(HERE), "data")
DATASET = os.path.join(DATA, "haven_dataset.npz")
METRICS = os.path.join(DATA, "model_metrics.json")

CSI_MAGIC, STATUS_MAGIC = 0xC5110001, 0xC5110002
F_FROM_AP, F_FIRST_BAD, F_TX_MAC = 0x20, 0x40, 0x80
N_RAW = 64                       # the LLTF block (first 128 bytes) is in every packet type
VALID = np.r_[1:27, 38:64]       # 52 data subcarriers: DC (0) and guard band (27-37) carry nothing
N_SC = len(VALID)
WINDOW = 700                     # frames kept per link (~14 s at 50 Hz)

WIN, HOP, MIN_FRAMES = 2.0, 0.5, 4   # (was 1.5 s; widened for our ~3-10 pkt/s paths) feature window, step, minimum frames per link per window
LAG = 1.0                        # training windows end 1 s in the past so camera fall events can arrive
LABELS = ["empty", "standing", "walking", "sitting", "lying", "fall"]
ACTIVE = {"standing", "walking", "sitting"}
# Guided recording: which camera labels are accepted while the page asks for each movement.
# The camera supplies the label; the prompt vetoes implausible ones (e.g. "walking" during "sit").
ACCEPT = {"empty": {"empty"}, "standing": {"standing"}, "walking": {"walking"}, "sitting": {"sitting"},
          "lying": {"lying"}, "fall": {"fall", "lying"}}


# ------------------------------------------------------------------------------------------ input

class Link:
    """One transmitter -> receiver path. Only its most common CSI length is used (non-HT and HT
    packets from the same sender have different spectral shapes)."""

    def __init__(self, key):
        self.key = key
        self.amp = deque(maxlen=WINDOW)
        self.t = deque(maxlen=WINDOW)
        self.sizes = {}
        self.rssi = None
        self.lock = threading.Lock()

    def add(self, size, amp, now, rssi):
        with self.lock:
            self.sizes[size] = self.sizes.get(size, 0) + 1
            if sum(self.sizes.values()) > 20 and size != max(self.sizes, key=self.sizes.get):
                return
            self.amp.append(amp)
            self.t.append(now)
            self.rssi = rssi

    def window(self, t_end, win=WIN):
        with self.lock:
            if not self.t:
                return None
            t = np.fromiter(self.t, float, len(self.t))
            m = (t > t_end - win) & (t <= t_end)
            if m.sum() < MIN_FRAMES:
                return None
            return np.array(self.amp, np.float32)[m]

    def stats(self, now):
        with self.lock:
            t = np.fromiter(self.t, float, len(self.t))
            pps = float(((t > now - 2.0)).sum() / 2.0)
            age = now - t[-1] if len(t) else None
        w = self.window(now, 1.0)
        motion = float((w.std(0) / (w.mean(0) + 1e-3)).mean()) if w is not None and len(w) > 4 else 0.0
        shape = w.mean(0).round(1).tolist() if w is not None else []
        return {"pps": pps, "age": age, "rssi": self.rssi, "motion": motion, "shape": shape}


class Receiver:
    def __init__(self, cfg):
        self.names = havenconfig.board_names(cfg)          # MAC -> "1", "2", ...
        self.router = str(cfg.get("router_bssid") or "").lower()
        self.links = {}
        self.nodes = {}                                     # node id -> status
        self.packets = 0
        self.lock = threading.Lock()

    def link(self, key):
        with self.lock:
            if key not in self.links:
                self.links[key] = Link(key)
            return self.links[key]

    def parse(self, d, origin):
        if len(d) < 4:
            return
        magic = struct.unpack_from("<I", d)[0]
        now = time.time()
        self.packets += 1
        if magic == CSI_MAGIC and len(d) >= 20 + 2 * N_RAW:
            nid = d[4]
            rssi = struct.unpack_from("<b", d, 16)[0]
            flags = d[19]
            tagged = bool(flags & F_TX_MAC) and len(d) >= 26 + 2 * N_RAW
            raw = d[20:-6] if tagged else d[20:]
            mac = ":".join(f"{b:02x}" for b in d[-6:]) if tagged else None
            if flags & F_FROM_AP or not tagged or mac == self.router:
                src = "R"
            else:
                src = self.names.get(mac)
            node = self.nodes.setdefault(nid, {"id": nid})
            node.update(origin=origin, seen=now)
            if src is None or src == str(nid):
                node["other"] = node.get("other", 0) + 1
                return
            iq = np.frombuffer(raw[:2 * N_RAW], np.int8).astype(np.float32)
            im, re = iq[0::2], iq[1::2]                     # ESP-IDF order: imaginary, real
            amp = np.sqrt(im * im + re * re)
            if flags & F_FIRST_BAD:                         # hardware flagged subcarrier 1 as invalid
                amp[1] = amp[2]
            amp = amp[VALID]
            amp = amp / (amp.mean() + 1e-6) * 20.0          # automatic gain jumps per packet: keep the shape
            self.link(f"{src}>{nid}").add(len(raw), amp, now, rssi)
            if src == "R":
                node["rssi"] = rssi
        elif magic == STATUS_MAGIC and len(d) >= 32:
            nid, flags = d[4], d[5]
            motion, score = struct.unpack_from("<ff", d, 16)
            uptime = struct.unpack_from("<I", d, 24)[0]
            mac_b = bytes(d[14:16]) + bytes(d[28:32])
            node = self.nodes.setdefault(nid, {"id": nid})
            node.update(origin=origin, seen=now, board_motion=round(motion, 4), board_moving=bool(flags & 4),
                        uptime_s=uptime // 1000)
            if any(mac_b):
                mac = ":".join(f"{b:02x}" for b in mac_b)
                node["mac"] = mac
                self.names.setdefault(mac, str(nid))         # learn peers that aren't in config.yaml

    def active_links(self, now, min_pps=3.0):
        with self.lock:
            items = list(self.links.items())
        return sorted(k for k, l in items if l.stats(now)["pps"] >= min_pps)


def udp_loop(rx, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 22)
    s.bind(("0.0.0.0", port))
    while True:
        d, a = s.recvfrom(4096)
        try:
            rx.parse(d, a[0])
        except Exception as e:  # a malformed packet must not stop the listener
            print("parse error:", e, flush=True)


GATEWAY_STATS = {"ok": 0, "bad": 0, "last_bad": b""}
# Raw CSI log while a recording runs (data/raw/raw-<session>-<time>.csv), so recordings can be
# re-analysed later with other windows/features. Haven itself only stores finished features.
RAW_LOG = {"f": None, "prompt": "", "paused": True, "lock": threading.Lock()}


def raw_log_open(session):
    raw_log_close()
    os.makedirs(os.path.join(DATA, "raw"), exist_ok=True)
    path = os.path.join(DATA, "raw", f"raw-{session}-{time.strftime('%Y%m%d-%H%M%S')}.csv")
    f = open(path, "w", buffering=1 << 16)
    f.write("t,kind,receiver_mac,rssi_dbm,prompt,paused,lltf_hex_centered\n")
    with RAW_LOG["lock"]:
        RAW_LOG["f"] = f
    print("raw CSI log:", path, flush=True)


def raw_log_close():
    with RAW_LOG["lock"]:
        f, RAW_LOG["f"] = RAW_LOG["f"], None
    if f:
        f.close()


def parse_gateway_line(rx, line):
    """Adapt the existing three-board Arduino gateway to the Haven packet parser."""
    match = re.fullmatch(rb"(RELAY|PEER),([0-9a-f]{12}),(-?\d+),([0-9a-f]{256})", line.strip())
    if not match:
        if line.strip():
            GATEWAY_STATS["bad"] += 1
            GATEWAY_STATS["last_bad"] = line.strip()
        return
    GATEWAY_STATS["ok"] += 1
    if RAW_LOG["f"]:
        with RAW_LOG["lock"]:
            if RAW_LOG["f"]:
                RAW_LOG["f"].write(f"{time.time():.3f},{match[1].decode()},{match[2].decode()},{match[3].decode()},"
                                   f"{RAW_LOG['prompt']},{int(RAW_LOG['paused'])},{match[4].decode()}\n")
    kind, raw_mac, raw_rssi, raw_csi = match.groups()
    mac = ":".join(raw_mac.decode()[i:i + 2] for i in range(0, 12, 2))
    nid = rx.names.get(mac)
    if nid not in ("2", "3") or (kind == b"PEER" and nid != "3"):
        return
    source = "2" if kind == b"PEER" else "1"
    source_mac = next((address for address, number in rx.names.items() if number == source), None)
    if source_mac is None:
        return
    header = bytearray(20)
    struct.pack_into("<I", header, 0, CSI_MAGIC)
    header[4] = int(nid)
    struct.pack_into("<b", header, 16, int(raw_rssi))
    # The Arduino receivers send the 64 L-LTF tones in centred order (-32..31): measured live on
    # Nov 14, zeros sit at indices 2-4 and 60-63. Haven expects 0..31,-32..-1, so swap the halves.
    # The first-word-invalid tones (-32, -31) then land in the guard band, which VALID already
    # drops, so F_FIRST_BAD must NOT be set (it would overwrite real subcarrier 1).
    csi = bytes.fromhex(raw_csi.decode())
    csi = csi[64:] + csi[:64]
    header[19] = F_TX_MAC
    rx.parse(bytes(header) + csi + bytes.fromhex(source_mac.replace(":", "")), "gateway")


def handle_serial_line(rx, port, line, gateway):
    if gateway:
        try:
            parse_gateway_line(rx, line)
        except Exception as e:  # one bad line must not stop the reader
            print("gateway parse error:", e, flush=True)
    elif line.startswith(b"CSIB:"):
        try:
            rx.parse(base64.b64decode(line[5:].strip()), f"serial:{port}")
        except Exception:
            pass


def serial_loop(rx, port, baud, gateway=False):
    """Non-blocking reader (short read timeout + manual line splitting, like tools/csi-visualizer.py)
    plus a watchdog thread that force-closes the port if no bytes arrive for 5 s. On Nov 14 a
    blocking readline() hung for good mid-session and silently lost most of a training run."""
    import serial
    while True:
        s = None
        try:
            s = serial.Serial(baudrate=baud, timeout=0.2)
            s.port, s.dtr, s.rts = port, False, False      # don't reset the board when opening
            s.open()
            try:
                s.set_buffer_size(rx_size=1 << 20)          # Windows default (4 KB) overflows and mangles lines
            except Exception:
                pass
            print(f"reading serial CSI from {port}", flush=True)
            state = {"last": time.time(), "alive": True}

            def watchdog(conn=s, st=state):
                while st["alive"]:
                    time.sleep(1)
                    if st["alive"] and time.time() - st["last"] > 5:
                        print(f"serial {port}: no data for 5 s, force-reopening", flush=True)
                        st["alive"] = False
                        try:
                            conn.cancel_read()
                        except Exception:
                            pass
                        try:
                            conn.close()
                        except Exception:
                            pass

            threading.Thread(target=watchdog, daemon=True).start()
            pending, lines, report = bytearray(), 0, time.time()
            while state["alive"]:
                chunk = s.read(s.in_waiting or 1)
                now = time.time()
                if chunk:
                    state["last"] = now
                    pending.extend(chunk)
                    while b"\n" in pending:
                        line, _, rest = pending.partition(b"\n")
                        pending = bytearray(rest)
                        lines += 1
                        handle_serial_line(rx, port, bytes(line), gateway)
                    if len(pending) > 4096:
                        pending.clear()
                if now - report > 10:
                    print(f"serial {port}: {lines / (now - report):.1f} lines/s, gateway matched "
                          f"{GATEWAY_STATS['ok']}, unmatched {GATEWAY_STATS['bad']}", flush=True)
                    lines, report = 0, now
            state["alive"] = False
        except Exception as e:
            print(f"serial {port}: {e}; retrying in 2 s", flush=True)
            time.sleep(2)
        finally:
            try:
                if s is not None:
                    s.close()
            except Exception:
                pass


# --------------------------------------------------------------------------------------- features

_last_feat = {}


def link_feature(link, t_end):
    w = link.window(t_end)
    if w is None:
        return None
    return np.concatenate([w.mean(0), w.std(0), np.abs(np.diff(w, axis=0)).mean(0)])


def feature(rx, ids, t_end, max_stale=3.0):
    """Concatenated per-link features, or None if a link has been silent for more than max_stale s."""
    parts = []
    for k in ids:
        l = rx.links.get(k)
        f = link_feature(l, t_end) if l else None
        if f is not None:
            _last_feat[k] = (t_end, f)
        elif k in _last_feat and t_end - _last_feat[k][0] < max_stale:
            f = _last_feat[k][1]
        else:
            return None
        parts.append(f)
    return np.concatenate(parts).astype(np.float32)


# ----------------------------------------------------------------------------------------- camera

class Camera:
    """Labels posted by the training page (~10/s) and fall events with their start/end times."""

    def __init__(self):
        self.hist = deque(maxlen=400)
        self.falls = deque(maxlen=50)
        self.last_post = 0.0
        self.lock = threading.Lock()

    def add(self, label, fall_ago=None):
        now = time.time()
        with self.lock:
            self.last_post = now
            self.hist.append((now, label if label in LABELS else "unsure"))
            if fall_ago:
                a, b = float(fall_ago[0]), float(fall_ago[1])
                self.falls.append((now - max(a, b), now - min(a, b)))

    def label(self, t_end, win=WIN, agree=0.6):
        with self.lock:
            L = [l for t, l in self.hist if t_end - win < t <= t_end]
            falls = list(self.falls)
        for a, b in falls:                                # a fall overlapping >= 0.5 s of the window wins
            if min(b, t_end) - max(a, t_end - win) >= 0.5:
                return "fall"
        if len(L) < 5:
            return None
        lab = max(set(L), key=L.count)
        return lab if lab != "unsure" and L.count(lab) / len(L) >= agree else None

    def latest(self, now):
        with self.lock:
            return (self.hist[-1][1], now - self.hist[-1][0]) if self.hist else (None, None)


# ------------------------------------------------------------------------------------------ model

def knn(Z, y, z, k=7):
    d = np.linalg.norm(Z - z, axis=1)
    nn = np.argsort(d)[:k]
    vals, cnt = np.unique(y[nn], return_counts=True)
    return dict(zip(vals.tolist(), (cnt / cnt.sum()).tolist()))


def predict(Z, y, Q, k=7):
    out = []
    for q in Q:
        p = knn(Z, y, q, k)
        out.append(max(p, key=p.get))
    return np.array(out)


def balanced(mask, y, cap=4.0, seed=0):
    """Subset of a boolean mask where no class has more than cap x the smallest class's windows.
    The lying-focused routine records ~7x more lying than standing; unbalanced, kNN then calls
    standing 'lying' (a 4 s false run on the Nov 14 test round). Deterministic (fixed seed)."""
    idx = np.where(mask)[0]
    if not len(idx):
        return mask
    labs, cnt = np.unique(y[idx], return_counts=True)
    limit = int(cap * cnt.min())
    rng = np.random.default_rng(seed)
    keep = []
    for l in labs:
        li = idx[y[idx] == l]
        keep.append(li if len(li) <= limit else np.sort(rng.choice(li, limit, replace=False)))
    out = np.zeros_like(mask)
    out[np.concatenate(keep)] = True
    return out


def training_label(y_cam, y_prompt):
    """Label used for training: the camera's, if the movement page's prompt allows it ('' otherwise).
    Free recording (no prompt) uses the camera label as is."""
    if not y_cam:
        return ""
    if not y_prompt:
        return y_cam
    # Team decision (Nov 14): sitting on a chair and squatting are ONE class. The camera often reads
    # a squat as "standing", so under the sit/squat prompt standing also counts as sitting.
    if y_prompt == "sitting" and y_cam in ("sitting", "standing"):
        return "sitting"
    # 4-class routine: while asked to lie down, the camera may read curled-up / propped poses as
    # "sitting"; the person is on the floor, so that counts as lying.
    if y_prompt == "lying" and y_cam in ("lying", "sitting"):
        return "lying"
    return y_cam if y_cam in ACCEPT.get(y_prompt, set()) else ""


class Dataset:
    """Windows: WiFi feature, camera label, prompt, session ('train'|'test'), round, take."""

    def __init__(self):
        self.X, self.cam, self.prompt, self.sess, self.rnd, self.take, self.t = [], [], [], [], [], [], []
        self.ids = None
        self.rec = None
        self.model = None
        self.recent = deque(maxlen=6)     # last 3 s of probabilities (live smoothing)
        self.lock = threading.Lock()
        if os.path.exists(DATASET):
            d = np.load(DATASET, allow_pickle=False)
            self.X = list(d["X"])
            self.cam, self.prompt, self.sess = list(map(str, d["cam"])), list(map(str, d["prompt"])), list(map(str, d["sess"]))
            self.rnd, self.take, self.t = list(map(int, d["rnd"])), list(map(int, d["take"])), list(map(float, d["t"]))
            self.ids = [str(i) for i in d["ids"]] or None
            self.train()

    def save(self):
        os.makedirs(DATA, exist_ok=True)
        tmp = DATASET + ".tmp.npz"
        np.savez(tmp, X=np.array(self.X, np.float32).reshape(len(self.X), -1) if self.X else np.zeros((0, 0), np.float32), cam=np.array(self.cam, dtype=str),
                 prompt=np.array(self.prompt, dtype=str), sess=np.array(self.sess, dtype=str),
                 rnd=np.array(self.rnd, np.int32), take=np.array(self.take, np.int32), t=np.array(self.t),
                 ids=np.array(self.ids or [], dtype=str))
        os.replace(tmp, DATASET)

    # -- recording
    def start(self, rx, body):
        with self.lock:
            now = time.time()
            if not body.get("on"):
                raw_log_close()
                if self.rec:
                    self.rec = None
                    self.save()
                    self.train()
                return None
            ids = rx.active_links(now)
            if not ids:
                return "no links are streaming (check the boards and that this computer is the UDP target)"
            if self.ids and not set(self.ids) <= set(rx.active_links(now, min_pps=0.5)):
                return f"links changed: recorded with {self.ids}, now {ids}. Clear the dataset or restore the boards."
            self.ids = self.ids or ids
            take = (max(self.take) + 1) if self.take else 1
            self.rec = {"session": body.get("session", "train"), "round": int(body.get("round", 1)),
                        "prompt": body.get("prompt") or "", "take": take, "n": 0, "skipped": 0,
                        "paused": bool(body.get("prompt"))}   # guided sessions start in a countdown
            raw_log_open(f"{self.rec['session']}-r{self.rec['round']}")
            RAW_LOG["prompt"], RAW_LOG["paused"] = self.rec["prompt"], self.rec["paused"]
            return None

    def set_prompt(self, prompt, paused=False):
        """Guided recording: the page reports the current prompt; paused = countdown before a step.
        Each recorded step (pause -> record) becomes its own take."""
        with self.lock:
            r = self.rec
            if not r:
                return
            paused = bool(paused)
            if r.get("paused") and not paused:
                r["take"] = max(self.take + [r["take"]]) + 1
            r["prompt"], r["paused"] = prompt or "", paused
            RAW_LOG["prompt"], RAW_LOG["paused"] = r["prompt"], paused

    def tick(self, rx, cam, now):
        with self.lock:
            if not self.rec or self.rec.get("paused"):
                return
            t_end = now - LAG
            y = cam.label(t_end)
            f = feature(rx, self.ids, t_end)
            if f is None or y is None:
                self.rec["skipped"] += 1
                return
            r = self.rec
            self.X.append(f); self.cam.append(y); self.prompt.append(r["prompt"]); self.sess.append(r["session"])
            self.rnd.append(r["round"]); self.take.append(r["take"]); self.t.append(t_end)
            r["n"] += 1
            if r["n"] % 20 == 0:
                self.save()

    def clear(self, session=None):
        with self.lock:
            keep = [i for i, s in enumerate(self.sess) if session and s != session]
            for name in ("X", "cam", "prompt", "sess", "rnd", "take", "t"):
                setattr(self, name, [getattr(self, name)[i] for i in keep])
            if not self.X:
                self.ids = None
            self.rec = None
            self.save()
            self.train()

    # -- training and honest scores
    def arrays(self):
        X = np.array(self.X, np.float32).reshape(len(self.X), -1)
        y = np.array([training_label(c, p) for c, p in zip(self.cam, self.prompt)], dtype=object)
        return X, y, np.array(self.sess), np.array(self.rnd)

    CAL_ROUND = 99     # calibration windows: session "train", round 99; each calibration replaces the last
    CAL_ROUNDS = {"empty": 99, "standing": 96, "walking": 95, "lying": 94}   # one round per calibrated state
    CAL_WEIGHT = 3     # calibration windows count 3x (fresh, exact demo conditions) so old rounds can't outvote them

    def calibrate_empty(self, rx, seconds=20.0, countdown=5.0, label="empty", session="train", rnd=None):
        """Demo 'Calibrate empty room': after a countdown (people leave), record `seconds` of the
        empty room live, replace the previous calibration and retrain. Runs in its own thread."""
        rnd = self.CAL_ROUND if rnd is None else rnd
        st = self.cal = {"phase": "countdown", "ends": time.time() + countdown, "n": 0, "error": None,
                         "label": label, "session": session}
        time.sleep(countdown)
        ids = self.ids or rx.active_links(time.time())
        if not ids:
            st.update(phase="error", ends=time.time() + 3, error="no links streaming")
            return
        st.update(phase="recording", ends=time.time() + seconds)
        X, ts = [], []
        while time.time() < st["ends"]:
            t_end = time.time() - 0.1
            f = feature(rx, ids, t_end)
            if f is not None:
                X.append(f); ts.append(t_end); st["n"] = len(X)
            time.sleep(HOP)
        if len(X) < 5:
            st.update(phase="error", ends=time.time() + 3, error=f"only {len(X)} windows (links dropping?)")
            return
        with self.lock:
            keep = [i for i, r in enumerate(self.rnd) if not (r == rnd and self.sess[i] == session)]
            for name in ("X", "cam", "prompt", "sess", "rnd", "take", "t"):
                setattr(self, name, [getattr(self, name)[i] for i in keep])
            self.ids = self.ids or ids
            take = (max(self.take) + 1) if self.take else 1
            for f, t in zip(X, ts):
                self.X.append(f); self.cam.append(label); self.prompt.append(label); self.sess.append(session)
                self.rnd.append(rnd); self.take.append(take); self.t.append(t)
            self.save()
            self.train()
        st.update(phase="done", ends=time.time())
        print(f"recorded {label} ({session}, round {rnd}): {len(X)} windows", flush=True)

    def train(self):
        if not self.X:
            self.model = None
            return
        X, y, sess, rnd = self.arrays()
        ok = y != ""
        tr, te = ok & (sess == "train"), ok & (sess == "test")
        if tr.sum() < 10 or len(set(y[tr])) < 2:
            self.model = None
            return
        n_train = int(tr.sum())
        cal = tr & np.isin(rnd, list(self.CAL_ROUNDS.values()))
        # a calibrated state uses ONLY its latest calibration run: old training windows of that state are dropped
        tr = tr & (cal | ~np.isin(y, list(set(y[cal]))))
        tr = balanced(tr & ~cal, y) | cal                  # cap majority classes at 4x the smallest (2x starved lying on setup 4; host/cap_sweep.py)
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
        Z = (X - mu) / sd
        labels = sorted(set(y[tr]))
        use = np.concatenate([np.where(tr & ~cal)[0]] + [np.where(cal)[0]] * self.CAL_WEIGHT)
        test = None
        if te.any():
            p = predict(Z[use], y[use], Z[te])
            yt = y[te]
            test = {"acc": float((p == yt).mean()), "n": int(te.sum()),
                    "per_class": {l: float((p[yt == l] == l).mean()) for l in sorted(set(yt))},
                    "confusion": {l: {q: int(((yt == l) & (p == q)).sum()) for q in labels} for l in sorted(set(yt))}}
        lor = None
        rounds = sorted(set(rnd[tr & ~cal].tolist()))
        if len(rounds) >= 2:
            hits = []
            for r in rounds:
                a, b = balanced(ok & (sess == "train") & ~cal & (rnd != r), y), ok & (sess == "train") & (rnd == r)
                if len(set(y[a])) >= 2 and b.any():
                    hits += list(predict(Z[a], y[a], Z[b]) == y[b])
            lor = float(np.mean(hits)) if hits else None
        counts = {s: {l: int(((sess == s) & (y == l)).sum()) for l in LABELS} for s in ("train", "test")}
        cal_counts = {l: int((cal & (y == l)).sum()) for l in LABELS if (cal & (y == l)).any()}
        self.model = {"mu": mu, "sd": sd, "Z": Z[use], "y": y[use], "labels": labels, "calibrated": cal_counts, "test": test, "lor": lor,
                      "counts": counts, "dropped": int((~ok).sum())}
        self.write_metrics()

    def write_metrics(self):
        m = self.model
        out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": "k-nearest neighbours (k=7) on standardised WiFi CSI features",
               "links": self.ids, "labels": m["labels"], "train_windows": int(len(m["y"])),
               "test_session": m["test"], "leave_one_round_out_acc": m["lor"], "counts": m["counts"],
               "windows_dropped_camera_disagreed": m["dropped"],
               "split": "test = a separately recorded session; never windows sampled from the training recordings",
               "chance_acc": 1.0 / len(m["labels"])}
        os.makedirs(DATA, exist_ok=True)
        with open(METRICS, "w") as f:
            json.dump(out, f, indent=1)

    def estimate(self, rx, now):
        m = self.model
        if not m or not self.ids:
            return None
        f = feature(rx, self.ids, now)
        if f is None:
            return {"status": "waiting for links", "missing": [k for k in self.ids if k not in rx.active_links(now, 0.5)]}
        p = knn(m["Z"], m["y"], (f - m["mu"]) / m["sd"])
        self.recent.append(p)
        probs = {l: float(np.mean([q.get(l, 0.0) for q in self.recent])) for l in m["labels"]}
        best = max(probs, key=probs.get)
        return {"status": "ok" if probs[best] >= 0.5 else "unsure", "best": best, "confidence": probs[best],
                "probs": probs, "raw": p}

    def summary(self):
        m = self.model or {}
        counts = {}
        for s, c, p in zip(self.sess, self.cam, self.prompt):
            lab = training_label(c, p)
            if lab:
                counts.setdefault(s, {}).setdefault(lab, 0)
                counts[s][lab] += 1
        return {"counts": counts, "calibrated": m.get("calibrated"), "ids": self.ids, "recording": dict(self.rec) if self.rec else None,
                "test": m.get("test"), "lor": m.get("lor"), "trained": bool(self.model), "total": len(self.X)}


# -------------------------------------------------------------------------------- live detection

def push_phone(cfg, test=False):
    """Phone notification through ntfy (https://ntfy.sh): install the ntfy app, subscribe to the topic
    in config.yaml (notify.ntfy_topic). Fire-and-forget in a thread so the detector never blocks.
    Returns the send time (shown on the demo screen), or None if no topic is configured."""
    n = cfg.get("notify") or {}
    topic = n.get("ntfy_topic")
    if not topic:
        return None
    room = cfg.get("room", {}).get("name", "the room")
    title = "TEST: fall alert" if test else f"Fall detected in {room}"
    msg = n.get("message", "Check on patient.")

    def send():
        import urllib.request
        try:
            req = urllib.request.Request(f"{n.get('ntfy_server', 'https://ntfy.sh')}/{topic}", data=msg.encode(),
                                         headers={"Title": title, "Priority": "urgent", "Tags": "rotating_light"})
            urllib.request.urlopen(req, timeout=5).read()
            print(f"phone notification sent: {title}", flush=True)
        except Exception as e:
            print(f"phone notification failed: {e}", flush=True)

    threading.Thread(target=send, daemon=True).start()
    return time.time()


class Detector:
    """Fall / long-lie state machine on top of the WiFi activity estimate.

    active ──(fall detected, or active→lying within a few seconds)──▶ fall_suspected
    fall_suspected ──(still lying for long_lie_seconds)──▶ alert   (stays until the person is up or staff acknowledge)
    While someone is on the floor, "empty" predictions are read as "lying": a person cannot leave
    the room without first getting up.
    """

    def __init__(self, cfg):
        d = cfg.get("detection") or {}
        self.cfg = cfg
        self.last_push = None
        self.armed = False          # phone push only while the demo screen is started (Start -> /api/reset)
        self.long_lie = float(d.get("long_lie_seconds", 10))
        self.recover = float(d.get("recover_seconds", 3))
        self.alert_any_lying = bool(d.get("alert_on_any_lying", False))
        self.drop_window = float(d.get("drop_seconds", 2.5))   # active -> lying faster than this counts as a fall
        self.state, self.since = "unknown", time.time()
        self.lying_since = self.fall_time = self.last_active = self.up_since = None
        self.acked = False
        self.events = deque(maxlen=50)

    def _go(self, state, now, note=""):
        if state != self.state:
            self.state, self.since = state, now
            self.events.appendleft({"t": now, "state": state, "note": note})
            if state == "alert" and self.armed:
                self.last_push = push_phone(self.cfg)

    def update(self, est, now):
        if not est or est.get("status") not in ("ok", "unsure"):
            return
        best, raw = est["best"], est.get("raw", {})
        on_floor = self.state in ("fall_suspected", "alert")
        if best == "empty" and on_floor:
            best = "lying"
        if raw.get("fall", 0) >= 0.5 and self.state != "alert":
            self.fall_time = now
        if best in ACTIVE:
            self.last_active = now
            self.up_since = self.up_since or now
        else:
            self.up_since = None
        if best in ("lying", "fall"):
            self.lying_since = self.lying_since or now
            if not on_floor:
                recent_fall = self.fall_time and now - self.fall_time < 6
                dropped = self.last_active and self.lying_since - self.last_active < self.drop_window
                if recent_fall or dropped or self.alert_any_lying:
                    self.fall_time = self.fall_time or now
                    self.acked = False
                    self._go("fall_suspected", now, "possible fall")
                else:
                    self._go("lying", now)
            elif self.state == "fall_suspected" and now - self.lying_since >= self.long_lie:
                self._go("alert", now, f"on the floor for {self.long_lie:.0f}s")
            return
        if self.state == "alert" and not self.acked:
            return                                       # a FALL ALERT stays until staff acknowledge it:
                                                         # limb movement on the floor can read as "walking"
        if on_floor and not (self.up_since and now - self.up_since >= self.recover):
            return                                       # brief flicker: stay on the floor
        self.lying_since = None
        if best == "empty":
            self._go("empty", now)
        else:
            self._go("active", now, best)
        if self.state != "alert":
            self.fall_time = None

    def reset(self, now):
        """Demo screen Start/Reset: forget any fall in progress and start watching fresh."""
        self.lying_since = self.fall_time = self.last_active = self.up_since = self.last_push = None
        self.acked = False
        self.state, self.since = "unknown", now
        self.armed = True
        self.events.appendleft({"t": now, "state": "reset", "note": "demo reset"})

    def ack(self, now):
        self.acked = True
        self.events.appendleft({"t": now, "state": self.state, "note": "acknowledged by staff"})

    def summary(self, now):
        return {"state": self.state, "since": self.since, "for_s": now - self.since,
                "on_floor_s": (now - self.lying_since) if self.lying_since and self.state in ("fall_suspected", "alert") else None,
                "fall_time": self.fall_time, "acknowledged": self.acked, "pushed": self.last_push, "long_lie_s": self.long_lie,
                "events": list(self.events)[:12]}


# -------------------------------------------------------------------------------------------- web

def make_handler(app):
    class H(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".wasm": "application/wasm"}

        def __init__(self, *a, **k):
            super().__init__(*a, directory=WEB, **k)

        def log_message(self, *a):
            pass

        def end_headers(self):
            if self.path.startswith("/api/"):
                self.send_header("Access-Control-Allow-Origin", "*")   # the caregiver dashboard reads /api/live
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_json(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/state":
                return self.send_json(app.state())
            if path == "/api/live":
                return self.send_json(app.live())
            return super().do_GET()

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError:
                return self.send_json({"ok": False, "error": "bad json"}, 400)
            if path == "/api/pose":
                app.camera.add(str(body.get("label", "unsure")), body.get("fall_ago"))
                if "prompt" in body:
                    app.data.set_prompt(body.get("prompt"), body.get("paused"))
                return self.send_json({"ok": True})
            if path == "/api/rec":
                err = app.data.start(app.rx, body)
                return self.send_json({"ok": not err, "error": err}, 400 if err else 200)
            if path == "/api/clear":
                app.data.clear(body.get("session"))
                return self.send_json({"ok": True})
            if path == "/api/notify_test":
                t = push_phone(app.cfg, test=True)
                return self.send_json({"ok": bool(t), "error": None if t else "no notify.ntfy_topic in config.yaml"})
            if path == "/api/calibrate":
                c = getattr(app.data, "cal", None)
                if c and c["phase"] in ("countdown", "recording"):
                    return self.send_json({"ok": False, "error": "already calibrating"})
                secs = float(body.get("seconds", 20))
                # label/session/round: re-record one class only, e.g. {"label":"standing","round":98}
                lbl = body.get("label", "empty")
                args = (app.rx, secs, float(body.get("countdown", 5)), lbl,
                        body.get("session", "train"), body.get("round", Dataset.CAL_ROUNDS.get(lbl)))
                threading.Thread(target=app.data.calibrate_empty, args=args, daemon=True).start()
                return self.send_json({"ok": True})
            if path == "/api/disarm":
                app.detector.armed = False
                return self.send_json({"ok": True})
            if path == "/api/reset":
                app.detector.reset(time.time())
                return self.send_json({"ok": True})
            if path == "/api/ack":
                app.detector.ack(time.time())
                return self.send_json({"ok": True})
            return self.send_json({"ok": False, "error": "not found"}, 404)
    return H


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rx = Receiver(cfg)
        self.camera = Camera()
        self.data = Dataset()
        self.detector = Detector(cfg)
        self.est = None
        self.started = time.time()

    def loop(self):
        while True:
            now = time.time()
            for name, fn in (("recording", lambda: self.data.tick(self.rx, self.camera, now)),
                             ("estimate", lambda: setattr(self, "est", self.data.estimate(self.rx, now))),
                             ("detector", lambda: self.detector.update(self.est, now)),
                             ("live log", lambda: self.log_live(now))):
                try:
                    fn()
                except Exception as e:  # never let the loop die silently
                    print(f"{name} error: {e!r}", flush=True)
            time.sleep(HOP)

    def log_live(self, now):
        """One row per tick (0.5 s) to data/live-log-<date>.csv: what the model saw and what the
        alert logic decided, so a live test can be reviewed afterwards."""
        est = getattr(self, "est", None) or {}
        probs = est.get("probs") or {}
        if not hasattr(self, "_live_log"):
            os.makedirs(DATA, exist_ok=True)
            path = os.path.join(DATA, f"live-log-{time.strftime('%Y%m%d')}.csv")
            new = not os.path.exists(path)
            self._live_log = open(path, "a", buffering=1)
            if new:
                self._live_log.write("t,clock,state,best,confidence,p_empty,p_standing,p_walking,p_sitting,p_lying,status,pps\n")
        pps = "|".join(f"{k}:{self.rx.links[k].stats(now)['pps']:.0f}" for k in sorted(self.rx.links))
        self._live_log.write(f"{now:.2f},{time.strftime('%H:%M:%S')},{self.detector.state},{est.get('best', '')},"
                             f"{est.get('confidence', 0):.2f}," + ",".join(f"{probs.get(k, 0):.2f}" for k in
                             ("empty", "standing", "walking", "sitting", "lying")) + f",{est.get('status', '')},{pps}\n")

    def signal_ok(self, now):
        return any(l.stats(now)["pps"] >= 2 for l in list(self.rx.links.values()))

    def live(self):
        """Compact status for the caregiver dashboard. mode is LIVE only while real frames arrive."""
        now = time.time()
        est = self.est or {}
        return {"mode": "LIVE" if self.signal_ok(now) else "NO_SIGNAL", "room": self.cfg["room"].get("name", "Room"),
                "t": now, "activity": est.get("best"), "confidence": est.get("confidence"),
                "model_trained": bool(self.data.model), **self.detector.summary(now)}

    def state(self):
        now = time.time()
        with self.rx.lock:
            links = dict(self.rx.links)
        est = dict(self.est) if self.est else None
        if est:
            est.pop("raw", None)
        lab, age = self.camera.latest(now)
        boards = {str(b["id"]): b["name"] for b in self.cfg["boards"]}
        return {"t": now, "links": {k: l.stats(now) for k, l in sorted(links.items())},
                "nodes": {str(k): {**v, "age": now - v.get("seen", now)} for k, v in sorted(self.rx.nodes.items())},
                "boards": boards, "data": self.data.summary(), "estimate": est,
                "camera": {"label": lab, "age": age}, "live": self.live(),
                "calibration": getattr(self.data, "cal", None)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", action="append", default=[], help="also read CSI lines from this serial port")
    ap.add_argument("--gateway", help="Arduino RELAY/PEER gateway port, at 460800 baud")
    ap.add_argument("--baud", type=int, default=921600)
    ap.add_argument("--config")
    ap.add_argument("--host", default="127.0.0.1", help="HTTP bind address (use 0.0.0.0 to share on the LAN)")
    a = ap.parse_args()
    cfg = havenconfig.load(a.config)
    app = App(cfg)
    if a.gateway:
        threading.Thread(target=serial_loop, args=(app.rx, a.gateway, 460800, True), daemon=True).start()
    threading.Thread(target=udp_loop, args=(app.rx, cfg["host"]["udp_port"]), daemon=True).start()
    for p in a.serial:
        threading.Thread(target=serial_loop, args=(app.rx, p, a.baud), daemon=True).start()
    threading.Thread(target=app.loop, daemon=True).start()
    srv = ThreadingHTTPServer((a.host, cfg["host"]["http_port"]), make_handler(app))
    print(f"UDP {cfg['host']['udp_port']} (boards send to {cfg['host']['ip']}) · open http://127.0.0.1:{cfg['host']['http_port']}",
          flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
