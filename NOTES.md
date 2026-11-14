# NOTES

## Goal
Hackathon project: 3x ESP32 Wi-Fi CSI sensing to detect falls of elderly residents and report when and in which room zone they happened. No cameras, no wearables.

## Team / repo
- Repo: https://github.com/luisscheibe9-git/Hackathon (private). Collaborators with write access: Aouzzo, jbj4poly-dotcom.
- Default branch `main`. Research added on branch `research`.

## Current state (2026-11-13)
- Research done: see `research/` (viability verdict, approach, sources, open questions).
- No code yet. `test.txt` and `jack.test` are leftover push-access tests and can be deleted.

## Decisions
- Scope: fall detection + zone-level location. Not precise tracking or room mapping.
- Use CSI, not RSSI.
- Base: RuView if boards are ESP32-S3/C6, otherwise espressif/esp-csi + own Python pipeline.
- Presence state machine to stop "person lying still" from reading as "empty room".

## Next steps
1. Answer `research/open-questions.md` (board model first).
2. Create `firmware/`, `detection/`, `dashboard/` skeletons.
3. Get CSI streaming from one board to a laptop.
4. Record training data; build threshold fall detector; dashboard.

## Gotchas
- CSI models don't transfer between rooms: retrain at the venue.
- RuView does not support original ESP32 or ESP32-C3.
