#!/bin/bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 - "$REPO_DIR/config.json" << 'PYEOF'
import os, json, sys

basename_only = False
try:
    with open(sys.argv[1]) as f:
        basename_only = json.load(f).get('statusline', {}).get('element_settings', {}).get('cwd', {}).get('basename_only', False)
except Exception:
    pass

path = os.getcwd()
home = os.path.expanduser('~')
if basename_only:
    print(os.path.basename(path))
else:
    if path.startswith(home):
        path = '~' + path[len(home):]
    print(path)
PYEOF
