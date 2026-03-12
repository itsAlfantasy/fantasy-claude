#!/bin/bash
# Notification hook for auth_success events
input=$(cat)
msg=$(echo "$input" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('message', 'Authentication succeeded'))
except:
    print('Authentication succeeded')
" 2>/dev/null)
[ -z "$msg" ] && msg="Authentication succeeded"

if [[ "$OSTYPE" == "darwin"* ]]; then
    printf '\e]9;\n\n✅ %s\a' "$msg" > /dev/tty 2>/dev/null
else
    notify-send "Claude Code" "✅ $msg" 2>/dev/null
fi
