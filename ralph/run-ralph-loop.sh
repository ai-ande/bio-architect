#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./run_ralph_loop.sh [max_iterations]

set -e

MAX_ITERATIONS=${1:-30}
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")/ralph"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
APP="claude"

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")
  
  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    # Archive the previous run
    DATE=$(date +%Y-%m-%d)
    # Strip "ralph/" prefix from branch name for folder
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    
    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    echo "   Archived to: $ARCHIVE_FOLDER"
    
    # Reset progress file for new run
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ]; then
    echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
  fi
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo "Starting Ralph - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo "  Ralph Iteration $i of $MAX_ITERATIONS"
  echo "═══════════════════════════════════════════════════════"
  
  # Run ai app with the ralph prompt
  # FIX: Uses stream-json + completion detection (from claude-code#19060)
  PROMPT="$(<"$PROMPT_FILE")"
  TEMP_OUTPUT=$(mktemp)
  FIFO=$(mktemp -u)
  mkfifo "$FIFO"

  # Run with stream-json to detect completion reliably
  $APP --dangerously-skip-permissions -p "$PROMPT" --output-format stream-json --verbose > "$FIFO" 2>&1 &
  CLAUDE_PID=$!

  RESULT_RECEIVED=false
  while IFS= read -r line; do
    echo "$line" >> "$TEMP_OUTPUT"
    # Show non-json lines (the actual output)
    [[ "$line" != "{"* ]] && echo "$line"

    if [[ "$line" == *'"type":"result"'* ]]; then
      RESULT_RECEIVED=true
      ( sleep 2; kill $CLAUDE_PID 2>/dev/null ) &
      KILLER_PID=$!
      break
    fi
  done < "$FIFO"

  wait $CLAUDE_PID 2>/dev/null || true
  [ -n "$KILLER_PID" ] && { kill $KILLER_PID 2>/dev/null; wait $KILLER_PID 2>/dev/null; }

  # Extract and show the result text from JSON
  RESULT_TEXT=$(grep '"type":"result"' "$TEMP_OUTPUT" | jq -r '.result // empty' 2>/dev/null | head -1)
  [ -n "$RESULT_TEXT" ] && echo "$RESULT_TEXT"

  OUTPUT=$(cat "$TEMP_OUTPUT")
  rm -f "$TEMP_OUTPUT" "$FIFO"

  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi
  
  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1
