# Installation

`csm` is a single Python 3 script with **zero dependencies** — only the standard library. No pip, no fzf, no Node. Works on Linux, macOS, and WSL.

## Requirements

- Python 3.8+
- Claude Code CLI (`claude`)
- A terminal (curses-capable — any modern terminal works)

## 1. Get the script

```bash
git clone https://github.com/Bitmads/claude-session-manager.git
cd claude-session-manager
chmod +x cc-sessions
```

## 2. Add an alias

Add to `~/.zshrc` (or `~/.bashrc`):

```bash
alias csm='python3 /full/path/to/claude-session-manager/cc-sessions'
```

Reload: `source ~/.zshrc`. Now `csm` launches the picker.

## 3. Hook setup (optional but recommended)

Hooks track sessions and auto-inject task notes when you resume. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{ "type": "command", "command": "python3 /full/path/to/cc-sessions hook" }]
    }],
    "SessionEnd": [{
      "hooks": [{ "type": "command", "command": "python3 /full/path/to/cc-sessions hook" }]
    }],
    "PreCompact": [{
      "hooks": [{ "type": "command", "command": "python3 /full/path/to/cc-sessions hook" }]
    }]
  }
}
```

## 4. /hop skill (optional)

The `/hop` slash command continues a session in a fresh one when context fills up.

```bash
cp -r skills/hop ~/.claude/skills/hop
```

Edit the path inside `~/.claude/skills/hop/SKILL.md` to point at your `cc-sessions`.

## 5. Clipboard copy (optional)

`/hop` prints a command to start the continuation session. To have it copied to your clipboard automatically, configure a copy command. **Off by default.**

Create the config:

```bash
csm config --init        # writes ~/.claude/csm.json
```

Then set `copy.command`. Easiest is `"auto"` (detects the right tool for your OS):

```json
{ "copy": { "command": "auto" } }
```

`auto` picks the first available of:

| OS / session | Tool | Install |
|--------------|------|---------|
| macOS | `pbcopy` | built-in |
| Linux (Wayland) | `wl-copy` | `sudo apt install wl-clipboard` |
| Linux (X11) | `xclip` | `sudo apt install xclip` |
| Linux (X11) | `xsel` | `sudo apt install xsel` |
| WSL | `clip.exe` | built-in |
| Windows | `clip` | built-in |

Or set an explicit command:

```json
{ "copy": { "command": "wl-copy" } }
```

You can also override per-invocation with the `$CSM_COPY_CMD` env var. Leave it empty to disable.

## 6. Customize the naming convention (optional)

The default session-title scheme is:

```
TICKET/PHASE.SESSION: Title       e.g.  SET-123/1.001: Implement settlements
```

You are **not** locked into it. The naming logic is fully config-driven via a named-group regex plus templates. Four keys in `~/.claude/csm.json`:

| Key | Meaning |
|-----|---------|
| `pattern` | Regex with named groups `(?P<name>...)` that parses a title |
| `full_template` | Rebuilds the full title — `str.format` with the groups |
| `group_template` | Rebuilds the grouping key (usually omits the bumped field) |
| `bump_field` | Which numeric group `csm hop` increments |

The field named by `bump_field` is coerced to an integer, so `{session:03d}` zero-pads correctly. All other groups keep their captured text.

### Examples

**Default (ticket / phase / session):**

```json
{
  "naming": {
    "pattern": "^(?P<ticket>[A-Za-z]+-\\d+)/(?P<phase>\\d+)\\.(?P<session>\\d{3}):\\s*(?P<title>.+)$",
    "full_template": "{ticket}/{phase}.{session:03d}: {title}",
    "group_template": "{ticket}/{phase}: {title}",
    "bump_field": "session"
  }
}
```
`SET-123/1.001: Title` → hop → `SET-123/1.002: Title`, grouped as `SET-123/1: Title`.

**Simple `JIRA-123 v5` scheme:**

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
`ABC-42 v5` → hop → `ABC-42 v6`, grouped as `ABC-42`.

**Plain `name-NNN` scheme:**

```json
{
  "naming": {
    "pattern": "^(?P<name>.+)-(?P<n>\\d{3})$",
    "full_template": "{name}-{n:03d}",
    "group_template": "{name}",
    "bump_field": "n"
  }
}
```
`refactor-auth-004` → hop → `refactor-auth-005`, grouped as `refactor-auth`.

Titles that don't match your pattern still work — `csm` falls back to a generic bump (`Title - v002`, `(v2)`, `#3`, etc.) and groups by the cleaned title.

Remember: in JSON, backslashes in the regex must be doubled (`\\d`, not `\d`).

## Verify

```bash
csm config        # show effective config + where it's read from
csm               # launch the picker
```
