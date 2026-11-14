# NOTES

## Goal
Hackathon project: 3x ESP32 Wi-Fi CSI sensing to detect falls of elderly residents and report when and in which room zone they happened. No cameras, no wearables.

## Team / repo
- Repo: https://github.com/luisscheibe9-git/Hackathon (private). Collaborators with write access: Aouzzo, jbj4poly-dotcom.
- Default branch `main`. Research added on branch `research`.

## Current state (2026-11-13)
- Research done: see `research/` (viability verdict, approach, sources, open questions).
- [Wi-Fi sensing demo](research/wifi-sensing.md) records reported ESP32-S3 results and reproduction steps.
- No code yet. `test.txt` and `jack.test` are leftover push-access tests and can be deleted.

- Team to-do list with owners and deadlines (presentation, hardware, software/AI, dashboard, website, submission): Google Doc "Hackathon ideas", https://docs.google.com/document/d/1upIEmQUVUbZdIuxvN-gHEJgOShMZMWAb9dQ6_YxRwJs/edit (To DO LIST section). Keep tasks there, not in the repo.
- Shared Google Drive folder "Hackathon" (editors: Anthony, Jack): https://drive.google.com/drive/folders/1IWIpqnB7UojHoDrU4_enAqYaaRD2JUB3

## Decisions
- Goal is a product to sell to nursing homes; the hackathon is the first demo. See `research/product.md` (market, competitors, product requirements).
- Event rules, deadlines and judging rubric summarized in `research/hackathon-rules.md`. Key dates: project link Sat 2 PM, Sunday commit + live link Sat 8 PM, submissions close Sun 12 PM, demo is 4 min live + 3 min Q&A. 45/100 points are problem + path to customers, so talk to real caregivers this weekend.
- Scope: fall detection + zone-level location. Not precise tracking or room mapping.
- Use CSI, not RSSI.
- Hardware: 3x ESP32-U (original ESP32, external antenna). RuView doesn't support it → base is espressif/esp-csi + own Python pipeline.
- Presence state machine to stop "person lying still" from reading as "empty room".

## Next steps
1. Answer `research/open-questions.md` (board model first).
2. Create `firmware/`, `detection/`, `dashboard/` skeletons.
3. Get CSI streaming from one board to a laptop.
4. Record training data; build threshold fall detector; dashboard.

## Gotchas
- CSI models don't transfer between rooms: retrain at the venue.
- RuView does not support original ESP32 or ESP32-C3.
