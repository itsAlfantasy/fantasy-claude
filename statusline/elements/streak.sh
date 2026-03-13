#!/bin/bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/lib/python.sh"
$PYTHON_BIN - "$REPO_DIR/config.json" << 'PYEOF'
import glob, os, json, sys
from datetime import date, timedelta

show_unit = True
try:
    with open(sys.argv[1]) as f:
        show_unit = json.load(f).get('statusline', {}).get('element_settings', {}).get('streak', {}).get('show_unit', True)
except Exception:
    pass

claude_dir = os.path.expanduser('~/.claude/projects')
files = glob.glob(f'{claude_dir}/**/*.jsonl', recursive=True)
days = set()
for f in files:
    try:
        with open(f, errors='replace') as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    ts = d.get('timestamp')
                    if ts:
                        days.add(ts[:10])
                except Exception:
                    pass
    except Exception:
        pass

if not days:
    print("0 days" if show_unit else "0d")
    exit()

today = date.today()
streak = 0
current = today
while current.isoformat() in days:
    streak += 1
    current -= timedelta(days=1)
if streak == 0:
    current = today - timedelta(days=1)
    while current.isoformat() in days:
        streak += 1
        current -= timedelta(days=1)
print(f"{streak} days" if show_unit else f"{streak}d")
PYEOF
