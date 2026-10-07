# Plan: task-manager integrations (Linear, YouTrack, plugins)

Status: **Phase 0 + 1 done** (2026-10-07). Live API check pending tokens; Phase 2 next.

## Goal

Stop hand-typing ticket titles. `csm new SET-1234` should look the ticket up in
the task manager the current project uses and start
`SET-1234/1.001: <real ticket title>`. Later: search and pick tasks inside the
picker, and TAB-complete ticket keys in the shell.

Different folders use different trackers:

| Project folder | Tracker | Project / team | Key prefix |
|---|---|---|---|
| `/media/nvme4tb/DEV/settlemate` | Linear | Settlemate | `SET-` |
| Visited repo | YouTrack | Visited | `VIS-` (confirm) |
| Bitmads repos | YouTrack | Bitmads | `BIT-` (confirm) |

Anyone must be able to add a tracker (Jira, GitHub Issues, ...) by dropping in
one adapter file, **without editing the core**.

## Deliverables, in order

All three are planned; they share one adapter layer, so later phases are cheap.

| Phase | What you get | Why this order |
|---|---|---|
| 0 | Refactor: `new` uses the configured naming templates | removes a DRY bug the rest builds on |
| 1 | Adapter layer, Linear and YouTrack adapters, `csm new SET-1234` auto-title, `csm tasks`, `csm connections` | the biggest win for the least code |
| 2 | Task search in the picker: Ctrl+T (and `csm new` with no args) opens a search with a list and a detail pane | browse and pick without knowing the key |
| 3 | Shell TAB completion for `csm new <TAB>` (zsh and bash), served from a local cache | fast muscle-memory path |

---

## Phase 0: DRY fix in `new`

`cmd_new` hard-codes `f"{ticket}/{phase}.{session:03d}: {title}"` and
`_parse_new_input` hard-codes the `SET-123/2.005` regex. Both bypass the
`naming` config that `hop` and grouping already use, so a custom naming scheme
breaks `csm new`.

- Build the title with `_render_title(naming.full_template, groups, bump_field)`.
- Keep `_parse_new_input` for the input shorthand, but return named groups
  (`ticket`, `phase`, `session`, `title`) and make `title` optional. `SET-1234`
  alone becomes valid input; Phase 1 fills in the title.
- Tests: the existing `new` formats, plus the custom-scheme cases from
  `INSTALLATION.md`.

## Phase 1: adapter layer + auto-title

### Architecture

```
cc-sessions (core, single file)                adapters/ (one file per tracker)
┌──────────────────────────────────────┐       ┌───────────────────────────┐
│ TaskSource protocol (the interface)  │◄──────│ linear.py   class Linear  │
│ Task record (the shared shape)       │       │ youtrack.py class YouTrack│
│ Registry: discover + validate        │       └───────────────────────────┘
│ Factory: make_source(connection cfg) │       ~/.claude/csm/adapters/*.py
│ Router: cwd / key prefix → source    │       (user plugins, same contract)
│ Cache, secrets, HTTP helper          │
│ Callers: new, tasks, picker, complete│
└──────────────────────────────────────┘
```

**Interface (protocol, duck-typed).** Adapters do not import the core, which
keeps plugins dependency-free and avoids import cycles with a script that has
no `.py` extension. The core checks the shape when it loads the plugin.

```python
class Task:            # a plain dict in practice; these keys, all strings
    key                # "SET-1234": always present
    title              # always present
    url, status, assignee, project, description, updated   # "" if unknown

class TaskSource:      # what an adapter file must provide
    kind = "linear"                         # registry name, used in config "type"
    def __init__(self, options, http): ...  # options = connection config; http injected
    def get(self, key) -> Task | None              # REQUIRED
    def search(self, text, limit, scope) -> [Task] # optional, enables picker search
    def recent(self, limit, scope) -> [Task]       # optional: open tasks, newest first
    def whoami(self) -> str                        # optional: `csm connections` auth check
```

As built: `TASK_FIELDS`, `Http`, `HttpError`, `TaskSourceError`,
`_adapter_registry`, `make_source`, `route`, `fetch_task`, `list_tasks` and
the cache helpers are in the "Task sources" section of `cc-sessions`.

**SOLID mapping:**
- **S:** adapters only talk to their API and map responses to `Task`. Routing,
  caching, secrets and UI stay in the core.
- **O:** a new tracker is a new file. No core edits, no `if kind == ...`.
- **L:** every adapter returns the same `Task` shape. A missing optional method
  means the capability is absent, never a crash.
- **I:** only `get` is required. `search` and `recent` are opt-in.
- **D:** the core depends on the protocol. Adapters receive an injected `http`
  helper (stdlib `urllib`: JSON, timeout, error mapping) and resolved options,
  so tests inject a fake `http`.

**Discovery (registry).** Load `*.py` from `<repo>/adapters/` (built-in) and
then `~/.claude/csm/adapters/` (user plugins; can override a built-in with the
same `kind`). Each module exposes `ADAPTERS = [ClassName, ...]`. A broken
plugin prints one warning and is skipped; it never takes the core down.

**Factory.** `make_source(name)` reads `connections[name]`, resolves secrets,
looks up `registry[type]` and instantiates it with `(options, http)`. Instances
are memoized per run.

### Config (as built; in `~/.claude/csm.json`)

```json
{
  "connections": {
    "linear":   { "type": "linear", "token_env": "LINEAR_API_KEY", "prefixes": ["SET"] },
    "youtrack": { "type": "youtrack", "url": "https://visited.youtrack.cloud",
                  "token_env": "YOUTRACK_TOKEN",
                  "prefixes": ["VIS", "BIT", "BOS", "CLA", "HH", "PHN", "SDU", "LAB"] }
  },
  "folders": [
    { "path": "/media/nvme4tb/DEV/settlemate",             "connection": "linear",   "scope": "SET" },
    { "path": "/media/nvme4tb/DEV/visited.to",             "connection": "youtrack", "scope": "VIS" },
    { "path": "/media/nvme4tb/DEV/bitmads.com",            "connection": "youtrack", "scope": "BIT" },
    { "path": "/media/nvme4tb/DEV/claude-session-manager", "connection": "youtrack", "scope": "BIT" }
  ]
}
```

- A **connection** is one tracker account (adapter type, URL, token). One
  YouTrack connection serves every project on that instance; Visited and
  Bitmads are both projects on `visited.youtrack.cloud` (found in Peter's
  logged-in browser, 2026-10-07).
- **Secrets:** `token_env` names a variable read from the real environment,
  then from `.env` next to `cc-sessions` (or `$CSM_ENV_FILE`). The resolved
  value is passed to the adapter as `options["token"]`, never logged or cached.
- **Routing, first match wins:**
  1. explicit `--from <connection>` (`csm tasks`);
  2. the ticket's prefix is in a connection's `prefixes` (so `csm new SET-12`
     works from any folder);
  3. the longest `folders[].path` containing the current directory, which also
     gives the `scope` (project) for `search`/`recent`;
  4. none → a title is required, as before.
- Not built (dropped as unneeded): a per-repo `.csm.json`.

### Adapters (verified against the official docs, 2026-10-07)

**Linear**: GraphQL `POST https://api.linear.app/graphql`, header
`Authorization: <API_KEY>` (personal key, **no** `Bearer`).
- get: `issue(id: "SET-1234") { identifier title url description state { name } assignee { name } updatedAt }`.
  `issue(id:)` accepts the human identifier.
- search: `searchIssues(term: $term, first: N)`, rate-limited to about 30
  requests/min, so the picker debounces and caches.
- recent: `issues(filter: { team: { key: { eq: "SET" } }, state: { type: { nin: ["completed","canceled"] } } }, first: N, orderBy: updatedAt)`.
  Verified against the SDK schema (`packages/sdk/src/schema.graphql`, 2026-10-07):
  `IssueFilter.team/state`, `WorkflowStateFilter.type: StringComparator`,
  `PaginationOrderBy { createdAt updatedAt }`, `searchIssues(term, first, filter)`,
  `IssueSearchResult` has the same fields, `viewer { name }`.
- Not verified without a key: the exact error text for a missing issue. The
  adapter treats any error containing "not found" as `None`.
- Sources: <https://linear.app/developers/graphql>, schema at
  <https://studio.apollographql.com/public/Linear-API/schema/reference>

**YouTrack**: REST at `<base>/api/`, header `Authorization: Bearer perm:...`.
- get: `GET /api/issues/SP-38?fields=idReadable,summary,description,resolved,project(shortName)`.
  The readable ID is accepted in the path.
- search / recent: `GET /api/issues?query=project: VIS #Unresolved <text>&fields=...&$top=N`.
- Status: `resolved` is a timestamp (null means open). State and Assignee
  come from `customFields(name,value(name,fullName,login))`.
- Not verified without a token: that a missing issue returns 404 (the adapter
  maps 404 to `None`).
- Live check 2026-10-07 with a bogus token: both `api.linear.app` and
  `visited.youtrack.cloud` answer HTTP 401, so URLs and auth headers reach
  the right endpoints.
- Sources: <https://www.jetbrains.com/help/youtrack/devportal/operations-api-issues.html>,
  <https://www.jetbrains.com/help/youtrack/devportal/authentication-with-permanent-token.html>

### Commands

- `csm new SET-1234`: fetch the title, then start
  `claude -n "SET-1234/1.001: <title>"`. Print the resolved title on stderr
  first so you see it. `/PHASE` and `.SESSION` shorthands still work. A title
  you type yourself always wins and makes no network call.
  On failure (no route, auth error, not found, offline) it prints the reason
  and exits without starting a session. It never invents a title.
- `csm tasks [TEXT] [--from NAME]`: list or search tasks for this folder. Good
  for checking a connection and for scripts.
- `csm connections`: shows each connection, its adapter, the folders routed to
  it, and a live auth check (`OK` / `401` / `unreachable`).

### Cache

`~/.claude/csm-cache/<connection>.json` holds the task records from recent
`get`/`search`/`recent` calls, with a timestamp. Picker and shell completion
read it instantly; a background refresh (the picker already runs a refresh
thread) updates it. Default TTL 10 min, configurable. It never stores tokens.

## Phase 2: task search in the picker

- **Ctrl+T** in the picker, or `csm new` with no arguments, opens the "New
  session from task" view. Ctrl+N is not available: it is already Down.
- Layout: a search line at the top; a task list (`KEY  status  title`) on the
  left; on the right or bottom a detail pane with the title, status, assignee,
  URL and the first N lines of the description.
- It opens with the cached `recent()` tasks, so the list is never empty.
  Typing filters the cache instantly, then a debounced (~300 ms) live `search()`
  merges in more results on the background thread.
- **Enter** starts `KEY/1.001: Title`. **Tab** lets you edit the title (or set
  the phase) before starting. **Esc** goes back. If a task already has
  sessions, the view shows that and offers the next session number instead of
  `.001`.

## Phase 3: shell completion

- `csm completion zsh|bash` prints a completion script; you add one `source`
  line to your rc file.
- `csm new <TAB>` completes keys with titles as descriptions (zsh shows them),
  read from the cache through a hidden `csm _complete new <prefix>` that never
  touches the network, so TAB stays instant.

## Decisions (Peter, 2026-10-07)

- **Adapters are separate files in `adapters/`.** `CONTRIBUTING.md` is updated:
  core = one file, trackers = one file each, stdlib only, no core edits.
- **Credentials live in `.env`** in the repo root (gitignored), with a
  committed `.env.example`. Connections name the variable with `token_env`.
  This replaces the `env:`/`cmd:`/`file:` secret references sketched below.
- **Titles are never shortened.** The session title uses the full ticket title.
- Settlemate's Linear team key is `SET`. For `recent()`, all open team tasks is
  fine.

## Testing

- A fake `http` plus recorded JSON fixtures per adapter. No network in CI.
- A shared contract test that runs against every adapter in `adapters/`:
  `get` returns the `Task` shape or `None`, optional methods are either
  missing or return lists, and errors map to the core's error type.
- Routing table tests (prefix vs path vs `--from`), secret resolver tests, and
  `new` title-building tests for the default and custom naming.
- A manual check with real tokens via `csm connections` and `csm tasks`.

## Open questions

All answered; see Decisions. The YouTrack URLs and project codes are filled in
from Peter's logged-in accounts.
