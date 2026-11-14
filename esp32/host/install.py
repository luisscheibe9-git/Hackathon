#!/usr/bin/env python3
"""One-time host setup: Python packages + the in-browser pose model for the webcam teacher.

  python host/install.py

Downloads Google MediaPipe Tasks Vision 0.10.14 (Apache-2.0) and pose_landmarker_full into
host/web/vendor/mediapipe/ (~30 MB, git-ignored) so the training page works offline. Without it the page
falls back to loading the same files from the jsDelivr / Google CDNs.
"""
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "web", "vendor", "mediapipe")
CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14"
FILES = {
    "vision_bundle.mjs": f"{CDN}/vision_bundle.mjs",
    "wasm/vision_wasm_internal.js": f"{CDN}/wasm/vision_wasm_internal.js",
    "wasm/vision_wasm_internal.wasm": f"{CDN}/wasm/vision_wasm_internal.wasm",
    "wasm/vision_wasm_nosimd_internal.js": f"{CDN}/wasm/vision_wasm_nosimd_internal.js",
    "wasm/vision_wasm_nosimd_internal.wasm": f"{CDN}/wasm/vision_wasm_nosimd_internal.wasm",
    "pose_landmarker_full.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
}

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join(HERE, "..", "requirements.txt")], check=True)
    for rel, url in FILES.items():
        dst = os.path.join(VENDOR, rel)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        print("downloading", rel, flush=True)
        urllib.request.urlretrieve(url, dst + ".part")
        os.replace(dst + ".part", dst)
    print("host setup done")
