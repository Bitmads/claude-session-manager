---
name: hop
description: Bump session version and print the command to start a continuation session
allowedTools:
  - Bash
---

# Hop — Session Continuation

When the user invokes /hop:

1. Run this bash command:
   ```bash
   python3 /media/nvme4tb/DEV/claude-session-manager/cc-sessions hop --dry-run
   ```

2. Print the output exactly as returned. No explanation, no commentary.

Clipboard copy is handled by the tool itself (configure `copy.command` in
~/.claude/csm.json or set $CSM_COPY_CMD). No piping needed here.
