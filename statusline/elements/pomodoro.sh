#!/bin/bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POMO_FILE="/tmp/pomodoro_$(id -u)"

_get_duration() {
    python3 - "$REPO_DIR/config.json" << 'PYEOF'
import json, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f).get('statusline', {}).get('element_settings', {}).get('pomodoro', {}).get('duration', 25)
    print(int(d) * 60)
except Exception:
    print(1500)
PYEOF
}

if [ ! -f "$POMO_FILE" ]; then
    dur_secs=$(_get_duration)
    printf '%d:00\n' "$(( dur_secs / 60 ))"
    exit 0
fi

IFS='|' read -r start_ts duration state < "$POMO_FILE"
now=$(date +%s)
elapsed=$(( now - start_ts ))
remaining=$(( duration - elapsed ))

if [ "$state" = "running" ]; then
    if [ "$remaining" -le 0 ]; then
        echo "done!"
    else
        printf '%d:%02d\n' "$(( remaining / 60 ))" "$(( remaining % 60 ))"
    fi
elif [ "$state" = "paused" ]; then
    printf '⏸%d:%02d\n' "$(( remaining / 60 ))" "$(( remaining % 60 ))"
else
    dur_secs=$(_get_duration)
    printf '%d:00\n' "$(( dur_secs / 60 ))"
fi
