# Research

Background research for the project: **camera-free fall detection for elder care using Wi-Fi sensing on three ESP32 boards.**

| File | What's in it |
|---|---|
| [viability.md](viability.md) | Can we actually build this? Verdict, what works, what doesn't, risks |
| [approach.md](approach.md) | How Wi-Fi CSI sensing works and our proposed technical design |
| [sources.md](sources.md) | Annotated list of videos, repos and papers |
| [open-questions.md](open-questions.md) | Things we still need to decide or test |

## TL;DR

- **Viable for a hackathon** if we scope it as *fall detection + which zone of the room*, not precise tracking or room mapping.
- Use **Wi-Fi CSI** (Channel State Information), not RSSI. RSSI is too noisy.
- Best starting points: [RuView](https://github.com/ruvnet/RuView) (needs ESP32-S3 or C6) or Espressif's [esp-csi](https://github.com/espressif/esp-csi) (more boards supported).
- Biggest risk: models trained in one room fail in another. **Record training data at the venue.**
- Known failure mode: a person lying still after a fall looks like an empty room. Fix with a presence state machine (see [approach.md](approach.md)).

## Adding research

Add a new `.md` file here or append to `sources.md` with: link, one-line summary, and what it means for us. Keep big PDFs out of the repo; link them instead.
