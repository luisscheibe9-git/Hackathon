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

## Overnight video task — Nov 15, 02:32 Pacific
- User requests a finished, polished, editable OpenAI challenge video for review before 9AM, with actual demo footage, two product photos, and Haven presentation styling. Under 120 seconds required. No further user questions; synthetic scratch narration and subtitles approved; team will replace voice later.
- Media downloaded from Drive Recents via signed-in browser, not Hackathon folder: IMG_0512.MOV (35.87s), IMG_0496.HEIC, IMG_0497.HEIC. Originals in video/assets/originals; JPEG conversions in video/assets. Preserve source originals. Caption actual staged test honestly; website animation is simulated.
- Smaller-model subagent /root/video_editor (gpt-6.1-sol, low) owns assembly/render/source files. Main agent reviews finished result. Do not touch its files concurrently.
- Python tools installed in video/.venv; read video/README.md. Final deliverables copied to Downloads. No video files or code pushed without user approval; only this handoff is authorized for push.
- User superseded initial quota request: next five-hour window can be fully used, but prioritize pacing and finished deliverable. At02:32 current primary75% used, resets04:00:29 Pacific (Unix1794744029). Leave margin now, check usage at milestones; do not redeem resets or purchase credits. Resume quality work after natural reset if needed. Account-wide usage can change due other tasks.
- Latest guide verified in browser: OpenAI challenge 'Build something that helps someone', requires Codex, <2min video and public-viewable link before noon. Preparing local export only; publishing/submitting remains user's action.

## Finished OpenAI challenge film — Nov 15 morning
- Delivered `video/exports/Haven - Challenge Film.mp4`: 117.500 seconds, 1920x1080, 30fps, H.264/AAC, burned subtitles. Same file in Luis's Downloads. Includes real hardware photos and continuous staged prototype trial, phone alert, caregiver benefit, Codex contribution and remaining validation needs. No accuracy claims or simulated website data presented as live.
- Downloads also contains `Haven - Editable Project.zip` (115,980,264 bytes), `Haven - Clean Picture.mp4`, `Haven - Scratch Narration.wav`, `Haven - Captions.srt`.
- Extract ZIP, open Haven.mlt in Shotcut. Nine picture clips and separate Narration track; mute/replace the latter with team's voice. See video/README.md and edits/narration.md for exact steps/timecodes. render.py + edits/timeline.json provide reproducible edits; cached narration supports offline rebuilding.
- Verification: full decode of both MP4s (3,525 frames), audio and picture117.500s, SHA256 matched Downloads copies, all8 cuts and18 subtitle cues checked, extracted relocated Shotcut project rendered through its MLT engine, offline cached-voice rebuild passed. Main inspected contact sheet and playback portions. QA details video/review/QA.md. No publishing/submitting done.
- User manually redeemed a reset at~02:37. Later visible usage panel verified69% remaining; preserve allowance for morning changes rather than using time merely to exhaust quota.
- Haven website fetch exposed overnight/website-polish and theme/clinical, theme/night-shift, theme/signal. Video deliberately stays on established Haven styling and real evidence; no live website files changed.
- Video code/media remain local/uncommitted pending normal approval; only STATUS.md pushed. Project location: C:/Users/lscheibe/OneDrive - Cal Poly/Desktop/Hackathon-latest/video. Original Desktop/hackathon hardware checkout preserved.

## Nov 15 ~10:43 AM — website opener and voice recording ready
- User requested an animated website opening and preparation for their own narration. Delivered Downloads/Haven - Challenge Film v2.mp4 and Haven - Clean Picture v2.mp4, exact117.500s/3525frames at1080p30. V1 Downloads files preserved.
- First11.5s renders actual Haven website Three.js camera movement from pinned main6e1035d5e212dbd6f8c220ddc72b887e49d80e0d; exterior through roof reveal, before new website's one-sensor-per-room concept appears. Small assisted-living concept label. Site source is isolated under video/assets; no live website edits. Regenerate with video/capture_website.py then render.py; see video/README.md.
- Downloads/Haven - Editable Project v2.zip includes Shotcut clips, website opening asset, narration/script and local recorder. Archive CRC checked and export SHA256 matched. Decode verified, contact-sheet reviewed by main.
- Recording URL: http://127.0.0.1:8941/Haven%20-%20Voiceover%20Recorder.html . Files also Downloads/Haven - Voiceover Recorder.html and Haven - Voiceover Script.txt. User clicks Record/permits mic,3s countdown,timed cues,Save recording. Keep tab visible; no automatic mic capture or external upload. Uses original silent guide with unchanged timings so user can record while v2 renders.
- Recorder tested end-to-end with fake media (no real microphone used). video/replace_voice.py replaces scratch narration after user saves their take; preserves source and refuses excess duration unless explicit --allow-trim. Retime captions if new wording or timing changes.
- Next: await user's take/revision feedback; do not publish or submit automatically. Current source progress remains local; only this STATUS handoff is pushed.
