# Claude Session Manager (csm)

A terminal UI for managing Claude Code sessions. Browse, search, resume, and organize sessions with an interactive curses picker — no external dependencies beyond Python 3 stdlib.

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

### Hook setup

Add to `~/.claude/settings.json` to enable session tracking and task notes injection:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{ "type": "command", "command": "python3 /path/to/cc-sessions hook" }]
    }],
    "SessionEnd": [{
      "hooks": [{ "type": "command", "command": "python3 /path/to/cc-sessions hook" }]
    }],
    "PreCompact": [{
      "hooks": [{ "type": "command", "command": "python3 /path/to/cc-sessions hook" }]
    }]
  }
}
```

### /hop skill

Copy `skills/hop/` to `~/.claude/skills/hop/` to enable the `/hop` slash command inside Claude Code for session continuation.

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
| Ctrl+O | Add note to selected task |
| Ctrl+S | Cycle task status (open/wip/done/blocked) |
| Ctrl+X | Trash selected session |
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

Legacy titles (e.g. `Session Manager - v003`) are still supported.

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

## License

MIT
