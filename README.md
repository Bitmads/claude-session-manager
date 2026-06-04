# Claude Session Manager (csm)

A terminal UI for managing Claude Code sessions. Browse, search, resume, and organize sessions with an interactive curses picker — no external dependencies beyond Python 3 stdlib.

<p align="center">
  <img src="demo/picker.gif" alt="csm — browse, search, and organize Claude Code sessions" width="850">
</p>

## Why

Claude Code has no session grouping. When you run 10+ sessions at 1M tokens each, finding and resuming the right one becomes painful. `csm` fixes that with a full-screen interactive picker, task-based grouping, context usage indicators, and session lifecycle tools.

## Install

```bash
git clone https://github.com/Bitmads/claude-session-manager.git
cd claude-session-manager
chmod +x cc-sessions

# Add alias to your shell
echo 'alias csm="python3 '$(pwd)'/cc-sessions"' >> ~/.zshrc
source ~/.zshrc
```

That's enough to run `csm`. For hooks, the `/hop` skill, clipboard copy, and
customizing the naming convention, see **[INSTALLATION.md](INSTALLATION.md)**.

## Usage

### Interactive picker

```bash
csm
```

Full-screen curses UI. Sessions grouped by task, sorted by recency. Right-side columns (timestamp, context bar, session ID) fixed at terminal edge. Responsive on resize.

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| Up/Down | Navigate sessions |
| Enter | Resume selected session |
| Esc | Quit |
| Tab | Toggle scope: Current directory / All |
| Shift+Tab | Cycle view: Grouped-Date, Grouped-A-Z, Flat-Date, Flat-A-Z |
| Type | Fuzzy search filter |
| Ctrl+E | Rename selected session |
| Ctrl+O | Add note to selected task |
| Ctrl+S | Cycle task status (open/wip/done/blocked) |
| Ctrl+X | Trash selected session (asks to confirm) |
| Ctrl+R | Refresh now (the picker also auto-refreshes) |
| Ctrl+D | Toggle detail panel |

### Start a new session

```bash
csm new "SET-123 Implement settlements"
# → claude -n "SET-123/1.001: Implement settlements"

csm new "SET-123/2 Implement settlements"
# → claude -n "SET-123/2.001: Implement settlements"

csm new "SET-123/2.005: Implement settlements"
# → claude -n "SET-123/2.005: Implement settlements"
```

All input formats normalize to `TICKET/PHASE.SESSION: Title`.

### Hop to next session (context continuation)

When context runs out, use `/hop` inside Claude Code or run from CLI:

```bash
csm hop                                    # latest session for cwd
csm hop "SET-123/1.003: Implement..."      # specific session by title
csm hop 5897ff98                           # by session ID prefix
csm hop --dry-run                          # print command without executing
```

Bumps the session number: `SET-123/1.003` → `SET-123/1.004`. Starts a new Claude session pointing at the previous transcript so Claude can read the full conversation and continue.

### Task status

```bash
csm status "SET-123" wip          # set status
csm status "SET-123"              # get status
```

Statuses: `open`, `wip`, `done`, `blocked`. Stored in task notes frontmatter. Shown as icons in the picker: ● done, ◐ wip, ○ open, ◌ blocked.

### Task notes

```bash
csm note "SET-123" "Left off at migration step"
csm note "SET-123"                # read notes
csm note                          # list all notes
```

Notes are auto-injected into Claude's context on SessionStart via the hook.

### Delete sessions

```bash
csm del 5897ff98                  # by session ID
csm del "old task name"           # by title fragment
```

Moves transcript to `~/.claude/trash/` (recoverable).

## Naming convention

The **default** session-title scheme:

```
TICKET/PHASE.SESSION: Title
```

| Component | Format | Example |
|-----------|--------|---------|
| Ticket | `XXX-NNN` | `SET-123` |
| Phase | integer after `/` | `/1`, `/2` (maps to git branch) |
| Session | 3-digit zero-padded after `.` | `.001`, `.002` (bumped by hop) |
| Title | free text after `: ` | `Implement multi-country settlements` |

Full example: `SET-123/1.003: Implement multi-country settlements`

**This is fully configurable** — you are not locked into it. The parse / bump /
group logic is driven by a named-group regex and templates in
`~/.claude/csm.json`. Bring your own scheme (`JIRA-123 v5`, `name-NNN`, anything).
Legacy titles (e.g. `Session Manager - v003`) work without any config.

See [Configuration](#configuration) below.

## Configuration

Optional JSON config at `~/.claude/csm.json` (or `$CSM_CONFIG`). Zero config =
sensible defaults. Inspect or create it:

```bash
csm config           # show effective config + where it loads from
csm config --init    # write a starter ~/.claude/csm.json
```

### Clipboard copy (off by default)

Have `/hop` copy its command to your clipboard. Set `copy.command` to `"auto"`
(detects pbcopy / wl-copy / xclip / xsel / clip.exe) or an explicit command:

```json
{ "copy": { "command": "auto" } }
```

Or override per-invocation with `$CSM_COPY_CMD`. Empty = disabled.

### Custom naming scheme

```json
{
  "naming": {
    "pattern": "^(?P<key>[A-Z]+-\\d+) v(?P<v>\\d+)$",
    "full_template": "{key} v{v}",
    "group_template": "{key}",
    "bump_field": "v"
  }
}
```

`ABC-42 v5` → hop → `ABC-42 v6`, grouped as `ABC-42`. Full reference and more
examples in **[INSTALLATION.md](INSTALLATION.md#6-customize-the-naming-convention-optional)**.

## Detail panel

The bottom panel (toggle with Ctrl+D) shows for the selected session:

- Title with status indicator
- Working directory and git branch
- Message count, context usage %, timestamps
- Task notes (if any)
- Last user message from the conversation

## Architecture

- Single Python script, stdlib only (`curses`, `json`, `pathlib`, `re`, etc.)
- No pip packages, no fzf, no external dependencies
- Reads Claude Code transcripts from `~/.claude/projects/*/`
- Task notes in `~/.claude/task-notes/*.md`
- Event log in `~/.claude/task-index.jsonl`
- Trashed sessions in `~/.claude/trash/`
- Terminal width via `ioctl(TIOCGWINSZ)` on `/dev/tty` for reliable detection

## File layout

```
~/.claude/bin/cc-sessions        → symlink or alias target
~/.claude/task-notes/*.md        → per-task notes with status frontmatter
~/.claude/task-index.jsonl       → hook event log
~/.claude/trash/*.jsonl          → trashed session transcripts
~/.claude/skills/hop/SKILL.md    → /hop skill for Claude Code
```

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The golden rule:
keep it a single, stdlib-only Python file.

## License

MIT
