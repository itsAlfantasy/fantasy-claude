#!/bin/bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPO_DIR/lib/python.sh"
$PYTHON_BIN - "$REPO_DIR/config.json" << 'PYEOF'
import json, sys
from datetime import datetime

mood_set = 1
try:
    with open(sys.argv[1]) as f:
        mood_set = json.load(f).get('statusline', {}).get('element_settings', {}).get('mood', {}).get('mood_set', 1)
except Exception:
    pass

SETS = {
    1: [(5, "😴"), (8, "☕"), (12, "🍕"), (14, "💻"), (18, "🌆"), (22, "🌙")],
    2: [(5, "🥱"), (8, "⚡"), (12, "🎯"), (14, "🔥"), (18, "🍺"), (22, "🌃")],
    3: [(5, "💤"), (8, "🌅"), (12, "☀️"), (14, "🌤️"), (18, "🌇"), (22, "🌌")],
}
hour = datetime.now().hour
emojis = SETS.get(mood_set, SETS[1])
result = emojis[-1][1]
for threshold, emoji in emojis:
    if hour < threshold:
        break
    result = emoji
print(result)
PYEOF
