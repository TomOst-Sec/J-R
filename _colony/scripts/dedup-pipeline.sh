#!/bin/bash
set -euo pipefail
# dedup-pipeline.sh — Remove ghost duplicates from pipeline
# Ghost files appear when git restores old tracked _colony/ files from branches.
# Run this to clean them up. Safe to run multiple times.

COLONY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXED=0

for f in "$COLONY_ROOT"/queue/TASK-*.md; do
  [ -f "$f" ] || continue
  TASK=$(basename "$f" .md)

  # If task is already done, review, or active — remove the queue ghost
  if [ -f "$COLONY_ROOT/done/$TASK.md" ] || [ -f "$COLONY_ROOT/review/$TASK.md" ] || [ -f "$COLONY_ROOT/active/$TASK.md" ]; then
    rm "$f"
    echo "Removed ghost queue/$TASK.md"
    FIXED=$((FIXED + 1))
  fi
done

for f in "$COLONY_ROOT"/active/TASK-*.md; do
  [ -f "$f" ] || continue
  TASK=$(basename "$f" .md)

  # If task is already done or in review — remove active ghost
  if [ -f "$COLONY_ROOT/done/$TASK.md" ] || [ -f "$COLONY_ROOT/review/$TASK.md" ]; then
    rm "$f"
    echo "Removed ghost active/$TASK.md"
    FIXED=$((FIXED + 1))
  fi
done

for f in "$COLONY_ROOT"/review/TASK-*.md; do
  [ -f "$f" ] || continue
  TASK=$(basename "$f" .md)

  # If task is already done — remove review ghost
  if [ -f "$COLONY_ROOT/done/$TASK.md" ]; then
    rm "$f"
    echo "Removed ghost review/$TASK.md"
    FIXED=$((FIXED + 1))
  fi
done

echo "Dedup complete: $FIXED ghosts removed"
