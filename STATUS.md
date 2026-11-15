# Repository handoff — November 15, 2026

Read NOTES.md for hardware, training history, and calibration limitations.

## Goal and current state
Haven uses three ESP32-WROOM-32U boards for router-free Wi-Fi CSI sensing. The goal is accurate tracking and fall detection within their triangle. Current software classifies activity/posture and alerts on sustained lying; exact position and general fall-detection accuracy are not established.

## Latest download
- Hackathon main downloaded at `f18ee5858b0c9d7997caab17ee71caab9c90092f` into `C:/Users/lscheibe/OneDrive - Cal Poly/Desktop/Hackathon-latest`.
- Original `Desktop/hackathon` has extensive uncommitted training work, local configuration, environments and recordings. Preserved unchanged; this new checkout does not replace that live environment. Do not overwrite its dataset or run retrain_from_raw --save without reviewing NOTES.md.
- Git fetch in the original folder reported permission errors deleting old worktree metadata. The new independent clone succeeded and matched remote main.
- This handoff branch is `codex/repo-sync-handoff`; only STATUS.md is committed here.

## Presentation website
- Repository: https://github.com/Aouzzo/Haven
- Downloaded main `b84498729c2e9d7589e2e073f298c28e49a562f4` into `C:/Users/lscheibe/OneDrive - Cal Poly/Desktop/Haven`.
- Presentation: https://haven-public-ten.vercel.app
- Active site is `safer/public/`, static HTML/CSS/JavaScript with local Three.js. `web/` is a separate Next.js implementation, not the active pitch site according to its NOTES.md.
- Read Haven's NOTES.md, ReadME.md and safer/README.md before editing. Main pushes redeploy; use feature branches for proposed changes.
- Key files: `safer/public/cinematic/story.js` (chapters and DEMO_VIDEO), `scene3d.js` (3D scene), `timeline.js` (scroll story and simulated dashboard), `pages/sections.js` (pitch sections).
- Run website from the Haven root with `python safer/serve.py`, then http://127.0.0.1:4173. No build/dependency installation required for this static site.
- The presentation fall animation, CSI trace and dashboard are simulated. No sensor bridge is implemented. Demo video is unset; customer evidence, final pricing and measured results still need review.

## Next work / gotchas
1. Keep the hardware demo and pitch simulation clearly distinguished; integrate a labeled real recording or live bridge if requested.
2. Align pitch wording with actual sustained-lying detection and three dedicated boards; exact tracking is a goal, not a verified capability.
3. Review the latest local calibration before reporting any accuracy. Moving boards invalidates earlier room training.
4. Live host entry point is `esp32/host/server.py --gateway COM4`; configuration and Python environment must be supplied locally. Only one process can own the gateway serial port. This download did not launch hardware or change firmware.

## Verification
Both independent clones completed; their main revisions matched GitHub and working trees were clean before this handoff. Website source and repo notes reviewed. No application code was changed and no new hardware/model validation was performed.
