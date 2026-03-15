#!/bin/bash
# Token burn rate — reads from cache written by hooks/burn-rate-update.sh
CACHE="/tmp/claude_burn_cache_$(id -u)"

[ -f "$CACHE" ] || { echo "--"; exit 0; }

mtime=$(stat -f %m "$CACHE" 2>/dev/null || stat -c %Y "$CACHE" 2>/dev/null)
age=$(( $(date +%s) - ${mtime:-0} ))
[ "$age" -gt 120 ] && { echo "--"; exit 0; }

awk '{
  r = $1 + 0
  if (r >= 1000) printf "%.1fk/m\n", r/1000
  else printf "%d/m\n", r
}' "$CACHE"
