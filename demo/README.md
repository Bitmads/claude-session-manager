# Demo assets

The README GIF/MP4 are generated reproducibly with [VHS](https://github.com/charmbracelet/vhs)
running in Docker — no host tooling beyond Docker, and **no real session data** is
used (the demo runs against a curated fake `~/.claude`).

## Rebuild

```bash
cd demo
./build.sh
```

That:
1. `make_demo_data.py` writes a curated fake dataset into `demo/home/.claude`
   (reusing csm's own helpers so the data always matches the tool's logic).
2. Builds a small image: the official VHS image + `python3` + a UTF-8 locale +
   `cc-sessions` (see `Dockerfile`).
3. Runs `demo.tape` to render `picker.gif` (README hero) and `picker.mp4` (socials).

## Files

| File | Purpose |
|------|---------|
| `make_demo_data.py` | Generates the curated fake sessions, statuses, notes |
| `Dockerfile` | VHS + python3 + locale + the script |
| `demo.tape` | The scripted walkthrough (keystrokes, timing) |
| `build.sh` | One command: data → image → render the GIF/MP4 |
| `make_video.sh` | Composes `launch.mp4` (intro → captioned demo → CTA) |
| `STORYBOARD.md` | Plan for an even more polished hand-edited cut |
| `picker.gif` / `picker.mp4` | README demo (committed) |
| `launch.mp4` | Polished ~34s launch video, captions + cards (committed) |

## Launch video

`make_video.sh` turns `picker.mp4` into a polished, silent, captioned launch
video (`launch.mp4`, 1080p): a hook title card → the demo with timed
lower-third captions → a CTA card with the repo URL. It runs ffmpeg inside the
`csm-vhs` image (re-execs itself there), so no host ffmpeg/fonts needed:

```bash
cd demo
./build.sh        # produces picker.mp4 (prereq)
./make_video.sh   # produces launch.mp4
```

Captions are timed to the walkthrough; tweak the `between(t,…)` ranges or the
card text in `make_video.sh` and re-run. For a hand-tuned cut with music and
zoom, see `STORYBOARD.md`.

## Tweaking the walkthrough

Edit `demo.tape`. Keys are sent literally (`Down`, `Tab`, `Shift+Tab`, `Ctrl+E`,
`Ctrl+S`, `Type "…"`, `Sleep`). Change `Set Theme` / `Set FontSize` / `Set Width`
to restyle. The font is `DejaVu Sans Mono` because it's the bundled font that
contains the status glyphs (`◐ ◌`); most real terminals render those fine in any font.

To preview without re-rendering the GIF, extract frames:

```bash
docker run --rm -v "$PWD":/vhs --entrypoint ffmpeg csm-vhs \
  -i picker.mp4 -vf fps=1 frames_%02d.png
```

---

## Maintainer notes — how it was built (read this first to recreate/improve)

### Pipeline

```
make_demo_data.py ──► demo/home/.claude        (curated fake sessions)
        │
build.sh ──► docker build (Dockerfile) ──► docker run vhs demo.tape
        │                                          │
        └────────────────────────────────► picker.gif + picker.mp4
make_video.sh ──► ffmpeg in csm-vhs ──► launch.mp4   (cards + captions)
```

Three independent stages: **data → VHS render → ffmpeg compose**. The image is
named `csm-vhs` (built by `build.sh`); `make_video.sh` reuses it.

### Gotchas & decisions (the non-obvious stuff)

- **VHS image has no `python3`.** Base is `debian:stable-slim` (apt, not apk).
  `Dockerfile` adds `python3` + `locales`. Don't override VHS's `ENTRYPOINT`.
- **Font must contain `◐`/`◌` (wip/blocked icons).** Of the bundled fonts, only
  the **DejaVu** family has them — JetBrains Mono / Fira Code / Hack do NOT
  (checked with `fc-list ":charset=25D0"`). So `demo.tape` uses
  `DejaVu Sans Mono`. Real terminals render these in most fonts; this is a
  VHS-image-only constraint.
- **Locale + TERM.** Container needs `LANG/LC_ALL=en_US.UTF-8` and
  `TERM=xterm-256color` (set in `Dockerfile`) or box-drawing (`├── █░`) renders
  as mojibake and curses may bail.
- **Sandboxed data.** `demo.tape` sets `Env HOME "/vhs/home"` so csm reads the
  fake `~/.claude`. Never uses real session data. `make_demo_data.py` also sets
  `os.environ["HOME"]` **before importing** cc-sessions so its `CLAUDE_DIR`
  resolves to the demo home (and it reuses `extract_task_key`/`sanitize`/
  `_set_task_status`, so demo data can't drift from the tool).
- **Never press `Enter` on a session in the tape** — Enter runs
  `claude --resume`, which isn't installed in the container. The tape ends with
  `Escape`. `cd /home/dev/payments` (dir created in `Dockerfile`) before launch
  so "Current" scope is populated on the first frame.
- **VHS keys:** navigation uses named keys (`Down`, `Tab`, `Shift+Tab`, `Ctrl+E`,
  `Ctrl+S`, `Ctrl+R`) — `Shift+Tab` works. `Type "…"` for text.
- **ffmpeg `drawtext`:** `:` is the option separator — keep it out of caption/card
  text (use `-` / `to`). UTF-8 text is fine. Fonts live at
  `/usr/share/fonts/truetype/dejavu/` (`DejaVuSans-Bold.ttf`, etc.).
- **Caption timing** in `make_video.sh` is mapped to the tape's cumulative
  `Sleep` sequence (demo-local `t`). Captions are baked into the demo clip
  *before* the `xfade` concat, so the crossfade offsets don't shift them.
- **`xfade` offset = (sum of earlier clip durations) − crossfade duration.** All
  clips forced to 1920×1080, 25fps, `setsar=1`, `yuv420p` so xfade accepts them.
- **Verify by frames, not motion.** Extract stills (`ffmpeg -ss T -frames:v 1`)
  and look — that's how the `◐`-glyph and frontmatter-in-panel bugs were caught.
- **Committed vs ignored:** `picker.gif`, `picker.mp4`, `launch.mp4` are
  committed. `home/`, `frames_*`, `vchk_*`, `_*.mp4` are gitignored scratch.

### To change something fast

| Want to… | Edit | Then |
|----------|------|------|
| change what the demo shows | `make_demo_data.py` (the `SESSIONS` list) | `./build.sh` |
| change the walkthrough / pacing | `demo.tape` (`Sleep`, keys, `Set …`) | `./build.sh` |
| restyle (theme/font/size) | `demo.tape` `Set Theme/FontFamily/FontSize` | `./build.sh` |
| change captions / cards / timing | `make_video.sh` (`drawtext`, `between(t,…)`) | `./make_video.sh` |
| regenerate everything | — | `./build.sh && ./make_video.sh` |
