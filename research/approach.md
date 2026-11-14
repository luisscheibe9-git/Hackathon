# Technical approach

## How Wi-Fi sensing works

Every Wi-Fi packet is spread across many subcarriers (frequencies). **CSI** reports the amplitude and phase of each subcarrier as received. A human body absorbs and reflects the signal, so movement between two radios changes the CSI pattern. ESP32 chips can expose CSI for each received packet.

- **RSSI** = one number per packet (overall strength). Cheap but noisy; fine for "something moved", not for falls.
- **CSI** = dozens of numbers per packet. Enough detail to distinguish walking, sitting and falling.

## Proposed setup

```
        A ─────────── B        3 ESP32 boards in room corners, ~1 m high
         \           /         Each pair forms a sensing link (A-B, B-C, A-C)
          \  person /          The link most disturbed ≈ the person's zone
           \       /
              C
              │  CSI over UDP or USB serial (~100 packets/s)
              ▼
     Laptop (Python): filter → features → classify
              ▼
     Dashboard: room map with active zone, FALL alert + timestamp, event log
```

- Nodes take turns transmitting short pings while the others record CSI (or all ping a router).
- ~100 packets/s is enough for fall dynamics.

## Detection pipeline

1. **Clean:** drop bad packets, Hampel filter for outliers, low-pass filter.
2. **Features per link, per ~1 s rolling window:** amplitude variance, max change rate, energy in motion frequency bands.
3. **Presence/zone:** threshold on variance; zone = most disturbed link.
4. **Fall:** large sudden spike (< 1 s) followed by several seconds of low variance.
5. **Classifier (if time):** scikit-learn random forest on windows labeled empty / walk / sit / lie down / fall.

## Presence state machine (fixes "fall looks empty")

```
EMPTY ──motion──▶ PRESENT ──spike then still──▶ FALL_SUSPECTED ──still > N s──▶ FALL_ALERT
  ▲                  │
  └─exit via door────┘   (only the doorway-zone link can move us back to EMPTY)
```

Because someone lying still can't "leave", stillness after a spike stays a fall instead of reading as an empty room.

## Training data plan

Record at the venue, ~10 min each: empty room, walking, sitting down, lying down slowly, falls onto a mattress (several people, several spots). Keep a held-out recording to report honest accuracy.

## Our hardware: 3x ESP32-U

The "U" boards have the **original ESP32 chip** with a **U.FL connector for an external antenna** (no PCB antenna).

- **RuView does not support the original ESP32** → we use **esp-csi** plus our own Python pipeline.
- Espressif ranks CSI quality C5 > C6 > C3 ≈ S3 > original ESP32. Ours is lowest but still works; fine for motion/fall signals.
- **Each board needs an antenna attached** or Wi-Fi will be very weak.
- External antennas are a plus: we can position and aim them independently of the board, and the board can sit in an enclosure (good for a product).
- Upgrade path for a product: ESP32-C5/C6 (better CSI, cheap).

## Candidate bases

| Option | Pros | Cons |
|---|---|---|
| [RuView](https://github.com/ruvnet/RuView) | Flashing + provisioning scripts, streaming, threshold fall module, web UI | ESP32-S3/C6 only; beta; large codebase |
| [esp-csi](https://github.com/espressif/esp-csi) + own Python | Official, supports many ESP32s, small and understandable | We write the pipeline and dashboard ourselves |
