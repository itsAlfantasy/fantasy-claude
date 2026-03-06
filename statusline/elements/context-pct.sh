#!/bin/bash
# Context window usage % from the most recent Claude Code session JSONL
python3 - << 'PYEOF'
import glob, json, os, sys

CLAUDE_DIR = os.path.expanduser("~/.claude/projects")
CONTEXT_WINDOW = 200_000  # all current Claude models

# Find the most recently modified JSONL
files = glob.glob(f"{CLAUDE_DIR}/**/*.jsonl", recursive=True)
if not files:
    print("ctx:--%")
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
    print("ctx:--%")
    sys.exit()

total = (
    last_usage.get("input_tokens", 0)
    + last_usage.get("cache_creation_input_tokens", 0)
    + last_usage.get("cache_read_input_tokens", 0)
)
pct = round(total / CONTEXT_WINDOW * 100)
print(f"ctx:{pct}%")
PYEOF
