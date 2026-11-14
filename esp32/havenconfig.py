"""Loads and checks esp32/config.yaml. Shared by tools/haven_fw.py and host/server.py."""
import os
import re
import socket
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
STREAMS = {"udp": 1, "serial": 2, "both": 3}


def load(path=None, need_wifi=False):
    path = path or os.path.join(ROOT, "config.yaml")
    if not os.path.exists(path):
        sys.exit(f"{path} not found: copy config.example.yaml to config.yaml and fill it in")
    with open(path) as f:
        c = yaml.safe_load(f) or {}
    c.setdefault("wifi", {})
    c.setdefault("host", {})
    c.setdefault("firmware", {})
    c.setdefault("detection", {})
    c.setdefault("room", {})
    c["boards"] = c.get("boards") or []
    for b in c["boards"]:
        b["mac"] = str(b.get("mac", "")).lower()
        b.setdefault("name", f"node {b.get('id')}")
        if not MAC_RE.match(b["mac"]):
            sys.exit(f"board {b.get('id')}: '{b['mac']}' is not a MAC address (aa:bb:cc:dd:ee:ff). "
                     "Run: python tools/haven_fw.py discover")
    ids = [b.get("id") for b in c["boards"]]
    if len(set(ids)) != len(ids) or not all(isinstance(i, int) and 1 <= i <= 255 for i in ids):
        sys.exit("board ids must be unique integers 1-255")
    w = c["wifi"]
    w["password_file"] = os.path.expanduser(str(w.get("password_file", "~/.haven-wifi-pass")))
    if need_wifi and not w.get("ssid"):
        sys.exit("wifi.ssid is empty in config.yaml")
    h = c["host"]
    h["udp_port"] = int(h.get("udp_port", 5005))
    h["http_port"] = int(h.get("http_port", 8940))
    if str(h.get("ip", "auto")) == "auto":
        h["ip"] = local_ip()
    fw = c["firmware"]
    fw["idf_path"] = os.path.expanduser(str(fw.get("idf_path", "~/esp/esp-idf")))
    fw["stream"] = str(fw.get("stream", "udp")).lower()
    if fw["stream"] not in STREAMS:
        sys.exit(f"firmware.stream must be one of {', '.join(STREAMS)}")
    return c


def local_ip():
    """This computer's address on the LAN (no packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def board_names(c):
    """MAC -> board id (as text), used to name links like '2>1'."""
    return {b["mac"]: str(b["id"]) for b in c["boards"]}
