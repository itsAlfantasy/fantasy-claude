#!/bin/bash
# Current Claude model — prefers CLAUDE_MODEL env var set by statusline.sh from stdin JSON
source "$(dirname "${BASH_SOURCE[0]}")/../../lib/python.sh"
$PYTHON_BIN - << 'PYEOF'
import glob, json, os, re, sys

model = os.environ.get('CLAUDE_MODEL', '').strip()
if model:
    name = model.replace("claude-", "")
    name = re.sub(r"-\d{8}$", "", name)
    print(name)
    sys.exit()

# Fallback: parse JSONL (for dev/testing outside Claude Code)
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
