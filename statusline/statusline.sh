#!/bin/bash
# Main statusline script — reads config.json and composes the status line

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_DIR/config.json"
ELEMENTS_DIR="$REPO_DIR/statusline/elements"

elements=$(python3 -c "
import json, sys
with open('$CONFIG') as f:
    d = json.load(f)
for e in d.get('statusline', {}).get('elements', []):
    print(e)
" 2>/dev/null)

parts=()
while IFS= read -r element; do
    script="$ELEMENTS_DIR/$element.sh"
    if [ -x "$script" ]; then
        output=$("$script" 2>/dev/null)
        [ -n "$output" ] && parts+=("$output")
    fi
done <<< "$elements"

IFS=' | '
echo "${parts[*]}"
