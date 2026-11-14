# Agent instructions

Shared by Claude Code (via `CLAUDE.md`) and Codex (reads this file directly). Edit this file, not a tool-specific copy.

## Start of every session
1. `git fetch` and pull the branch you're on; teammates and other agents push here too.
2. Read `NOTES.md` (current state, decisions, next steps), then `research/README.md`.

## Project
Hackathon: camera-free fall detection for elder care using Wi-Fi CSI from 3 ESP32 boards. Scope is fall detection + room zone, not precise tracking. Details in `research/`.

## Working rules
- Planned layout: `firmware/` (ESP32), `detection/` (Python), `dashboard/` (web UI), `research/` (notes and sources).
- Work on a feature branch; ask before pushing to `main`.
- Commit small, tested steps with clear messages.
- Update `NOTES.md` (state, decisions, next steps) after any substantial change.
- Several humans and two AI agents (Claude Code, Codex) share this repo. Don't edit files another agent is actively working on; pull before you start and push when you stop.
- No secrets (Wi-Fi passwords, API tokens) in the repo. Put them in a git-ignored `.env` or `secrets.h`.
- Keep large files (raw CSI recordings, PDFs) out of git unless the team agrees; link or ignore them.

## Coordination
- The Claude Desktop session "Hackathon – MAIN (coordinator)" is the main thread. Other Claude sessions on this project report to it (SendMessage) when they finish work or get blocked; new work sessions are started from it.
- The team task list (owners, due times, status) is the Google Doc "Hackathon ideas", To DO LIST section: https://docs.google.com/document/d/1upIEmQUVUbZdIuxvN-gHEJgOShMZMWAb9dQ6_YxRwJs/edit
