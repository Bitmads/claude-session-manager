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
| `build.sh` | One command: data → image → render |
| `STORYBOARD.md` | Plan for the polished ~45s launch video (Tier 2) |
| `picker.gif` / `picker.mp4` | Rendered output (committed) |

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
