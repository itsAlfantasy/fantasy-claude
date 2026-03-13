#!/bin/bash
# Duration of the current Claude Code session from its JSONL
source "$(dirname "${BASH_SOURCE[0]}")/../../lib/python.sh"
$PYTHON_BIN - << 'PYEOF'
import glob, json, os, sys
from datetime import datetime, timezone

CLAUDE_DIR = os.path.expanduser("~/.claude/projects")
files = glob.glob(f"{CLAUDE_DIR}/**/*.jsonl", recursive=True)
if not files:
    print("--")
    sys.exit()

latest = max(files, key=os.path.getmtime)

first_ts = None
with open(latest, errors="replace") as f:
    for line in f:
        try:
            d = json.loads(line)
            ts = d.get("timestamp")
            if ts and d.get("type") in ("user", "assistant"):
                first_ts = ts
                break
        except Exception:
            pass

if not first_ts:
    print("--")
    sys.exit()

try:
    start = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = int((now - start).total_seconds())
    h, rem = divmod(delta, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        print(f"{h}h{m:02d}m")
    else:
        print(f"{m}m{s:02d}s")
except Exception:
    print("--")
PYEOF
