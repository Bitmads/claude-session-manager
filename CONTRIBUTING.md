# Contributing

Thanks for considering a contribution! `csm` is small and deliberately simple —
this guide keeps it that way.

## The one rule: stdlib only

Everything is **Python 3 with zero dependencies**, only the standard library.
That's a feature, not a limitation. Please don't add pip packages, build
steps, or external binaries. If something seems to need a dependency, open an
issue first; there's usually a stdlib way.

- Target **Python 3.8+**.
- **Core = one file:** `cc-sessions`. No package, no `setup.py`, no framework.
  It must run on its own, with no adapters present.
- **Task-manager adapters = one file each** in `adapters/` (Linear, YouTrack,
  ...). Adding a tracker means adding a file there (or in
  `~/.claude/csm/adapters/`), never editing the core. Adapters don't import
  the core; they get an `http` helper injected. See
  [docs/plans/task-integrations.md](docs/plans/task-integrations.md).
- **Secrets live in `.env`** (gitignored). `.env.example` lists every variable
  and is committed.
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

## Adding a tracker adapter

One file in `adapters/` (or `~/.claude/csm/adapters/` for a private one). No
core edits. Use `adapters/linear.py` and `adapters/youtrack.py` as templates.

```python
class Jira:
    kind = "jira"                        # connections.<name>.type in csm.json

    def __init__(self, options, http):   # options = connection config + "token"
        self.http = http                 # injected: get_json / post_json, raises http.Error

    def get(self, key):                  # REQUIRED: task dict, or None if not found
        return {"key": key, "title": "...", "url": "", "status": "",
                "assignee": "", "project": "", "description": "", "updated": ""}

    # optional: search(text, limit, scope), recent(limit, scope), whoami()

ADAPTERS = [Jira]
```

- Don't import `cc-sessions`; everything you need is injected.
- `scope` is the tracker-side project for the current folder (may be `None`).
- Return `None` from `get` for "not found"; raise for anything else.
- Add tests in `tests/test_tasks.py` with a `FakeHttp` (no network). The
  contract test there covers every file in `adapters/` automatically.

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
