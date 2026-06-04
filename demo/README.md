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
