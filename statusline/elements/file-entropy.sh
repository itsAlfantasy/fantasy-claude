#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../../lib/python.sh"
$PYTHON_BIN - << 'PYEOF'
import glob, os, json
claude_dir = os.path.expanduser('~/.claude/projects')
files = glob.glob(f'{claude_dir}/**/*.jsonl', recursive=True)
if not files:
    print("0")
    exit()
latest = max(files, key=os.path.getmtime)
touched = set()
try:
    with open(latest, errors='replace') as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get('type') == 'assistant':
                    content = d.get('message', {}).get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                if block.get('name') in ('Edit', 'Write', 'Read', 'NotebookEdit'):
                                    inp = block.get('input', {})
                                    path = inp.get('file_path') or inp.get('path')
                                    if path:
                                        touched.add(path)
            except Exception:
                pass
except Exception:
    pass
print(len(touched))
PYEOF
