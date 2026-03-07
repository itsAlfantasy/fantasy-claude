#!/bin/bash
# Current Claude model from the most recent session JSONL
python3 - << 'PYEOF'
import glob, json, os, re, sys

CLAUDE_DIR = os.path.expanduser("~/.claude/projects")
files = glob.glob(f"{CLAUDE_DIR}/**/*.jsonl", recursive=True)
if not files:
    print("--")
    sys.exit()

latest = max(files, key=os.path.getmtime)

model = None
with open(latest, errors="replace") as f:
    for line in f:
        try:
            d = json.loads(line)
            if d.get("type") == "assistant":
                m = d.get("message", {}).get("model")
                if m:
                    model = m
        except Exception:
            pass

if not model:
    print("--")
    sys.exit()

name = model.replace("claude-", "")
name = re.sub(r"-\d{8}$", "", name)
print(name)
PYEOF
