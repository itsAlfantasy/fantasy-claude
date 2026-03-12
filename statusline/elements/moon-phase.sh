#!/bin/bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 - "$REPO_DIR/config.json" << 'PYEOF'
import json, sys
from datetime import date

show_name = False
try:
    with open(sys.argv[1]) as f:
        show_name = json.load(f).get('statusline', {}).get('element_settings', {}).get('moon-phase', {}).get('show_name', False)
except Exception:
    pass

d = date.today()
known_new = date(2000, 1, 6)
delta = (d - known_new).days
phase = (delta % 29.53058867) / 29.53058867
phases = [
    ('🌑', 'New Moon'),
    ('🌒', 'Waxing Crescent'),
    ('🌓', 'First Quarter'),
    ('🌔', 'Waxing Gibbous'),
    ('🌕', 'Full Moon'),
    ('🌖', 'Waning Gibbous'),
    ('🌗', 'Last Quarter'),
    ('🌘', 'Waning Crescent'),
]
idx = round(phase * 8) % 8
emoji, name = phases[idx]
print(f"{emoji} {name}" if show_name else emoji)
PYEOF
