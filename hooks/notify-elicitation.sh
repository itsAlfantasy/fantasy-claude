#!/bin/bash
# Notification hook for elicitation_dialog events
source "$(dirname "${BASH_SOURCE[0]}")/../lib/python.sh"
input=$(cat)
msg=$(echo "$input" | $PYTHON_BIN -c "
import sys, json
try:
    print(json.load(sys.stdin).get('message', 'Claude has a question'))
except:
    print('Claude has a question')
" 2>/dev/null)
[ -z "$msg" ] && msg="Claude has a question"

if [[ "$OSTYPE" == "darwin"* ]]; then
    printf '\e]9;\n\n❓ %s\a' "$msg" > /dev/tty 2>/dev/null
else
    notify-send "Claude Code" "❓ $msg" 2>/dev/null
fi
