#!/bin/bash
# 5-hour rate limit utilization, read from cache written by statusline-command.sh
CACHE="/tmp/claude_usage_cache_$(id -u)"
[ -f "$CACHE" ] || { echo "5h:--"; exit 0; }
read -r pct _ < "$CACHE"
[ -n "$pct" ] && echo "5h:${pct%.*}%" || echo "5h:--"
