#!/usr/bin/env bash
# Install csm — adds the `csm` alias to your shell and (optionally) the /hop
# skill. Re-runnable / idempotent. No root, no pip, nothing system-wide.
#
#   ./install.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$REPO/cc-sessions"

[ -f "$SCRIPT" ] || { echo "error: cc-sessions not found next to install.sh" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || {
  echo "error: python3 is required — it's the only dependency" >&2; exit 1; }
chmod +x "$SCRIPT"

# Pick the right shell rc file.
case "${SHELL:-}" in
  *zsh)  RC="${ZDOTDIR:-$HOME}/.zshrc" ;;
  *bash) RC="$HOME/.bashrc" ;;
  *)     RC="$HOME/.profile" ;;
esac

# 1) alias
ALIAS="alias csm='python3 \"$SCRIPT\"'"
if grep -qsE '^[[:space:]]*alias csm=' "$RC" 2>/dev/null; then
  echo "• csm alias already in $RC — leaving it"
else
  printf '\n# Claude Session Manager (csm)\n%s\n' "$ALIAS" >> "$RC"
  echo "• added csm alias to $RC"
fi

# 2) /hop skill (optional, additive — skipped if it already exists)
SKILL_SRC="$REPO/skills/hop"
SKILL_DST="$HOME/.claude/skills/hop"
if [ -d "$SKILL_SRC" ] && [ ! -e "$SKILL_DST" ]; then
  mkdir -p "$HOME/.claude/skills"
  cp -R "$SKILL_SRC" "$SKILL_DST"
  # point the skill at this checkout (it hard-codes the script path)
  if [ -f "$SKILL_DST/SKILL.md" ]; then
    sed -i.bak -E "s#[^ ]*/cc-sessions hop#$SCRIPT hop#g" "$SKILL_DST/SKILL.md"
    rm -f "$SKILL_DST/SKILL.md.bak"
  fi
  echo "• installed /hop skill → $SKILL_DST"
elif [ -e "$SKILL_DST" ]; then
  echo "• /hop skill already present — leaving it"
fi

echo
echo "Done. Start a new terminal (or: source $RC), then run:  csm"
echo "Hooks, clipboard copy, and naming config are optional — see INSTALLATION.md"
