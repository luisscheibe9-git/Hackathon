# Hackathon rules, schedule and judging

Source: [CPVC × OCOB × CPE AI Hackathon participant guide](https://cpvc-ai-hackathon-guide.vercel.app/#before-friday), read Fri 2026-11-13 ~8:45 PM. **If Discord says something different, Discord wins.** Event: Fri–Sun Nov 13–15, Cal Poly SLO. $10,000 in prizes.

## Deadlines (Pacific)

| When | What |
|---|---|
| Fri 5:00 PM | Build clock starts. Nothing in the demo may exist before this. |
| Fri 8:50 PM | Lock team on the registration site (2–4 people, final roster). |
| Sat 2:00 PM | **Project link due** (this GitHub repo works). Form link in Discord. |
| Sat 8:00 PM | **Sunday commit due**: confirm we present + send a live link judges can open. No commit = no judging slot. |
| Sun 12:00 PM | **Submissions close.** After that only setup, no features or fixes. |
| Sun 12:55 PM | Be in judging room (Cotchett). Stay until presented, then on campus till 3:30. |

Build rooms: Fri 5–9:45 PM, Sat 9:15 AM–9:45 PM, Sun 8:15 AM–12 PM. No overnight; doors lock 10 PM.

## Required events (workshops are mandatory)
- Fri 9:00 PM: Intro to Codex (Silo). Everyone gets a free ChatGPT seat with Codex + OpenAI API credits.
- Sat 10:00 AM: Customer discovery (Frost 181-0103, 10 min walk).
- Sat 11:00 AM: Industry talk, OpenAI (Frost 181-0103).
- Sat 5:00 PM: Business Model Canvas (Frost 181-0103).
- Sat 7:00 PM: How Sunday works (streamed).
- Sun 8:30 AM: Pitch workshop (Silo).
- Optional: Sat 12–4 PM Zoom office hours with a Walmart product/AI director, one 30-min slot per team, sign-up in Discord.

## Judging (100 points, same rubric in rooms and finals)

9-minute slot: **4 min live demo, 3 min questions**, 2 min switch. Two judges per room; room winner goes to finals (Sun 4:10 PM, Frost 181-0103).

| Points | Criterion | What "Top" looks like |
|---|---|---|
| 25 | Execution & design | Runs live, nothing faked, easy to use cold, looks like a real product. |
| 25 | Real problem, real user | Specific person with painful problem; real people used it this weekend, with proof. |
| 20 | Path to customers | Who pays, how much, why they switch; exactly where first users come from. |
| 15 | Pitch & demo | Judges care in 30 s; demo tells one user's story live; sharp honest answers. |
| 15 | Creative use of AI | A use judges haven't seen, and the product depends on it. |

Not scored: code difficulty, amount of AI used, majors. Tie-break: Real problem, then Execution.

## What this means for us (fall detection with ESP32 CSI)
- **Hardware is allowed**, but it must work **live at judging** in a Cotchett room we haven't calibrated. Plan a quick on-site calibration/recording step on Sunday morning (rooms open from 9:30) and keep a demo video as backup.
- **Creative use of AI (15 pts)**: a learned classifier on Wi-Fi CSI for privacy-preserving fall detection is a strong, uncommon AI use. Make it visible in the demo (live model output, not just a threshold). A generic chatbot bolted on scores low.
- **Real problem (25) + Path to customers (20) = 45 pts** are non-technical. Someone should talk to caregivers / assisted-living staff / families this weekend and capture proof (quotes, sign-ups). See [product.md](product.md).
- **Demo in first 30 s**: who it's for (e.g. an elderly person living alone and their family) and the problem (falls go unnoticed; cameras are invasive). Then one story: person walks in, falls, dashboard alerts with zone + time.
- **Live link required** by Sat 8 PM and Sun noon: the dashboard should be deployable (or a share link) so judges can open it.
- **Build check**: repo history must show work started after Fri 5 PM. This repo's first commit is Fri 6:11 PM, good. Don't delete commits, don't move to a fresh repo, don't squash history. Research notes before 5 PM are allowed; pre-built code is not.
- **Credit** everything we use (esp-csi, RuView, datasets) in the submission description; list each AI tool and what it did.
- **No secrets** in the repo or demo video. Only collect non-sensitive data from any test users and tell them it's a hackathon student project.

## Submission (one per team, form in Discord, by Sun 12 PM)
- Live link judges can open and try.
- Project link (this repo).
- Short description: problem, who has it, what we built, credits.
- AI tools used and what each did.
- Optional demo video < 2 min (unlisted YouTube/Loom, check it plays logged out). **Required to enter a challenge**; max one challenge per team. Challenges were announced at the Friday opening.
- Optional pitch deck link.

## Disqualifiers
Anything built before Fri 5 PM; outside help building it; made-up users/proof; false AI/credit disclosures; collecting sensitive data; Code of Conduct violations (includes building anything meant to surveil people, so frame our project clearly as consent-based, privacy-preserving safety monitoring).

## Pack for Sunday
Laptop + charger (demo on own laptop), ESP32s + USB cables + power, power strip/bank, HDMI adapter (finals), phone hotspot (Wi-Fi backup).
