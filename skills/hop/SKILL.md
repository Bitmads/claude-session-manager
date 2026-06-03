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
   CSM=$(command -v cc-sessions 2>/dev/null || echo "$HOME/.local/bin/cc-sessions"); CMD=$(python3 "$CSM" hop --dry-run) && echo -n "$CMD" | xclip -selection clipboard 2>/dev/null; echo "📋 $CMD"
   ```

2. Print the output exactly as returned. No explanation, no commentary.
