#!/bin/bash
# 5-hour window reset time, parsed from cache written by statusline-command.sh
CACHE="/tmp/claude_usage_cache_$(id -u)"
[ -f "$CACHE" ] || { echo "--"; exit 0; }
read -r _ resets_at < "$CACHE"
if [ -z "$resets_at" ] || [ "$resets_at" = "--" ]; then
    echo "--"
    exit 0
fi
# Strip sub-seconds and offset, convert to local time
TS_UTC="${resets_at%%.*}"
TS_UTC="${TS_UTC%+*}"
local_time=$(date -j -u -f "%Y-%m-%dT%H:%M:%S" "$TS_UTC" +"%H:%M" 2>/dev/null \
    || date -d "$resets_at" +"%H:%M" 2>/dev/null)
echo "${local_time:---}"
