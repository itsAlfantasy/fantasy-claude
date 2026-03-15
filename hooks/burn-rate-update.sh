#!/bin/bash
# Calcola token burn rate e scrive in cache — chiamato da PostToolUse e Stop
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/lib/python.sh"

CACHE="/tmp/claude_burn_cache_$(id -u)"
input=$(cat)

echo "$input" | $PYTHON_BIN -c "
import json, os, sys
from datetime import datetime, timezone, timedelta

cache_path = '$CACHE'

try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path')
if not transcript_path or not os.path.isfile(transcript_path):
    sys.exit(0)

cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
total_tokens = 0

try:
    with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') != 'assistant':
                continue
            ts_str = entry.get('timestamp')
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except Exception:
                continue
            if ts < cutoff:
                continue
            usage = entry.get('message', {}).get('usage', {})
            total_tokens += usage.get('output_tokens', 0)
except Exception:
    sys.exit(0)

rate = round(total_tokens / 2)

try:
    with open(cache_path, 'w') as f:
        f.write(str(rate))
except Exception:
    pass
" 2>/dev/null
