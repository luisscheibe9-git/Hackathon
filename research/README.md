# Research

Background research for the project: **camera-free fall detection for elder care using Wi-Fi sensing on three ESP32 boards.**

| File | What's in it |
|---|---|
| [viability.md](viability.md) | Can we actually build this? Verdict, what works, what doesn't, risks |
| [approach.md](approach.md) | How Wi-Fi CSI sensing works and our proposed technical design |
| [sources.md](sources.md) | Annotated list of videos, repos and papers |
| [product.md](product.md) | Selling to nursing homes: buyers, competitors, what a real product needs |
| [open-questions.md](open-questions.md) | Things we still need to decide or test |
| [hackathon-rules.md](hackathon-rules.md) | Event deadlines, required workshops, judging rubric, submission rules, and what they mean for us |
| [wifi-sensing.md](wifi-sensing.md) | ESP32-S3 demo results, setup, and reproduction steps |

## TL;DR

- **Viable for a hackathon** if we scope it as *fall detection + which zone of the room*, not precise tracking or room mapping.
- Use **Wi-Fi CSI** (Channel State Information), not RSSI. RSSI is too noisy.
- We have 3x ESP32-U (original ESP32 chip, external antenna), so the base is Espressif's [esp-csi](https://github.com/espressif/esp-csi). [RuView](https://github.com/ruvnet/RuView) doesn't support our chip.
- Product target: nursing homes. Main competitor is camera-free radar; our edge is cost. See [product.md](product.md).
- Biggest risk: models trained in one room fail in another. **Record training data at the venue.**
- Known failure mode: a person lying still after a fall looks like an empty room. Fix with a presence state machine (see [approach.md](approach.md)).

## Adding research

Add a new `.md` file here or append to `sources.md` with: link, one-line summary, and what it means for us. Keep big PDFs out of the repo; link them instead.
- [bom-cost.md](bom-cost.md): bulk hardware cost per Haven node and kit, power options.
