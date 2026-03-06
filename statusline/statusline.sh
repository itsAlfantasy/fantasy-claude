#!/bin/bash
# Main statusline script — reads config.json and composes the status line

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_DIR/config.json"
ELEMENTS_DIR="$REPO_DIR/statusline/elements"

# Read new "lines" format; fall back to flat "elements" for old configs
# Each output line from python is pipe-separated elements for one statusline line
while IFS= read -r raw_line; do
    parts=()
    old_ifs="$IFS"
    IFS='|'
    for element in $raw_line; do
        IFS="$old_ifs"
        script="$ELEMENTS_DIR/$element.sh"
        if [ -x "$script" ]; then
            out=$("$script" 2>/dev/null)
            [ -n "$out" ] && parts+=("$out")
        fi
        IFS='|'
    done
    IFS="$old_ifs"
    if [ ${#parts[@]} -gt 0 ]; then
        IFS=' | '
        echo "${parts[*]}"
        IFS="$old_ifs"
    fi
done < <(python3 -c "
import json, sys
with open('$CONFIG') as f:
    d = json.load(f)
sl = d.get('statusline', {})
lines = sl.get('lines')
if lines is None:
    elems = sl.get('elements', [])
    lines = [elems] if elems else []
for line in lines:
    print('|'.join(line))
" 2>/dev/null)
