# Haven live demo (simple, two-path mode)

**What we show (~30 s):** the boards talk to each other over Wi-Fi, Haven sees a person standing, and when they lie on the floor it raises **FALL DETECTED** and buzzes a phone.

**How it works:** one fixed rule, no machine learning, so there's nothing to retrain:

| Top path (#1 → #2, high) | Bottom path (#1 → #3, floor) | Haven shows |
|---|---|---|
| quiet | quiet | Room empty |
| disturbed | either | Person standing |
| quiet | disturbed | Person on the floor → **FALL DETECTED** after 3 s |

"Disturbed" means the path's CSI differs from the empty room by more than 1.5× the empty room's own noise. That's measured in a 10 s calibration.

## 1. Flash (once; skip if the boards already run the latest `firmware/`)
Board **#1** gets the gateway sketch, **#2 and #3** get the receiver sketch. Each board picks its role from its MAC. The receivers reboot and rejoin on their own if the gateway resets, so you don't need to press EN.
```bash
arduino-cli upload --fqbn esp32:esp32:esp32 --board-options UploadSpeed=230400 -p COM4 firmware/csi_transmitter
```
```bash
arduino-cli upload --fqbn esp32:esp32:esp32 --board-options UploadSpeed=230400 -p COM5 firmware/csi_link_check
```
Run `arduino-cli compile --fqbn esp32:esp32:esp32 <sketch folder>` first if it says the sketch isn't built. Use one COM port per board, as shown in Device Manager.

## 2. Place the boards (side view, ~2 m wide)
```
   #1 (gateway, ~0.7 m,          #2 (top, ~1.3-1.5 m on a stand)
   table, USB to laptop)  ........................ o
          o  .................                     |
          |           MAT (on floor, under the     |
          |           bottom path, near #3)  ..... o #3 (bottom, on the floor)
   ===================================================== floor
   JUDGES stand behind #1 / behind a tape line
```
- **#2 and #3 together:** put them at the same far end, one above the other. The two paths then run in one vertical plane, one high and one low.
- **The mat:** lay it along the bottom path, closer to #3. A person lying there blocks the low path but stays under the high one.
- **Fixed positions:** tape the boards down. If anything moves, recalibrate (30 s).
- **Power:** #2 and #3 on wall chargers. Weak power banks dropped out before.

## 3. Start
From `esp32/`, with the Observatory and any serial monitor closed (only one program can use COM4):
```bash
.venv\Scripts\python.exe -u host\simple_demo.py --gateway COM4
```
On a Mac: `.venv/bin/python -u host/simple_demo.py --gateway /dev/cu.usbserial-XXXX`.

Open **http://127.0.0.1:8950**. Both path bars should show about 20+ packets/s within ~20 s.
- **Phone alerts** use the ntfy topic in `esp32/config.yaml`. Press **T** to test.
- **If the boards are swapped** (#3 is the high one): add `--top 3 --bottom 2`.

## 4. Calibrate (under 30 s, right before the demo)
1. Everyone behind the line, then press **C**. That records 10 s of empty room.
2. The actor lies on the mat, then press **L**. That records 8 s of lying and sets both thresholds. If the page shows **WARNING**, move the mat closer to #3, away from the top path, and redo C and L.
3. The actor stands up and steps in. The page should say **Person standing**.

## 5. Demo script
1. "These three boards talk to each other over Wi-Fi. The top and bottom bars are two of those links." The room shows **empty**.
2. The actor steps in and stands: **Person standing**, with the top bar green.
3. The actor lies down on the mat: **Person on the floor** with a 3 s countdown, then **FALL DETECTED**, and the phone buzzes. Hold the phone up.
4. Press **R** to reset. The actor gets up.

## 6. Trial test (do it 3 times in the demo room before judging)
Run steps 1–4 of the script, plus 30 s of empty room, plus 15 s of the actor just standing. Pass = the fall alerts every time, and empty or standing never alerts. Every tick is logged to `esp32/data/simple-demo-log-<date>.csv` if you need to check what happened.

**If it misbehaves:**
- **"Sensor offline":** a board lost power or reset. It reboots itself within about 15 s; check its charger.
- **Standing reads as "on the floor":** #2 isn't high enough, or the actor stands too far from the paths. Raise #2 or move the actor closer to the boards, then press C and L again.
- **Lying reads as standing:** the mat is under the top path. Move the mat toward #3, then press C and L again.
- **Empty reads as standing:** someone was moving during calibration. Press C again with everyone behind the line.

## 7. At judging
- **Setup:** about 3 minutes. Boards on the tape marks, start the server, C, L, then one quiet run.
- **Fallback:** if a board fails, say so and play the demo video. Never fake the alert.
- **Bring:** a spare flashed board, a spare USB data cable, wall chargers plus a power strip, tape, the mat, a phone with ntfy, and the laptop charger.
- **Rehearsing without boards:** `python host/simple_demo.py --sim` runs the same page with simulated paths.

The full machine-learning version (4-state calibration, `server.py` + `demo.html`) still works and is described in `NOTES.md`. Use it only if there's time to rehearse it.
