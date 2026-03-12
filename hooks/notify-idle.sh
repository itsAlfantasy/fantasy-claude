#!/bin/bash
# Notification hook for idle_prompt events
input=$(cat)

if [[ "$OSTYPE" == "darwin"* ]]; then
    printf '\e]9;\n\n💤 Ready for your input\a' > /dev/tty 2>/dev/null
else
    notify-send "Claude Code" "💤 Ready for your input" 2>/dev/null
fi
