#!/bin/bash
set -euo pipefail
# complete-task.sh — Move a task from active to review
# Usage: complete-task.sh <TASK-NNN>

TASK="${1:?Usage: complete-task.sh <TASK-NNN>}"
COLONY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ACTIVE_FILE="$COLONY_ROOT/active/${TASK}.md"
REVIEW_FILE="$COLONY_ROOT/review/${TASK}.md"

if [[ ! -f "$ACTIVE_FILE" ]]; then
  echo "ERROR: Task $TASK not found in active/" >&2
  exit 1
fi

# Don't overwrite existing review file
if [[ -f "$REVIEW_FILE" ]]; then
  echo "WARN: Task $TASK already has a review file — removing active copy" >&2
  rm -f "$ACTIVE_FILE"
  exit 0
fi

# Append completion metadata
echo "" >> "$ACTIVE_FILE"
echo "Completed-At: $(date -Iseconds)" >> "$ACTIVE_FILE"

# Push the branch
BRANCH="task/${TASK}"
if git rev-parse --verify "$BRANCH" &>/dev/null; then
  git push origin "$BRANCH" 2>/dev/null || echo "WARN: Could not push branch $BRANCH"
fi

# Move to review
mv "$ACTIVE_FILE" "$REVIEW_FILE"

echo "Task $TASK moved to review/"
