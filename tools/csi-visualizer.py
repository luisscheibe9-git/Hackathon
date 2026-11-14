import argparse
from collections import deque
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import queue
import re
import socket
import statistics
import threading
import time
import tkinter as tk
import webbrowser

import serial


FRAME = re.compile(rb"CSI,\d+,(-?\d+),[01],([0-9a-f]{256})")
JOIN = re.compile(rb"JOINED ip=([\d.]+) .*channel=(\d+) rssi=-?\d+")


def amplitude(raw):
    values = bytes.fromhex(raw.decode())
    signed = [value if value < 128 else value - 256 for value in values]
    magnitudes = [math.hypot(i, q) for i, q in zip(signed[4::2], signed[5::2])]
    total = sum(magnitudes)
    return [value / total for value in magnitudes] if total else None


def read_board(port_name, network, password, updates, stop, external_traffic=False):
    try:
        with serial.Serial(port_name, 460800, timeout=0.03) as port, socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        ) as traffic:
            port.dtr = False
            port.rts = True
            time.sleep(0.15)
            port.rts = False
            time.sleep(1.25)
            port.reset_input_buffer()
            port.write(f"{network}\n{password}\n".encode())
            deadline = time.monotonic() + 30
            target = None
            pending = bytearray()
            previous = None
            next_packet = 0.0
            while not stop.is_set():
                now = time.monotonic()
                if now > deadline:
                    raise RuntimeError("No network connection reported" if target is None else
                                       "No CSI frames recently. Reconnecting.")
                if target and not external_traffic and now >= next_packet:
                    traffic.sendto(b"CSI", target)
                    next_packet = now + 0.035
                pending.extend(port.read(port.in_waiting or 1))
                while b"\n" in pending:
                    raw, _, rest = pending.partition(b"\n")
                    pending = rest
                    line = raw.strip()
                    joined = JOIN.fullmatch(line)
                    if joined:
                        target = (joined[1].decode(), 50000)
                        deadline = time.monotonic() + 12
                        updates.put((port_name, "status", f"Channel {joined[2].decode()} · waiting for CSI"))
                    if line.startswith((b"JOIN_FAILED", b"CSI_INIT_FAILED")):
                        raise RuntimeError(line.decode())
                    frame = FRAME.fullmatch(line)
                    if frame:
                        deadline = time.monotonic() + 12
                        current = amplitude(frame[2])
                        if current is None:
                            continue
                        if previous is not None:
                            change = sum(abs(a - b) for a, b in zip(current, previous))
                            updates.put((port_name, "frame", (time.monotonic(), change, int(frame[1]))))
                        previous = current
                if len(pending) > 2048:
                    pending.clear()
    except (OSError, RuntimeError, serial.SerialException) as error:
        updates.put((port_name, "status", str(error)))


def run_observatory(ports, updates, stop):
    frames = {port: deque(maxlen=3500) for port in ports}
    status = dict.fromkeys(ports, "Connecting")
    state = b"[]"

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/live":
                payload = state
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                super().do_GET()

        def log_message(self, *_):
            pass

    assets = Path(__file__).with_name("observatory")
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=assets)) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"Stillpoint Observatory: {url}", flush=True)
        webbrowser.open(url)
        try:
            while not stop.wait(0.15):
                while not updates.empty():
                    port, kind, value = updates.get()
                    if kind == "frame":
                        frames[port].append(value)
                    else:
                        status[port] = value
                now = time.monotonic()
                snapshot = []
                for port, history in frames.items():
                    while history and history[0][0] < now - 30:
                        history.popleft()
                    recent = [frame for frame in history if frame[0] >= now - 2]
                    motion = statistics.median(frame[1] for frame in recent) if recent else None
                    snapshot.append({
                        "port": port, "motion": motion,
                        "rssi": recent[-1][2] if recent else None,
                        "rate": len(recent) / 2,
                        "status": "Streaming" if recent else ("Stream paused" if history else status[port]),
                        "samples": [[round(now - t, 2), round(change, 4)] for t, change, _ in history],
                    })
                state = json.dumps(snapshot).encode()
        finally:
            server.shutdown()


def reconnect_board(port, network, password, updates, stop, external_traffic):
    while not stop.is_set():
        read_board(port, network, password, updates, stop, external_traffic)
        stop.wait(3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("network")
    parser.add_argument("ports", nargs="+")
    parser.add_argument("--observatory", action="store_true")
    parser.add_argument("--external-traffic", action="store_true",
                        help="Use packets from a dedicated transmitter instead of host probes.")
    args = parser.parse_args()
    password = input().rstrip("\r\n")
    updates = queue.SimpleQueue()
    stop = threading.Event()
    if args.observatory:
        for port in args.ports:
            threading.Thread(target=reconnect_board,
                             args=(port, args.network, password, updates, stop, args.external_traffic),
                             daemon=True).start()
        try:
            run_observatory(args.ports, updates, stop)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
        return

    root = tk.Tk()
    root.title("Stillpoint · Live Wi-Fi Sensing")
    root.geometry("960x630")
    root.minsize(610, 350)
    root.configure(bg="#121a20")
    tk.Label(root, text="Live Wi-Fi Sensing", font=("Segoe UI", 23, "bold"),
             fg="#edf4f5", bg="#121a20").pack(anchor="w", padx=28, pady=(22, 4))
    tk.Label(root, text="CSI change · last 30 seconds", font=("Segoe UI", 11),
             fg="#a8bdc6", bg="#121a20").pack(anchor="w", padx=30, pady=(0, 16))

    panels = {}
    for port in args.ports:
        card = tk.Frame(root, bg="#1b2830")
        card.pack(fill="both", expand=True, padx=27, pady=(0, 14))
        title = tk.Label(card, text=f"{port}  ·  Connecting", font=("Segoe UI", 12, "bold"),
                         fg="#edf4f5", bg="#1b2830", anchor="w")
        title.pack(fill="x", padx=15, pady=(10, 2))
        plot = tk.Canvas(card, bg="#1b2830", highlightthickness=0)
        plot.pack(fill="both", expand=True, padx=12, pady=(0, 9))
        panels[port] = (title, plot, deque(maxlen=3500))
        threading.Thread(target=read_board,
                         args=(port, args.network, password, updates, stop, args.external_traffic),
                         daemon=True).start()

    def refresh():
        now = time.monotonic()
        while not updates.empty():
            port, kind, value = updates.get()
            title, _, frames = panels[port]
            if kind == "frame":
                frames.append(value)
            else:
                title.configure(text=f"{port}  ·  {value}")
        for port, (title, plot, frames) in panels.items():
            while frames and frames[0][0] < now - 30:
                frames.popleft()
            recent = [frame for frame in frames if frame[0] >= now - 2]
            if recent:
                median = statistics.median(frame[1] for frame in recent)
                title.configure(text=f"{port}   ·   CSI change {median:.3f}   ·   "
                                     f"{len(recent) / 2:.1f} frames/s   ·   {recent[-1][2]} dBm")
            elif frames:
                title.configure(text=f"{port}  ·  CSI stream paused")
            plot.delete("trace")
            width, height = plot.winfo_width(), plot.winfo_height()
            if width < 80 or height < 45:
                continue
            left, top, right, bottom = 44, 12, width - 12, height - 24
            scale = max(0.4, max((frame[1] for frame in frames), default=0))
            for fraction in (0, 0.5, 1):
                y = bottom - fraction * (bottom - top)
                plot.create_line(left, y, right, y, fill="#32434c", tags="trace")
                plot.create_text(left - 6, y, anchor="e", text=f"{scale * fraction:.2f}",
                                 fill="#adc0c8", tags="trace")
            for seconds in (30, 20, 10, 0):
                x = right - seconds * (right - left) / 30
                plot.create_text(x, bottom + 13, text=f"{seconds}s", fill="#adc0c8", tags="trace")
            if len(frames) > 1:
                points = [(right - (now - t) * (right - left) / 30,
                           bottom - change / scale * (bottom - top)) for t, change, _ in frames]
                plot.create_line(points, fill="#70e2cd", width=2, tags="trace")
        root.after(200, refresh)

    root.after(0, refresh)
    try:
        root.mainloop()
    finally:
        stop.set()


if __name__ == "__main__":
    main()
