#!/bin/bash
# Context window usage % — prefers CLAUDE_CONTEXT_PCT env var set by statusline.sh from stdin JSON
source "$(dirname "${BASH_SOURCE[0]}")/../../lib/python.sh"
$PYTHON_BIN - << 'PYEOF'
import glob, json, os, sys

pct_env = os.environ.get('CLAUDE_CONTEXT_PCT', '').strip()
if pct_env != '':
    print(f"{pct_env}%")
    sys.exit()

# Fallback: parse JSONL (for dev/testing outside Claude Code)
CLAUDE_DIR = os.path.expanduser("~/.claude/projects")

size_env = os.environ.get('CLAUDE_CONTEXT_SIZE', '').strip()
CONTEXT_WINDOW = int(size_env) if size_env else 200_000

files = glob.glob(f"{CLAUDE_DIR}/**/*.jsonl", recursive=True)
if not files:
    print("0%")
    sys.exit()

latest = max(files, key=os.path.getmtime)

last_usage = None
with open(latest, errors="replace") as f:
    for line in f:
        try:
            d = json.loads(line)
            if d.get("type") == "assistant":
                u = d.get("message", {}).get("usage")
                if u:
                    last_usage = u
        except Exception:
            pass

if not last_usage:
    print("0%")
    sys.exit()

total = (
    last_usage.get("input_tokens", 0)
    + last_usage.get("cache_creation_input_tokens", 0)
    + last_usage.get("cache_read_input_tokens", 0)
)
pct = round(total / CONTEXT_WINDOW * 100)
print(f"{pct}%")
PYEOF
