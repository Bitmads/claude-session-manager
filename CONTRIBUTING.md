# Contributing

Thanks for considering a contribution! `csm` is small and deliberately simple —
this guide keeps it that way.

## The one rule: stdlib only

`cc-sessions` is a **single Python 3 file with zero dependencies** — only the
standard library. That's a feature, not a limitation. Please don't add pip
packages, build steps, or external binaries. If something seems to need a
dependency, open an issue first; there's usually a stdlib way.

- Target **Python 3.8+**.
- One file: `cc-sessions`. No package, no `setup.py`, no framework.
- Match the surrounding style (naming, ~4-space indent, the `_private` helper
  convention, the section-comment banners).

## Develop

```bash
git clone https://github.com/Bitmads/claude-session-manager.git
cd claude-session-manager
chmod +x cc-sessions

# run it against a sandbox dataset (never touches your real ~/.claude)
python3 demo/make_demo_data.py
HOME="$PWD/demo/home" python3 cc-sessions
```

Using the demo dataset (`demo/home`) for development means you can rename,
restatus, delete, etc. without affecting your real sessions.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Add a test for any logic change. The suite is stdlib `unittest`, no deps. CI
(`.github/workflows/ci.yml`) compiles the script, runs the tests, and exercises
the non-interactive commands on every push/PR — keep it green.

## Things to know before changing behavior

- **The picker is curses.** It needs a real TTY; you can't unit-test the UI.
  Test the pure helpers (parse/bump/group/status/format) instead — that's what
  `tests/` does.
- **Naming is config-driven.** Parse/bump/group go through `_parse_title` /
  `_render_title` using `~/.claude/csm.json`. Don't hard-code a scheme; if you
  change defaults, update the tests and `INSTALLATION.md`.
- **Resume / new / hop exec `claude`** on the host. That's intentional and is
  why csm can't be fully containerized — don't try to work around it with
  fragile wrappers.
- **Terminal width** comes from `ioctl(TIOCGWINSZ)` on `/dev/tty`; the picker
  live-refreshes via a cheap mtime signature. Keep both cheap.

## Demo assets (gif / video)

The README GIF and launch video are reproducible — see
[`demo/README.md`](demo/README.md) ("Maintainer notes"). If a change alters the
UI, regenerate them:

```bash
cd demo && ./build.sh && ./make_video.sh
```

## Pull requests

1. Branch from `main`.
2. Keep the change focused; one concern per PR.
3. Add/adjust tests; make sure `python3 -m unittest discover -s tests` passes.
4. Don't reformat unrelated code.
5. Describe what changed and why.

## Reporting bugs / ideas

Open an issue with your OS, terminal, Python version, and steps to reproduce.
For UI bugs, a screenshot or the exact session-list shape helps a lot.
