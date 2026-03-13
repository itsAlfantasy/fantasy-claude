#!/bin/bash
# Hook script for notifications when Claude Code needs user input.
# Uses iTerm2 OSC 9 escape sequence on macOS, notify-send on Linux.
source "$(dirname "${BASH_SOURCE[0]}")/../lib/python.sh"

input=$(cat)

# Build notification message with emoji prefix based on type
message=$(echo "$input" | $PYTHON_BIN -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ntype = d.get('notification_type', '')
    msg = d.get('message', '')

    if ntype == 'permission_prompt':
        print(f'🔐 {msg or \"Claude needs your permission\"}')
    elif ntype == 'idle_prompt':
        print('💤 Ready for your input')
    elif ntype == 'elicitation_dialog':
        print(f'❓ {msg or \"Claude has a question\"}')
    elif ntype == 'auth_success':
        print(f'✅ {msg or \"Authentication succeeded\"}')
    else:
        print(msg or 'Needs your attention')
except:
    print('Needs your attention')
" 2>/dev/null)

[ -z "$message" ] && message="Needs your attention"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # iTerm2 OSC 9: write to /dev/tty to bypass stdout capture
    printf '\e]9;\n\n%s\a' "$message" > /dev/tty 2>/dev/null
else
    if command -v notify-send &>/dev/null; then
        notify-send "Claude Code" "$message" 2>/dev/null
    fi
fi
