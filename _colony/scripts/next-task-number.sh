#!/bin/bash
set -euo pipefail
# next-task-number.sh — Returns the next available task number
COLONY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

MAX=0
for d in queue active review done bugs; do
  for f in "$COLONY_ROOT/$d"/TASK-*.md 2>/dev/null; do
    [ -f "$f" ] || continue
    NUM=$(basename "$f" .md | grep -oE '[0-9]+' | sed 's/^0*//')
    [ "${NUM:-0}" -gt "$MAX" ] && MAX="$NUM"
  done
done

NEXT=$((MAX + 1))
printf "TASK-%03d\n" "$NEXT"
