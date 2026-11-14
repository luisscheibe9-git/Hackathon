#!/usr/bin/env python3
"""Build, flash and set up Haven CSI nodes (classic ESP32 / ESP32-WROOM-32U).

  python tools/haven_fw.py discover            list boards on USB with their MACs (paste into config.yaml)
  python tools/haven_fw.py build               compile firmware/haven-csi-node with ESP-IDF
  python tools/haven_fw.py flash               flash + provision every configured board that is plugged in
  python tools/haven_fw.py flash --app-only    flash the program only, keep Wi-Fi/node settings
  python tools/haven_fw.py provision           (re)write Wi-Fi + node settings only (no reflash)
  python tools/haven_fw.py check               reset each board and report Wi-Fi, router and CSI yield
  python tools/haven_fw.py monitor [--port P]  show a board's log (CSI lines are counted, not printed)

Boards are matched by MAC, so it doesn't matter which USB port each one is on.
The Wi-Fi password is read from a file (wifi.password_file) and only ever written into the board's
NVS partition; it is never printed, and temporary files are deleted.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ESP32_DIR = os.path.dirname(HERE)
sys.path.insert(0, ESP32_DIR)
import havenconfig  # noqa: E402

PROJECT = os.path.join(ESP32_DIR, "firmware", "haven-csi-node")
BUILD = os.path.join(PROJECT, "build")
NVS_OFFSET, NVS_SIZE = 0x9000, 0x6000
BAUD_LOG = 921600
USB_BRIDGES = {(0x10C4, 0xEA60): "CP210x", (0x1A86, 0x7523): "CH340", (0x1A86, 0x55D4): "CH9102",
               (0x0403, 0x6001): "FTDI", (0x0403, 0x6010): "FTDI"}


# ----------------------------------------------------------------------------------------- serial

def serial_mod():
    try:
        import serial
        from serial.tools import list_ports
        return serial, list_ports
    except ImportError:
        sys.exit("pyserial missing: pip install pyserial")


def ports(only=None):
    _, list_ports = serial_mod()
    out = []
    for p in list_ports.comports():
        if only and p.device != only:
            continue
        if only or (p.vid, p.pid) in USB_BRIDGES:
            out.append(p.device)
    return out


def esptool(*args, port=None, capture=True):
    cmd = [sys.executable, "-m", "esptool", "--chip", "esp32"]
    if port:
        cmd += ["--port", port]
    cmd += list(args)
    r = subprocess.run(cmd, capture_output=capture, text=True)
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


def mac_of(port):
    ok, out = esptool("--after", "hard-reset", "read-mac", port=port)
    m = re.search(r"MAC:\s+([0-9a-fA-F:]{17})", out)
    return m.group(1).lower() if m else None


def open_port(port, baud=BAUD_LOG):
    serial, _ = serial_mod()
    s = serial.Serial(baudrate=baud, timeout=0.2)
    s.port = port
    s.dtr = False   # keep GPIO0 high: never drop into download mode
    s.rts = False
    s.open()
    return s


def reset(s):
    s.rts = True    # EN low
    time.sleep(0.12)
    s.rts = False


def read_boot(port, seconds=20, until=re.compile(rb"yield=")):
    s = open_port(port)
    try:
        reset(s)
        buf, t0 = b"", time.time()
        while time.time() - t0 < seconds:
            buf += s.read(4096)
            joined = buf.rfind(b"HAVEN_JOINED")
            if joined >= 0 and until.search(buf, joined):
                time.sleep(0.2)
                buf += s.read(4096)
                break
        return buf.decode(errors="replace")
    finally:
        s.close()


# ------------------------------------------------------------------------------------------ build

def idf_env_cmd(c, cmd):
    idf = c["firmware"]["idf_path"]
    if not os.path.exists(os.path.join(idf, "export.sh")):
        sys.exit(f"ESP-IDF not found at {idf}: install v5.4+ or set firmware.idf_path in config.yaml")
    # cmake/ninja may live next to this Python (pip-installed) rather than in the IDF tools dir
    extra = os.path.dirname(sys.executable)
    return ["bash", "-c", f'. "{idf}/export.sh" >/dev/null 2>&1 && export PATH="$PATH:{extra}" && {cmd}']


def build(c, args):
    first = not os.path.exists(os.path.join(PROJECT, "sdkconfig"))
    cmd = ("idf.py set-target esp32 && " if first else "") + "idf.py build"
    print(f"building {PROJECT} (ESP-IDF at {c['firmware']['idf_path']})", flush=True)
    r = subprocess.run(idf_env_cmd(c, cmd), cwd=PROJECT)
    if r.returncode:
        sys.exit("build failed (see output above)")
    print(f"\nbuilt {os.path.join(BUILD, 'haven-csi-node.bin')}\nnext: python tools/haven_fw.py flash")


# ---------------------------------------------------------------------------------------- flashing

def flash_image(port, app_only):
    meta_path = os.path.join(BUILD, "flasher_args.json")
    if not os.path.exists(meta_path):
        sys.exit("no firmware built yet: python tools/haven_fw.py build")
    with open(meta_path) as f:
        meta = json.load(f)
    files = {"0x10000": meta["app"]["file"]} if app_only else meta["flash_files"]
    fs = meta["flash_settings"]
    args = ["--baud", "460800", "--before", "default-reset", "--after", "hard-reset", "write-flash",
            "--flash-mode", fs["flash_mode"], "--flash-size", "detect", "--flash-freq", fs["flash_freq"]]
    for off, rel in sorted(files.items(), key=lambda kv: int(kv[0], 16)):
        args += [off, os.path.join(BUILD, rel)]
    return esptool(*args, port=port)


def nvs_python():
    """A Python that can run Espressif's NVS partition generator."""
    cands = [sys.executable] + sorted(glob.glob(os.path.expanduser("~/.espressif/python_env/idf*/bin/python")), reverse=True)
    for py in cands:
        if subprocess.run([py, "-c", "import esp_idf_nvs_partition_gen"], capture_output=True).returncode == 0:
            return py
    sys.exit("NVS generator missing: pip install esp-idf-nvs-partition-gen  (or install ESP-IDF's Python env)")


def nvs_rows(c, board):
    fw = c["firmware"]
    peers = [b["mac"] for b in c["boards"] if b["mac"] != board["mac"]]
    rows = [("ssid", "data", "string", c["wifi"]["ssid"]),
            ("target_ip", "data", "string", c["host"]["ip"] if fw["stream"] != "serial" else ""),
            ("target_port", "data", "u16", c["host"]["udp_port"]),
            ("node_id", "data", "u8", board["id"]),
            ("ping_hz", "data", "u8", int(fw.get("ping_hz", 50))),
            ("link_hz", "data", "u8", int(fw.get("link_hz", 50))),
            ("stream", "data", "u8", havenconfig.STREAMS[fw["stream"]])]
    if fw.get("tx_power_dbm"):
        rows.append(("tx_qdbm", "data", "u8", max(8, min(84, round(float(fw["tx_power_dbm"]) * 4)))))
    if fw.get("accept_all"):
        rows.append(("accept_all", "data", "u8", 1))
    if peers:
        rows.append(("link_macs", "data", "hex2bin", "".join(m.replace(":", "") for m in peers)))
    return rows


def provision(c, port, board):
    pw_file = c["wifi"]["password_file"]
    if not os.path.exists(pw_file):
        sys.exit(f"Wi-Fi password file {pw_file} not found (plain text, only the password; chmod 600). "
                 "For an open network create it empty.")
    with open(pw_file) as f:
        password = f.read().strip("\r\n")
    tmp = tempfile.mkdtemp(prefix="haven-nvs-")
    try:
        os.chmod(tmp, 0o700)
        csv_path, bin_path = os.path.join(tmp, "nvs.csv"), os.path.join(tmp, "nvs.bin")
        with open(csv_path, "w") as f:
            f.write("key,type,encoding,value\ncsi_cfg,namespace,,\n")
            for key, typ, enc, val in nvs_rows(c, board) + [("password", "data", "string", password)]:
                if enc == "string" and ("," in str(val) or '"' in str(val)):
                    val = '"' + str(val).replace('"', '""') + '"'
                f.write(f"{key},{typ},{enc},{val}\n")
        r = subprocess.run([nvs_python(), "-m", "esp_idf_nvs_partition_gen", "generate", csv_path, bin_path,
                            hex(NVS_SIZE)], capture_output=True, text=True)
        if r.returncode:
            err = (r.stderr or r.stdout)[-400:]
            return False, "NVS generation failed: " + (err.replace(password, "***") if password else err)
        return esptool("--baud", "460800", "--after", "hard-reset", "write-flash", hex(NVS_OFFSET), bin_path, port=port)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def configured_ports(c, only_port=None):
    by_mac = {b["mac"]: b for b in c["boards"]}
    found = []
    for p in ports(only_port):
        mac = mac_of(p)
        b = by_mac.get(mac)
        if not b:
            print(f"{p}: {mac or 'no ESP32 answered'} is not in config.yaml, skipped")
            continue
        found.append((p, b))
    if not found:
        sys.exit("no configured boards on USB: run python tools/haven_fw.py discover, update config.yaml")
    return found


def summarize_boot(text):
    j = re.search(r'HAVEN_JOINED ssid="(.*?)" channel=(\d+) rssi=(-?\d+) router_bssid=([0-9a-f:]{17}) ip=([\d.]+)', text)
    y = re.findall(r"yield=([\d.]+)/s \(router ([\d.]+), peers ([\d.]+)\)", text)
    node = re.search(r"\| node (\d+) \| mac ([0-9a-f:]{17})", text)
    if "not provisioned" in text:
        return "running but NOT provisioned (run provision)"
    if not j:
        reason = re.findall(r"Wi-Fi disconnected \(reason (\d+)\)", text)
        return ("NOT connected to Wi-Fi" + (f" (reason {reason[-1]})" if reason else "") +
                ": check ssid/password, and that it is a 2.4 GHz network")
    s = f"node {node.group(1) if node else '?'} joined \"{j.group(1)}\" ch {j.group(2)} RSSI {j.group(3)} dBm, ip {j.group(5)}, router {j.group(4)}"
    if y:
        s += f", CSI yield {y[-1][0]}/s (router {y[-1][1]}, peers {y[-1][2]})"
    else:
        s += ", no CSI status line yet"
    return s


def flash(c, args):
    for port, b in configured_ports(c, args.port):
        name = f"node {b['id']} ({b['name']})"
        ok, log = flash_image(port, args.app_only)
        if not ok:
            print(f"{port}: {name} FLASH FAILED\n{log[-800:]}")
            continue
        if not args.app_only:
            ok, log = provision(c, port, b)
            if not ok:
                print(f"{port}: {name} flashed, but writing settings failed\n{log[-400:]}")
                continue
        print(f"{port}: {name} flashed; {summarize_boot(read_boot(port))}", flush=True)
    print(f"\nboards stream to {c['host']['ip']}:{c['host']['udp_port']}. Start the host: python host/server.py")


def do_provision(c, args):
    for port, b in configured_ports(c, args.port):
        ok, log = provision(c, port, b)
        print(f"{port}: node {b['id']} settings " + ("written; " + summarize_boot(read_boot(port)) if ok else "FAILED\n" + log[-400:]))


def check(c, args):
    for p in ports(args.port):
        print(f"{p}: {summarize_boot(read_boot(p, seconds=args.seconds))}", flush=True)


def discover(c, args):
    ps = ports(args.port)
    if not ps:
        sys.exit("no USB-serial ESP32 boards found: use a data cable (charge-only cables don't show up)")
    print("boards:  # paste into config.yaml\n")
    for i, p in enumerate(ps, 1):
        mac = mac_of(p)
        print(f'  - {{ id: {i}, mac: "{mac}", name: "node {i}" }}   # {p}' if mac else f"  # {p}: no ESP32 answered")


def monitor(c, args):
    p = (ports(args.port) or [None])[0]
    if not p:
        sys.exit("no board found")
    s = open_port(p)
    if args.reset:
        reset(s)
    n_csi, t_last = 0, time.time()
    print(f"{p} @ {BAUD_LOG} baud, Ctrl-C to quit")
    try:
        while True:
            line = s.readline().decode(errors="replace").rstrip()
            if line.startswith("CSIB:"):
                n_csi += 1
            elif line:
                print(line, flush=True)
            if time.time() - t_last > 5 and n_csi:
                print(f"  [serial CSI lines: {n_csi / (time.time() - t_last):.1f}/s]", flush=True)
                n_csi, t_last = 0, time.time()
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["discover", "build", "flash", "provision", "check", "monitor"])
    ap.add_argument("--port", help="only this serial port")
    ap.add_argument("--app-only", action="store_true", help="flash: program only, keep settings")
    ap.add_argument("--reset", action="store_true", help="monitor: reset the board first")
    ap.add_argument("--seconds", type=float, default=20, help="check: how long to read the boot log")
    ap.add_argument("--config", help="path to config.yaml")
    a = ap.parse_args()
    if a.command in ("discover", "monitor", "check"):
        cfg = havenconfig.load(a.config) if os.path.exists(a.config or os.path.join(ESP32_DIR, "config.yaml")) else {}
    else:
        cfg = havenconfig.load(a.config, need_wifi=a.command in ("flash", "provision") and not a.app_only)
    {"discover": discover, "build": build, "flash": flash, "provision": do_provision, "check": check,
     "monitor": monitor}[a.command](cfg, a)
