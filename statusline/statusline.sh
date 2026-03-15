#!/bin/bash
# Main statusline script — reads config.json and composes the status line

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/lib/python.sh"
CONFIG="$REPO_DIR/config.json"
ELEMENTS_DIR="$REPO_DIR/statusline/elements"

# Read stdin JSON from Claude Code statusline API and export env vars for element scripts
_STDIN=$(cat)
export CLAUDE_MODEL=$(echo "$_STDIN" | $PYTHON_BIN -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('model',{}).get('display_name',''))
" 2>/dev/null)
export CLAUDE_CONTEXT_PCT=$(echo "$_STDIN" | $PYTHON_BIN -c "
import sys,json
d=json.load(sys.stdin)
pct=d.get('context_window',{}).get('used_percentage')
print('' if pct is None else str(round(pct)))
" 2>/dev/null)
export CLAUDE_COST_USD=$(echo "$_STDIN" | $PYTHON_BIN -c "
import sys,json
d=json.load(sys.stdin)
cost=d.get('cost',{}).get('total_cost_usd')
print('' if cost is None else str(cost))
" 2>/dev/null)
export CLAUDE_CONTEXT_SIZE=$(echo "$_STDIN" | $PYTHON_BIN -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('context_window',{}).get('context_window_size',''))
" 2>/dev/null)

BAR_WIDTH=8

make_bar() {
    local pct=$1
    local filled=$(( pct * BAR_WIDTH / 100 ))
    (( filled > BAR_WIDTH )) && filled=$BAR_WIDTH
    local empty=$(( BAR_WIDTH - filled ))
    local bar="" i
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    printf '%s' "$bar"
}

get_multi_color() {
    local rule=$1 pct=$2
    case "$rule" in
        usage)
            if (( pct <= 60 )); then echo "32"
            elif (( pct <= 80 )); then echo "38;5;208"
            else echo "31"
            fi ;;
        battery)
            if (( pct < 20 )); then echo "31"
            else echo "32"
            fi ;;
    esac
}

SEPARATOR_ANSI=""

flush_line() {
    if [ ${#current_parts[@]} -gt 0 ]; then
        local sep=" | "
        [ -n "$SEPARATOR_ANSI" ] && sep=$'\033'"[${SEPARATOR_ANSI}m | "$'\033'"[0m"
        local result="" i
        for ((i=0; i<${#current_parts[@]}; i++)); do
            [ $i -gt 0 ] && result+="$sep"
            result+="${current_parts[$i]}"
        done
        echo "$result"
    fi
}

current_parts=()
while IFS= read -r raw_line; do
    if [ -z "$raw_line" ]; then
        flush_line
        current_parts=()
        continue
    fi

    element=$(printf '%s' "$raw_line" | cut -f1)
    prefix=$(printf '%s' "$raw_line" | cut -f2)
    ansi_code=$(printf '%s' "$raw_line" | cut -f3)
    bar_mode=$(printf '%s' "$raw_line" | cut -f4)
    bar_rule=$(printf '%s' "$raw_line" | cut -f5)

    if [ "$element" = "__sep__" ]; then SEPARATOR_ANSI="$ansi_code"; continue; fi

    script="$ELEMENTS_DIR/$element.sh"
    if [ -x "$script" ]; then
        out=$("$script" 2>/dev/null)
        if [ -n "$out" ]; then
            formatted=""

            if [ -n "$bar_mode" ] && [ "$bar_mode" != "off" ] && [ -n "$bar_rule" ]; then
                pct_num=$(printf '%s' "$out" | grep -o '[0-9]*' | head -1)
                if [ -n "$pct_num" ] && [[ "$pct_num" =~ ^[0-9]+$ ]]; then
                    bar=$(make_bar "$pct_num")
                    if [ "$bar_mode" = "multi" ]; then
                        bar_color=$(get_multi_color "$bar_rule" "$pct_num")
                        colored_bar=$'\033'"[${bar_color}m${bar}"$'\033'"[0m"
                        if [ -n "$ansi_code" ]; then
                            formatted=$'\033'"[${ansi_code}m${prefix}"$'\033'"[0m${colored_bar}"$'\033'"[${ansi_code}m ${out}"$'\033'"[0m"
                        else
                            formatted="${prefix}${colored_bar} ${out}"
                        fi
                    else  # mono
                        if [ -n "$ansi_code" ]; then
                            formatted=$'\033'"[${ansi_code}m${prefix}${bar} ${out}"$'\033'"[0m"
                        else
                            formatted="${prefix}${bar} ${out}"
                        fi
                    fi
                fi
            fi

            if [ -z "$formatted" ]; then
                formatted="${prefix}${out}"
                if [ -n "$ansi_code" ]; then
                    formatted=$'\033'"[${ansi_code}m${formatted}"$'\033'"[0m"
                fi
            fi

            current_parts+=("$formatted")
        fi
    fi
done < <($PYTHON_BIN -c "
import json, sys
EMOJIS = {
    'battery': '\U0001f50b',
    'cwd': '\U0001f4c1',
    'datetime': '\U0001f552',
    'git-branch': '\U0001f33f',
    'usage-5h': '\U0001f4ca',
    'burn-rate': '\U0001f525',
    'reset-time': '\u23f0',
    'context-pct': '\U0001f4cb',
    'session-duration': '\u23f1',
    'session-cost': '\U0001f4b0',
    'github-repo': '\U0001f4cd',
    'mood': '\U0001f3ad',
    'streak': '\U0001f4c8',
    'pomodoro': '\U0001f345',
    'file-entropy': '\U0001f500',
    'moon-phase': '\U0001f319',
    'haiku': '\U0001f4dc',
}
LABELS = {
    'battery': 'bat',
    'cwd': 'dir',
    'datetime': 'time',
    'git-branch': 'branch',
    'usage-5h': '5h',
    'burn-rate': 'burn',
    'reset-time': 'reset',
    'context-pct': 'ctx',
    'session-duration': 'dur',
    'session-cost': 'cost',
    'github-repo': 'repo',
    'mood': 'mood',
    'streak': 'streak',
    'pomodoro': 'pomo',
    'file-entropy': 'files',
    'moon-phase': 'phase',
    'haiku': 'haiku',
}
COLORS = {
    'green': '32', 'cyan': '36', 'red': '31', 'yellow': '33',
    'orange': '38;5;208', 'light gray': '37', 'dark gray': '90',
}
BAR_ELEMENTS = {
    'context-pct': 'usage',
    'usage-5h': 'usage',
    'battery': 'battery',
}
MODEL_EMOJI_SETS = {
    1: {'haiku': '\U0001f6eb', 'sonnet': '\U0001f6f0', 'opus': '\U0001f6f8'},
    2: {'haiku': '\u26b1\ufe0f', 'sonnet': '\U0001f3fa', 'opus': '\U0001f52e'},
}
def get_model_emoji(set_idx=1):
    import glob, os
    model = os.environ.get('CLAUDE_MODEL', '').strip()
    if not model:
        claude_dir = os.path.expanduser('~/.claude/projects')
        files = glob.glob(f'{claude_dir}/**/*.jsonl', recursive=True)
        if not files:
            return ''
        latest = max(files, key=os.path.getmtime)
        try:
            with open(latest, errors='replace') as fj:
                for line in fj:
                    try:
                        d = json.loads(line)
                        if d.get('type') == 'assistant':
                            m = d.get('message', {}).get('model')
                            if m: model = m
                    except Exception:
                        pass
        except Exception:
            pass
    if model:
        ml = model.lower()
        emoji_map = MODEL_EMOJI_SETS.get(set_idx, MODEL_EMOJI_SETS[1])
        for kw, em in emoji_map.items():
            if kw in ml:
                return em
    return ''
with open('$CONFIG') as f:
    d = json.load(f)
sl = d.get('statusline', {})
lines = sl.get('lines')
if lines is None:
    elems = sl.get('elements', [])
    lines = [elems] if elems else []
settings = sl.get('element_settings', {})
default_color = COLORS.get(sl.get('default_color') or '', '')
sep_color = COLORS.get(sl.get('separator_color') or '', '')
if sep_color:
    print(f'__sep__\t\t{sep_color}\t\t')
for i, line in enumerate(lines):
    if i > 0:
        print('')  # blank separator
    for elem in line:
        s = settings.get(elem, {})
        parts = []
        if s.get('emoji', False):
            if elem == 'model':
                raw_set = s.get('emoji_set', 1)
                set_idx = raw_set if isinstance(raw_set, int) and raw_set in (1, 2) else 1
                em = get_model_emoji(set_idx)
                if em: parts.append(em)
            else:
                e = EMOJIS.get(elem, '')
                if e: parts.append(e)
        if s.get('label', False):
            l = LABELS.get(elem, '')
            if l: parts.append(l)
        prefix = ' '.join(parts) + ' ' if parts else ''
        color = COLORS.get(s.get('color') or '', '') or default_color
        bar_mode = s.get('bar', 'off') or 'off'
        bar_rule = BAR_ELEMENTS.get(elem, '')
        print(f'{elem}\t{prefix}\t{color}\t{bar_mode}\t{bar_rule}')
" 2>/dev/null)

# Flush last line
flush_line
