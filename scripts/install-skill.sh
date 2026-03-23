#!/usr/bin/env bash
set -euo pipefail

# install-skill.sh — Install codebase-explorer agent skill for Claude Code
#
# Usage:
#   bash scripts/install-skill.sh
#   bash scripts/install-skill.sh --target ~/.claude/skills

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_DIR/.agents/skills/codebase-explorer"
DEFAULT_TARGET="$HOME/.claude/skills/codebase-explorer"

TARGET="${1:-$DEFAULT_TARGET}"
# Strip --target flag if provided
if [[ "${1:-}" == "--target" ]]; then
  TARGET="${2:-$DEFAULT_TARGET}"
fi

echo "==> Installing codebase-explorer skill"
echo "    Source: $SKILL_SRC"
echo "    Target: $TARGET"

# Validate source exists
if [[ ! -d "$SKILL_SRC" ]]; then
  echo "ERROR: Skill source not found at $SKILL_SRC" >&2
  echo "       Make sure you're running this from the codebase-explorer repo." >&2
  exit 1
fi

if [[ ! -f "$SKILL_SRC/SKILL.md" ]]; then
  echo "ERROR: SKILL.md not found in $SKILL_SRC" >&2
  exit 1
fi

# Create parent directory
mkdir -p "$(dirname "$TARGET")"

# Copy skill files
if [[ -d "$TARGET" ]]; then
  echo "    Existing installation found — overwriting."
fi
cp -r "$SKILL_SRC" "$TARGET"

# Verify
if [[ -f "$TARGET/SKILL.md" ]]; then
  echo "==> Skill installed successfully."
  echo "    Files:"
  find "$TARGET" -type f | sort | while read -r f; do
    echo "      $(basename "$f")"
  done
else
  echo "ERROR: Installation verification failed — SKILL.md not found at $TARGET" >&2
  exit 1
fi
