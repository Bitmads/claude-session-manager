# Launch video storyboard (Tier 2)

A polished ~45s intro for Product Hunt / Twitter-X / the README, beyond the raw
VHS GIF. Silent with on-screen text captions (lands sound-off). 16:9, 1080p.

## Structure: hook → problem → demo → CTA

| Time | Beat | On-screen text (caption) | What's shown |
|------|------|--------------------------|--------------|
| 0–3s | **Hook** | "10 Claude Code sessions. 1M tokens each. Good luck finding the right one." | Fast scroll through a long, messy `claude --resume` list (or a blurred wall of sessions) |
| 3–6s | **Turn** | "csm groups them by task." | `csm` launches → clean grouped picker fades in |
| 6–14s | **Demo: browse** | "Status at a glance. Context usage. Live." | Cursor moves down the grouped list; status icons + context bars highlighted with a zoom |
| 14–22s | **Demo: find** | "Fuzzy-find across every project." | Type `oauth` → list filters; Tab toggles Current/All |
| 22–30s | **Demo: organize** | "Rename, set status, take notes — without leaving the picker." | Ctrl+E rename, Ctrl+S status cycle, detail panel with the note |
| 30–38s | **Demo: continue** | "Out of context? /hop into a fresh session — same thread, new title." | Show `/hop` producing the bumped `claude -n` command |
| 38–45s | **CTA** | "csm — your Claude Code sessions, organized.  github.com/Bitmads/claude-session-manager" | Logo/title card, repo URL, "pip-free · stdlib only" |

## Production (all free on Linux)

1. **Source footage** — record the terminal with **OpenScreen** (free, Linux,
   auto-zoom on keypresses) against the demo dataset:
   ```bash
   cd demo && python3 make_demo_data.py
   HOME="$PWD/home" csm     # or: HOME="$PWD/home" python3 ../cc-sessions
   ```
   Record a few clean takes of each beat. (Or reuse `picker.mp4` from VHS as the
   base and add zoom/captions in the editor.)
2. **Edit** in **Kdenlive**: title card (hook), trim dead air, add the captions
   above as high-contrast text (4–7 words, bottom third), 1 zoom per beat.
3. **Music** — a low, upbeat loop from **Pixabay Music** or **Uppbeat** (no
   attribution). Keep it under the captions.
4. **Captions** — burn in (don't rely on platform CC). Auto-draft with YouTube
   Studio or Choppity, then restyle in Kdenlive.
5. **Export** — 1080p H.264 16:9 master for README/YouTube/X. Re-crop a 1:1
   version for social feeds if needed.

## Tips
- Keep each shot ≤ 3s; cut on every action.
- The hook decides everything — lead with the pain, not the tool name.
- End on the repo URL held for ≥ 3s.
