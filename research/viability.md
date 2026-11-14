# Viability assessment

_Last updated: 2026-11-13_

## Verdict

**Viable as a hackathon demo** when pitched as *privacy-preserving fall alerts with time and room zone*. Not viable (in a weekend) as precise person tracking or automatic room mapping.

## Goal-by-goal

| Goal | Viability | Evidence |
|---|---|---|
| Presence / motion in room | High | ~96% empty-vs-occupied in the RuView demo (3x ESP32-S3) |
| Which zone a person is in | Medium | RuView is mostly zone-level; a 3-node ESP32 study used grid fingerprinting in a 6x4 m lab |
| Fall detection (controlled demo) | Medium-high | 3x ESP32-S3 student project: 91.5% on empty/walk/fall; IEEE Access 2023: >96% in controlled rooms |
| Fall detection (real elder home) | Low without much more work | One report: accuracy fell to 11% in an untrained room |
| Precise tracking / room mapping | Low | Viral Wi-Fi "skeleton" pose demo was partly simulated; RuView's live pose model scores 3% PCK@20 |

## Risks and mitigations

1. **Each room needs its own training.** Models don't generalize across rooms; furniture changes and extra people break them.
   *Mitigation:* record ~10 min per activity at the venue on demo day; rope off the demo area.
2. **Fall looks like an empty room.** A person lying still after falling produces a near-empty-room signal. This was the most common error in the 3-board study.
   *Mitigation:* state machine — if a person was present and didn't leave via the doorway zone, a spike followed by stillness = fall.
3. **Board compatibility.** RuView requires ESP32-S3 or C6 (not original ESP32 or C3). esp-csi supports more boards.
   *Mitigation:* confirm our boards first (see [open-questions.md](open-questions.md)).
4. **Firmware bring-up is the riskiest step.** Flashing and getting CSI streaming can eat hours.
   *Mitigation:* one person owns firmware from hour 0; RuView ships flashing/provisioning scripts.
5. **Over-claiming.** RuView is beta and has retracted some accuracy claims.
   *Mitigation:* report only accuracy we measure ourselves.

## Pitch angle

No cameras, no wearables, nothing for residents to remember to charge. Alerts give *when* and *where* a fall happened. Stretch: breathing detection while the person is still (RuView labels this unvalidated).
