#!/bin/bash
set -euo pipefail

copy_skill_tree() {
  local target="$1"
  mkdir -p "$target"
  for item in /opt/template-skills/*; do
    [ -e "$item" ] || continue
    cp -R "$item" "$target"/
  done
}

mkdir -p \
  /app/.codex/skills \
  /app/.claude/skills \
  /app/.agents/skills \
  /app/.gemini/skills \
  /logs/agent/skills

copy_skill_tree /app/.codex/skills
copy_skill_tree /app/.claude/skills
copy_skill_tree /app/.agents/skills
copy_skill_tree /app/.gemini/skills
copy_skill_tree /logs/agent/skills

exec "$@"
