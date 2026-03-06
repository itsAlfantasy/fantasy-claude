#!/bin/bash
# Hook script for sound events — reads config.json and plays the configured sound

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_DIR/config.json"

input=$(cat)

# Determine event type and whether it's an error
hook_event=$(echo "$input" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    event = d.get('hook_event_name', '')
    is_error = d.get('tool_response', {}).get('is_error', False)
    if event == 'PostToolUse' and is_error:
        print('on_error')
    elif event == 'Stop':
        print('on_stop')
    elif event == 'Notification':
        print('on_notification')
except:
    pass
" 2>/dev/null)

[ -z "$hook_event" ] && exit 0

sound_name=$(python3 -c "
import json
with open('$CONFIG') as f:
    d = json.load(f)
name = d.get('sounds', {}).get('$hook_event')
if name:
    print(name)
" 2>/dev/null)

[ -z "$sound_name" ] || [ "$sound_name" = "None" ] && exit 0

# Map event to sounds subdirectory
case "$hook_event" in
  on_error)       sound_dir="$REPO_DIR/sounds/error" ;;
  on_stop)        sound_dir="$REPO_DIR/sounds/notification" ;;
  on_notification) sound_dir="$REPO_DIR/sounds/notification" ;;
  *) exit 0 ;;
esac

sound_file="$sound_dir/$sound_name.mp3"
[ ! -f "$sound_file" ] && exit 0

if [[ "$OSTYPE" == "darwin"* ]]; then
    afplay "$sound_file" &
else
    command -v paplay &>/dev/null && paplay "$sound_file" & || \
    command -v aplay  &>/dev/null && aplay  "$sound_file" &
fi
