#!/bin/bash
set -euo pipefail
# claim-task.sh — Atomically claim a task from the queue
# Usage: claim-task.sh <TASK-NNN> <agent-name>
#
# HARDENED: checks done/, review/, active/ before claiming to prevent
# ghost re-claims caused by git restoring old queue files from branches.

TASK="${1:?Usage: claim-task.sh <TASK-NNN> <agent-name>}"
AGENT="${2:?Usage: claim-task.sh <TASK-NNN> <agent-name>}"
COLONY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

QUEUE_FILE="$COLONY_ROOT/queue/${TASK}.md"
ACTIVE_FILE="$COLONY_ROOT/active/${TASK}.md"
REVIEW_FILE="$COLONY_ROOT/review/${TASK}.md"
DONE_FILE="$COLONY_ROOT/done/${TASK}.md"

# Check if task is already completed (ghost file in queue from old git branch)
if [[ -f "$DONE_FILE" ]]; then
  echo "SKIP: Task $TASK is already done — queue file is a ghost from git history" >&2
  # Remove the ghost queue file
  rm -f "$QUEUE_FILE" 2>/dev/null
  exit 1
fi

# Check if task is already in review
if [[ -f "$REVIEW_FILE" ]]; then
  echo "SKIP: Task $TASK is already in review" >&2
  rm -f "$QUEUE_FILE" 2>/dev/null
  exit 1
fi

# Check if task is already active
if [[ -f "$ACTIVE_FILE" ]]; then
  echo "ERROR: Task $TASK is already active" >&2
  rm -f "$QUEUE_FILE" 2>/dev/null
  exit 1
fi

if [[ ! -f "$QUEUE_FILE" ]]; then
  echo "ERROR: Task $TASK not found in queue/" >&2
  exit 1
fi

# Move atomically
mv "$QUEUE_FILE" "$ACTIVE_FILE"

# Append claim metadata
echo "" >> "$ACTIVE_FILE"
echo "---" >> "$ACTIVE_FILE"
echo "Claimed-By: $AGENT" >> "$ACTIVE_FILE"
echo "Claimed-At: $(date -Iseconds)" >> "$ACTIVE_FILE"

echo "Task $TASK claimed by $AGENT"
