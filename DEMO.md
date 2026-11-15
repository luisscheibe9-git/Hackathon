# Haven live demo: setup, run, trial test

One use case only: **a person walks in, falls, stays down, and Haven raises FALL DETECTED and buzzes a phone.** Everything below is about making that one moment work every time. It builds on the setup on `main` (3 boards without a router, `esp32/host/server.py`, `demo.html`). The history is in `NOTES.md`.

## 0. What you need
- Boards **#1** (gateway, MAC ...9f:1d:98), **#2** (...9f:27:f4) and **#3** (...1a:80:ac), with antennas attached.
- #1: a known-good USB **data** cable to the laptop. #2 and #3: **wall chargers**. Weak power banks caused dropouts before.
- A mat, tape, the laptop with `esp32/.venv` and `esp32/config.yaml` (git-ignored), and a phone with the ntfy app subscribed to the topic in `config.yaml`.

## 1. Flash the firmware (once, ~5 min)
The firmware now **recovers on its own**. If the gateway resets (for example when the laptop opens its port), #2 and #3 reboot after 10 s of silence and rejoin. Nobody needs to press EN.

Plug in one board at a time. Check its COM port in Device Manager (Mac: `ls /dev/cu.usbserial-*`).

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/csi_transmitter
```
```bash
arduino-cli upload --fqbn esp32:esp32:esp32 --board-options UploadSpeed=230400 -p COM4 firmware/csi_transmitter
```
That's the gateway, **#1 only**. Then flash **both #2 and #3** with the same receiver sketch (each board picks its role from its MAC):
```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/csi_link_check
```
```bash
arduino-cli upload --fqbn esp32:esp32:esp32 --board-options UploadSpeed=230400 -p COM5 firmware/csi_link_check
```
Use 230400 baud. Faster uploads failed on these boards.

## 2. Set up a small "demo box" (the key to reliability)
Make the sensing area small and fixed, so the person dominates the signal and the room doesn't matter.

```
            #2  (high, ~1.3 m, on a stand)
           /  \
          /    \        sides ~2-2.5 m
         / MAT  \       mat inside the triangle, closer to #3
        /        \
      #1 -------- #3  (low, ~0.2-0.3 m, on the floor)
  (table, next to laptop)

   AUDIENCE / JUDGES: behind #1, behind the tape line
```
- **Fixed positions:** tape every board down and mark its spot on the floor. Take a photo, and rebuild exactly like it.
- **Why high and low:** a person standing crosses the high paths, a person lying on the mat crosses the low ones. That difference is what tells standing from lying.
- **Tape line:** nobody but the actor inside the triangle or walking near it during calibration and the demo. Moving people nearby are the #1 cause of wrong readings.
- **Moving boards = recalibrate.** Any board move invalidates the calibration.

## 3. Start Haven
1. Power #2 and #3, then plug #1 into the laptop.
2. Close the Observatory or any serial monitor, since only one program can hold the port. Then run, from `esp32/`:
   ```bash
   .venv\Scripts\python.exe -u host\server.py --gateway COM4
   ```
   (Mac: `.venv/bin/python -u host/server.py --gateway /dev/cu.usbserial-XXXX`)
3. Open http://127.0.0.1:8940/demo.html. Wait about 20 s. The live page (http://127.0.0.1:8940) should show **3 paths, each above ~20 packets/s**. If a path is missing after 30 s, check that board's power. It reboots itself, so give it 15 s.

## 4. Calibrate on site (~2 min, do it right before the demo)
On `demo.html`, open the small **▾** menu at the top and record each state, 20 s each:
1. **Empty room:** everyone behind the tape line.
2. **Standing:** the actor stands at the edge of the mat, swaying a little.
3. **Walking:** the actor walks the exact demo path in and out of the triangle.
4. **Lying down:** the actor lies on the mat in the fall position. Small movements are fine.

Each calibration replaces that state's old data. Redo just one state if it reads wrong.

## 5. The demo script (~45 s)
1. Press **Start** (Enter). Room shows **empty**.
2. The actor walks in along the calibrated path: **Person walking**.
3. Falls onto the mat and **stays down**: **Possible fall**, then **FALL DETECTED** about 3 s later, and the phone buzzes. Hold the phone up for the judges.
4. Press **R** (Reset) to clear the fall. The actor gets up. **Esc** goes back to the start screen.

Press **T** before judging to check that the phone buzzes (it uses the "Test phone" button).

Do **not** stand still for long in the demo. Standing still is the weakest state and can read as lying. Keep moving until the fall.

## 6. Trial test (do this in the demo room and score it)
Write down the start time (HH:MM), then run:

| # | Run | Expected | Times |
|---|---|---|---|
| A | Full demo script (section 5) | FALL DETECTED within 10 s of hitting the mat | 10 |
| B | Walk in, walk around, walk out (no fall) | No alert | 3 |
| C | Stand at the mat edge 15 s, then walk out | No alert | 3 |
| D | Empty room, 60 s | No alert | 1 |

Press **R** between runs. Then score it from `esp32/`:
```bash
.venv\Scripts\python.exe host\trial_report.py --since 10:05
```
It lists every state change with its time, counts the fall alerts, and warns if any path dropped below 10 packets/s.

**Pass = 10/10 alerts in A, and 0 alerts in B, C and D.**
- Missed a fall: recalibrate **Lying down**.
- False alert in C: recalibrate **Standing** (sway a little), or keep the actor moving in the demo.
- False alert in B or D: recalibrate **Empty room**, then **Walking**, with the audience behind the line.
- Path warning: fix power and cables first, then recalibrate everything.

## 7. At judging
- **Setup (~3 min):** place the boards on the tape marks, start the server, check the 3 paths, then calibrate all 4 states (section 4). Run the script once quietly if time allows.
- **If a board fails live:** say so, then play the recorded demo video. It's honest and fast. Never fake the alert.
- **Bring:** a spare flashed board, spare USB data cable, wall chargers plus a power strip, tape, the mat, a phone with ntfy, and the laptop charger.
