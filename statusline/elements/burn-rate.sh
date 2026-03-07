#!/bin/bash
# Token burn rate, read from cache written by statusline-command.sh
CACHE="/tmp/claude_burn_cache_$(id -u)"
[ -f "$CACHE" ] || { echo "--"; exit 0; }
rate=$(cat "$CACHE")
[ -n "$rate" ] && echo "${rate}" || echo "--"
