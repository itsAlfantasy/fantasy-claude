#!/bin/bash
# Estimated session cost — prefers CLAUDE_COST_USD env var set by statusline.sh from stdin JSON
# Fallback uses token counts from JSONL with Sonnet 4.6 pricing: $3/MTok in, $15/MTok out, $3.75/MTok cache-write, $0.30/MTok cache-read
source "$(dirname "${BASH_SOURCE[0]}")/../../lib/python.sh"
$PYTHON_BIN - << 'PYEOF'
import glob, json, os, sys

cost_env = os.environ.get('CLAUDE_COST_USD', '').strip()
if cost_env != '':
    cost = float(cost_env)
    print(f"~${cost:.4f}" if cost < 0.01 else f"~${cost:.2f}")
    sys.exit()

# Fallback: parse JSONL (for dev/testing outside Claude Code)
CLAUDE_DIR = os.path.expanduser("~/.claude/projects")
files = glob.glob(f"{CLAUDE_DIR}/**/*.jsonl", recursive=True)
if not files:
    print("--")
    sys.exit()

latest = max(files, key=os.path.getmtime)

PRICE = {
    "input":        3.00 / 1_000_000,
    "output":      15.00 / 1_000_000,
    "cache_write":  3.75 / 1_000_000,
    "cache_read":   0.30 / 1_000_000,
}

totals = {k: 0 for k in PRICE}
with open(latest, errors="replace") as f:
    for line in f:
        try:
            d = json.loads(line)
            if d.get("type") == "assistant":
                u = d.get("message", {}).get("usage", {})
                totals["input"]       += u.get("input_tokens", 0)
                totals["output"]      += u.get("output_tokens", 0)
                totals["cache_write"] += u.get("cache_creation_input_tokens", 0)
                totals["cache_read"]  += u.get("cache_read_input_tokens", 0)
        except Exception:
            pass

cost = sum(totals[k] * PRICE[k] for k in PRICE)
if cost < 0.01:
    print(f"~${cost:.4f}")
else:
    print(f"~${cost:.2f}")
PYEOF
