---
name: hop
description: Update docs, write a detailed handoff, then print the command that starts the continuation session
---

# Hop — Session Continuation

When the user invokes /hop, do these three steps in order.

Anything the user typed after `/hop` is a message for the NEXT session, not an
instruction for this one. Don't act on it here; pass it through unchanged in
step 3. It can be empty.

## 1. Bring the docs up to date

Make every README, plan file, docs page, and code comment touched by or
relevant to this session's work reflect what is true now, so the next session
can rely on them without the transcript.

- Cover the whole session, not just the last task: features added, behavior
  changed, decisions made, approaches rejected (and why), new commands, config,
  paths, and known issues.
- Fix anything this session made stale: outdated instructions, finished TODOs,
  plans whose status changed, comments describing old behavior.
- Update the project's memory files if it uses them.
- Read each file before editing it. Edit only what is wrong or missing; don't
  rewrite sections that are still accurate.
- Don't commit or push unless the user asked for that earlier in this session.

## 2. Write the handoff document

Write one Markdown file the next session will read first. It must stand on its
own: assume the reader has no memory of this session and has not read the
transcript.

Location: if the work lives in a repo, put it in that repo's docs folder
(follow an existing `HANDOFF-*` convention if there is one, otherwise
`docs/HANDOFF-YYYY-MM-DD-<topic>.md`). Otherwise use
`~/.claude/handoffs/YYYY-MM-DD-<topic>.md`. Use absolute paths everywhere in
the document.

Base every claim on something you checked in this session (a file you read,
command output, git log). Run `git status` / `git log` in the repos involved
so the state section is current. Mark anything unverified as unverified.

Sections, in this order (write "none" rather than dropping a section):

1. **Goal**: what the user is trying to achieve overall, and the scope of the
   current phase.
2. **Current state**: what is done and how it was verified; what is in
   progress and exactly where it stopped (file, function, step).
3. **Next steps**: ordered and concrete, each with the file or command it
   involves. Mark which ones need the user's input or approval.
4. **Required reading**: the files the next session must read before acting,
   with one line on why each matters.
5. **Key files and locations**: absolute paths of code, config, data, and
   output touched this session.
6. **Commands**: exact build / test / run / deploy commands that worked, with
   any environment they need.
7. **Decisions and rationale**: what was chosen, what was rejected, and why.
8. **User preferences and feedback**: instructions and corrections the user
   gave this session, in their words where it matters.
9. **Gotchas and open issues**: bugs, anomalies, traps, flaky steps, and
   anything that failed and how.
10. **Live state**: uncommitted changes, branches, running processes or
    services, deployed versions, and temp files in use.

## 3. Hop

Run this, with the absolute path of the handoff from step 2:

```bash
python3 /media/nvme4tb/DEV/claude-session-manager/cc-sessions hop --dry-run --handoff "<handoff path>" --message '<text after /hop>'
```

`--message` carries the user's text after `/hop` verbatim: same words, no
rewording, no additions. Wrap it in single quotes and write each `'` inside it
as `'\''`. If the user typed nothing after `/hop`, leave `--message` out.

Your final message must be exactly the command line it prints on stdout, as
plain text: no code fence, no heading, no summary, nothing before or after it.
Leave out any stderr lines such as `# copied to clipboard`. If the command
fails, show the error instead.

Clipboard copy is handled by the tool itself (configure `copy.command` in
~/.claude/csm.json or set $CSM_COPY_CMD).
