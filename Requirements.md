# CCS — Claude Code Session Manager

> Technical specification for rebuilding `ccs` from scratch.
> Date: 2026-06-02

---

## 1. Overview

Claude Code has no session grouping. Multi-session tasks (10+ sessions, 1M tokens each) become unmanageable. `ccs` is a Python CLI tool that provides an fzf-based interactive picker to browse, search, and resume sessions — grouped by task, with context usage indicators.

**One command, one UI.** There is no separate `list` command. The picker is the list. Running `ccs` (no args) launches the picker. Selecting a session resumes it via `claude --resume`.

---

## 2. Requirements

### Must-Have

| #   | Requirement                                                    | Status  |
| --- | -------------------------------------------------------------- | ------- |
| R1  | Interactive fzf picker as primary and only UI                  | Working |
| R2  | Session grouping by task key (strip version/status prefixes)   | Working |
| R3  | Three-tier title: custom (★ bright), auto (○ normal), fallback (· dim) | Working |
| R4  | Context bar: color-coded blocks + percentage (green/yellow/red) | Working |
| R5  | Scope: Current (cwd + subdirs) / All — toggle with Tab         | Working |
| R6  | Four view presets cycled with ←/→: Grouped·Date, Grouped·A-Z, Flat·Date, Flat·A-Z | Working |
| R7  | Tab bar header showing active scope and view                   | Working |
| R8  | Project section headers in grouped views (non-selectable)      | Working |
| R9  | Tree-view (├── └──) for multi-session groups; single-session = one-liner | Working |
| R10 | Responsive layout: right columns at terminal edge, title fills remainder | **Broken** |
| R11 | Per-task notes (`ccs note`), auto-injected on SessionStart     | Working |
| R12 | Hook integration: SessionStart, SessionEnd, PreCompact         | Working |
| R13 | No message count column                                        | Working |
| R14 | No session count column                                        | Working |
| R15 | Project labels use `/` not `-`                                 | Working |
| R16 | Project name only in section header, not per row               | Working |
| R17 | View labels use "Date" not "Recent"                            | Working |

### Nice-to-Have

| #  | Requirement                        |
| -- | ---------------------------------- |
| N1 | Asc/desc sort toggle               |
| N2 | External ticket integration        |
| N3 | Git branch filtering               |

---

## 3. Architecture

### 3.1 Single Python script, stdlib only

`~/.claude/bin/cc-sessions` — imports: `json`, `sys`, `os`, `re`, `time`, `subprocess`, `pathlib`, `shlex`, `tempfile`, `collections.defaultdict`, `datetime`. No pip packages.

Alias in `~/.zshrc`: `alias ccs='python3 ~/.claude/bin/cc-sessions'`

### 3.2 Single rendering pipeline

One function builds rows. The picker and any fallback list use the same output. No divergent code paths.

```
_build_rows(sessions, scope, view_idx, term_w)
  → list of {sid, name_str, ts, bar, sid8, is_header}
```

### 3.3 fzf invocation

fzf needs direct TTY access. The only working pattern:

```python
os.system(f'fzf --ansi ... < {tmp_in} > {tmp_out}')
```

State (scope, view index) persists in `/tmp/ccs-pick-state.json` because `reload()` spawns a fresh process.

### 3.4 Hooks

Configured in `~/.claude/settings.json` (already in place, do not modify other hooks):

- **SessionStart** — index event + print task notes to stdout (injected into Claude context)
- **SessionEnd** — index event
- **PreCompact** — index event

Hook receives JSON on stdin: `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `reason`, `source`.

### 3.5 Task key resolution (hook)

1. tmux window name (excluding `bash`, `zsh`, `fish`, `python`, `claude`)
2. `CC_TASK` env var
3. `custom-title` from transcript
4. cwd basename
5. `'untagged'`

### 3.6 Task notes

Markdown files in `~/.claude/task-notes/<sanitized-name>.md`. Append via `ccs note 'task' 'text'`. On SessionStart, matching note content (≤4000 chars) is printed to stdout.

---

## 4. Data Model

### Transcript location

`~/.claude/projects/<encoded-path>/*.jsonl`

Encoding: `/media/nvme4tb/DEV/settlemate` → `-media-nvme4tb-DEV-settlemate`. Filename stem = session UUID.

### Relevant record types

| Type           | Key fields                                              |
| -------------- | ------------------------------------------------------- |
| `custom-title` | `customTitle`, `sessionId`                              |
| `ai-title`     | `aiTitle`, `sessionId`                                  |
| `user`         | `message.content`, `cwd`, `gitBranch`, `timestamp`      |
| `assistant`    | `message.usage.{input_tokens, cache_creation_input_tokens, cache_read_input_tokens}`, `timestamp` |

### Session metadata (extracted per transcript)

```python
{
    'session_id': str,       # UUID from record or filename stem
    'title': str | None,     # custom_title > ai_title > first_user_msg snippet
    'renamed': bool,         # custom-title exists
    'auto_named': bool,      # ai-title exists
    'task_key': str | None,  # title with version/status stripped
    'project': str,          # encoded project dir name
    'cwd': str,
    'branch': str,
    'first_ts': str,         # ISO timestamp
    'last_ts': str,
    'msg_count': int,
    'ctx_tokens': int,       # peak (input + cache_creation + cache_read)
    'transcript': str,       # full path
}
```

### Task key extraction

Strip from title:
- Status prefixes: `[DONE]`, `[WIP]`, `[INIT]`, `[V2]`, `DONE -`, etc.
- Version suffixes: `- v001`, `- #3`, `(v2)`, etc.

`"[DONE] - Refactor X - v003"` → `"Refactor X"`

### Task index (`~/.claude/task-index.jsonl`)

Append-only JSONL: `{ts, iso, event, task, session_id, cwd, branch, transcript_path, reason, source}`

---

## 5. UI Specification

### 5.1 Columns

| Column       | Width         | Content                     |
| ------------ | ------------- | --------------------------- |
| Icon + Title | **flex** (fills remaining) | `★`/`○`/`·` + session title |
| Timestamp    | fixed, 7 chars | `now`, `5m ago`, `3d ago`, `May 15` |
| Context bar  | fixed, ~10 chars | `███░░ 58%` — green (<50%), yellow (50–80%), red (>80%) |
| Session ID   | fixed, 8 chars | first 8 of UUID             |

Gap between columns: 2 spaces. **Not shown:** message count, session count.

### 5.2 Title tiers

| Icon | Condition       | Title style  | Icon color |
| ---- | --------------- | ------------ | ---------- |
| `★`  | User renamed    | Bright white | Green      |
| `○`  | Auto-generated  | White        | Cyan       |
| `·`  | Fallback snippet | Dim         | Dim        |

### 5.3 Grouped views

```
  ━━ settlemate ━━

  ★ Canada / UK Settlements Refactoring Init          9h ago  █░░░░ 17%
    ├── ● Canada / UK Settlements Refactoring Init     9h ago            7bdc4f85
    └── ● Canada / UK Settlements Refactoring Init    13d ago  █░░░░ 17%  eacf293b
  ○ Continue multi-country refactor v5                 1h ago  ███░░ 52%  cd3c2712
```

- Project section header: yellow `━━ name ━━`, non-selectable
- Multi-session groups: tree connectors (`├──`, `└──`)
- Single-session tasks: compact one-liner, no tree
- Project name in header only, not per row

### 5.4 Flat views

No headers, no tree. Project name inline per row.

### 5.5 Sorting

- **Date:** descending by `last_ts`
- **A-Z:** ascending by title (grouped mode: project first, then title)

### 5.6 Navigation

| Key       | Action                        |
| --------- | ----------------------------- |
| Tab       | Toggle Current ↔ All          |
| ← →       | Cycle view preset             |
| Enter     | Resume selected session       |
| Esc       | Cancel                        |
| Type      | fzf fuzzy search              |

### 5.7 Tab bar (fzf `--header-lines=1`)

```
 ▸Current  All  │  ▸Grouped·Date  Grouped·A-Z  Flat·Date  Flat·A-Z  │  Tab: scope  ◀ ▶: view
```

Active = bold + `▸`. Inactive = dim.

### 5.8 Project label formatting

Encoded dir name → split on `-` → remove noise words (`media`, `nvme4tb`, `DEV`, `mnt`, `network`, `nas`, `data`, `cloud`, `bitmads`, `files`, `OneDrive`, `pitt`, `jss`, `hu`, `home`, `Obsidian`, `pitt@jss.hu`) → keep last 2 segments → join with `/`.

`-mnt-network-...-Obsidian-Bitnotes` → `Bitnotes`
`-media-nvme4tb-DEV-settlemate` → `settlemate`

Fallback when all filtered: last 2 raw segments joined with `/` (`-home-pitt` → `home/pitt`).

---

## 6. Responsive Layout

This was the only unsolved problem. Everything else works.

### 6.1 The requirement

Right-side columns (timestamp + bar + sid) always sit at the **terminal edge**. The title column fills the remaining space. Long titles truncate with `…` when the terminal is narrow. The layout adapts when the terminal is resized and the command is re-run.

### 6.2 Why previous attempts failed

Every attempt used a **single column width** (`cap`) shared across all rows:

| Approach | Result |
| -------- | ------ |
| `cap = 58` (hardcoded) | Not responsive |
| `cap = term_w - 36` | Short titles get massive gap before timestamp |
| `cap = min(longest_title, term_w - 36)` | Right columns stuck at longest title, not terminal edge |

A single number cannot satisfy both "no gap after short titles" and "right columns at terminal edge."

### 6.3 The solution: per-row padding

Each row computes its own padding. Right columns are built as a fixed string. Padding fills the gap between the title and the right side.

```python
def format_row(name_str, ts_str, bar_str, sid_str, tw):
    # Build right side
    right_parts = [f'  \033[2m{ts_str:>7s}\033[0m']
    if bar_str:
        right_parts.append(f'  {bar_str}')
    if sid_str:
        right_parts.append(f'  \033[2m{sid_str}\033[0m')
    right_str = ''.join(right_parts)
    right_w = vis_len(right_str)

    # Available space for name
    max_name = tw - right_w
    name_w = vis_len(name_str)

    # Truncate if needed
    if name_w > max_name:
        name_str = ansi_truncate(name_str, max(max_name - 1, 3)) + '…'
        name_w = max_name

    # Pad to push right side to edge
    pad = max(max_name - name_w, 0)
    return f'{name_str}{" " * pad}{right_str}'
```

At width 120, "Blockchain" (14 chars): pad = 75, right side at col 120.
At width 120, "Extend ID verification..." (55 chars): pad = 34, right side at col 120.
At width 80, "Extend ID verification..." truncated to ~43 chars, right side at col 80.

### 6.4 Terminal width detection

```python
def term_width():
    # 1. FZF_COLUMNS (fzf >= 0.46 only — user has 0.29, won't fire)
    # 2. COLUMNS env var (works because 'export COLUMNS' is in .zshrc)
    # 3. os.get_terminal_size on fd 0, 1, 2 (first that succeeds)
    # 4. stty size via /dev/tty
    # 5. fallback: 100
    for var in ('FZF_COLUMNS', 'COLUMNS'):
        v = os.environ.get(var)
        if v and v.isdigit() and int(v) > 0:
            return int(v)
    for fd in (0, 1, 2):
        try:
            return os.get_terminal_size(fd).columns
        except (OSError, ValueError):
            continue
    try:
        out = subprocess.check_output(
            ['stty', 'size'], stderr=subprocess.DEVNULL,
            stdin=open('/dev/tty'))
        return int(out.split()[1])
    except Exception:
        pass
    return 100
```

**Why `export COLUMNS` in `.zshrc` is required:** zsh maintains `COLUMNS` as a shell variable (auto-updated on resize) but does not export it by default. Without `export`, Python child processes cannot read it. This is the primary detection path for both direct terminal use and fzf reload subprocesses.

**Why not `shutil.get_terminal_size()`:** it silently returns 80 on failure. You cannot distinguish a real 80-col terminal from a broken fallback.

### 6.5 ANSI-safe truncation

`len()` counts escape codes. Slicing colored strings breaks mid-sequence. Required utilities:

```python
ANSI_RE = re.compile(r'\033\[[0-9;]*[a-zA-Z]')

def vis_len(s):
    return len(ANSI_RE.sub('', s))

def ansi_truncate(s, max_visible):
    result, visible, i = [], 0, 0
    while i < len(s):
        if s[i] == '\033' and i + 1 < len(s) and s[i + 1] == '[':
            j = i + 2
            while j < len(s) and not s[j].isalpha():
                j += 1
            if j < len(s):
                j += 1
            result.append(s[i:j])
            i = j
        else:
            if visible >= max_visible:
                break
            result.append(s[i])
            visible += 1
            i += 1
    result.append('\033[0m')
    return ''.join(result)
```

---

## 7. Technical Constraints

### fzf 0.29

| Works                            | Broken                          |
| -------------------------------- | ------------------------------- |
| `--ansi`, `--header-lines`, `--no-sort`, `--reverse` | `ctrl-<number>` keybindings     |
| `--bind key:reload(cmd)`         | `--with-nth` / `--delimiter`    |
| `tab`, `left`, `right` binds     | `FZF_COLUMNS` (needs ≥ 0.46)   |

### Environment

- Shell: zsh
- fzf: 0.29 at `/usr/bin/fzf`
- Python 3, stdlib only
- Pop!_OS (Ubuntu-based)
- tmux available, not always active
- No Rich/Textual/gum/dialog

### Performance

~1.2s to scan ~130K lines across all project transcripts. Acceptable for interactive use.

### Existing config (do not modify)

```
~/.zshrc:
  export COLUMNS
  alias ccs='python3 ~/.claude/bin/cc-sessions'

~/.claude/settings.json:
  hooks.SessionStart → python3 ~/.claude/bin/cc-sessions hook
  hooks.SessionEnd   → python3 ~/.claude/bin/cc-sessions hook
  hooks.PreCompact   → python3 ~/.claude/bin/cc-sessions hook
```

---

## 8. Current Code — What to Keep

These functions in `~/.claude/bin/cc-sessions` are correct and should be preserved:

| Function              | Purpose                                    |
| --------------------- | ------------------------------------------ |
| `extract_task_key()`  | Regex chain stripping version/status       |
| `scan_transcripts()`  | Read all JSONL, extract metadata           |
| `_parse_transcript()` | Parse one transcript file                  |
| `group_sessions()`    | Group by task key, sort by recency         |
| `fmt_ts()`            | Relative timestamp formatting              |
| `proj_label()`        | Project dir → clean label with `/`         |
| `ctx_bar()`           | Color-coded context usage bar              |
| `session_label()`     | Three-tier title styling                   |
| `cmd_hook()`          | Hook entry point                           |
| `_resolve_task()`     | Task key resolution chain                  |
| `cmd_note()`          | Task notes CRUD                            |
| `_term_width()`       | Terminal width detection chain             |
| `_vis_len()`          | ANSI-aware visible length                  |

**Rewrite:** the entire row rendering and layout system. Replace single-`cap` approach with per-row `format_row()` from Section 6.3. Unify into one rendering pipeline shared by picker and fallback list.

---

## 9. File Layout

```
~/.claude/bin/cc-sessions        # main script
~/.claude/task-notes/*.md        # per-task scratchpads
~/.claude/task-index.jsonl       # hook event log
/tmp/ccs-pick-state.json         # ephemeral fzf state
```

---

## 10. Rebuild Checklist

- [ ] Per-row padding via `format_row()` (Section 6.3)
- [ ] `ansi_truncate()` (Section 6.5)
- [ ] Single rendering pipeline for picker + fallback
- [ ] `ccs` with no args → launch picker
- [ ] Test at 80, 120, 200 cols with short and long titles
- [ ] Test inside fzf reload (COLUMNS detection)
- [ ] Tree-view for multi-session groups
- [ ] Single-session tasks: compact one-liner
- [ ] Section headers non-selectable in fzf
- [ ] Tab = scope toggle, ←/→ = view cycle
- [ ] Hook injects task notes on SessionStart
- [ ] No message count, no session count columns
- [ ] Project labels use `/`
- [ ] Grouped view: project name in header only
