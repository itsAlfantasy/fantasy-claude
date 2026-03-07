#!/usr/bin/env python3
"""Interactive TUI configurator for claude-hooks."""

import curses
import json
import platform
import subprocess
import unicodedata
from pathlib import Path

REPO_DIR = Path(__file__).parent

EVENT_DIRS = {
    "on_error": "sounds/error",
    "on_stop": "sounds/notification",
    "on_notification": "sounds/notification",
}

EVENT_LABELS = {
    "on_error": "On tool error",
    "on_stop": "On tool stop",
    "on_notification": "On notification",
}

HOOKS_ITEMS = ["on_error", "on_stop", "on_notification"]
MAIN_ITEMS = ["Hooks", "Statusline"]
MAX_ELEMENTS_PER_LINE = 4

ELEMENT_EMOJIS = {
    "battery": "\U0001f50b",
    "cwd": "\U0001f4c1",
    "datetime": "\U0001f552",
    "git-branch": "\U0001f33f",
    "usage-5h": "\U0001f4ca",
    "burn-rate": "\U0001f525",
    "reset-time": "\u23f0",
    "context-pct": "\U0001f4cb",
    "session-duration": "\u23f1",
    "session-cost": "\U0001f4b0",
}

ELEMENT_LABELS = {
    "battery": "bat",
    "cwd": "dir",
    "datetime": "time",
    "git-branch": "branch",
    "usage-5h": "5h",
    "burn-rate": "burn",
    "reset-time": "reset",
    "context-pct": "ctx",
    "session-duration": "dur",
    "session-cost": "cost",
    "model": "model",
}

MODEL_EMOJI_SETS = [
    {},  # index 0: unused placeholder
    {  # index 1: set 1
        "haiku": "\U0001f6eb",   # 🛫 airplane departing
        "sonnet": "\U0001f6f0",  # 🛰 satellite
        "opus": "\U0001f6f8",    # 🛸 flying saucer
    },
    {  # index 2: set 2
        "haiku": "\u26b1\ufe0f",  # ⚱️ urn
        "sonnet": "\U0001f3fa",   # 🏺 amphora
        "opus": "\U0001f52e",     # 🔮 crystal ball
    },
]

BAR_ELEMENTS = {
    "context-pct": "usage",
    "usage-5h": "usage",
    "battery": "battery",
}
BAR_OPTIONS = ["off", "mono", "multi"]
BAR_WIDTH = 8


def _bar_color_for(rule: str, pct: int) -> str:
    if rule == "usage":
        if pct <= 60:
            return "green"
        elif pct <= 80:
            return "orange"
        else:
            return "red"
    elif rule == "battery":
        return "red" if pct < 20 else "green"
    return ""

COLOR_OPTIONS = [
    ("none", None),
    ("green", "32"),
    ("cyan", "36"),
    ("red", "31"),
    ("yellow", "33"),
    ("orange", "38;5;208"),
    ("light gray", "37"),
    ("dark gray", "90"),
]

# Curses color pair index for each color name (initialized in run())
CURSES_COLOR_MAP: dict[str, int] = {}


def init_colors() -> None:
    """Initialize curses color pairs for element preview colors."""
    pairs = [
        ("green", curses.COLOR_GREEN),
        ("cyan", curses.COLOR_CYAN),
        ("red", curses.COLOR_RED),
        ("yellow", curses.COLOR_YELLOW),
        ("orange", 208),  # 256-color
        ("light gray", 7),
        ("dark gray", 8),
    ]
    for i, (name, fg) in enumerate(pairs, start=1):
        try:
            curses.init_pair(i, fg, -1)
            CURSES_COLOR_MAP[name] = i
        except Exception:
            pass


_preview_proc: subprocess.Popen | None = None


def preview_sound(sound_path: Path) -> None:
    global _preview_proc
    if _preview_proc and _preview_proc.poll() is None:
        _preview_proc.kill()
    if not sound_path.exists():
        return
    if platform.system() == "Darwin":
        _preview_proc = subprocess.Popen(
            ["afplay", str(sound_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        for player in ("paplay", "aplay"):
            if subprocess.run(["command", "-v", player], capture_output=True).returncode == 0:
                _preview_proc = subprocess.Popen(
                    [player, str(sound_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                break


def list_sounds(directory: str) -> list[str]:
    d = REPO_DIR / directory
    if not d.exists():
        return ["(none)"]
    return ["(none)"] + sorted(p.stem for p in d.glob("*.mp3"))


def display_width(s: str) -> int:
    """Return the terminal display width of s, correctly counting wide/emoji chars as 2."""
    width = 0
    chars = list(s)
    i = 0
    while i < len(chars):
        cp = ord(chars[i])
        if 0xFE00 <= cp <= 0xFE0F:  # bare variation selector: already counted by lookahead
            i += 1
            continue
        next_cp = ord(chars[i + 1]) if i + 1 < len(chars) else 0
        has_vs16 = 0xFE00 <= next_cp <= 0xFE0F
        if cp >= 0x10000:  # supplementary plane (emoji, etc.) are wide
            width += 2
        elif has_vs16:  # BMP char + VS16 = emoji presentation = 2 wide
            width += 2
        else:
            eaw = unicodedata.east_asian_width(chars[i])
            if eaw in ('W', 'F'):
                width += 2
            elif unicodedata.category(chars[i]) in ('Mn', 'Cf'):
                pass  # zero-width
            else:
                width += 1
        i += 1
    return width


def list_elements() -> list[str]:
    d = REPO_DIR / "statusline/elements"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.sh"))


def run_element(name: str, settings: dict | None = None) -> list[tuple[str, str | None]]:
    """Return a list of (text, color_name) segments for rendering."""
    script = REPO_DIR / "statusline/elements" / f"{name}.sh"
    try:
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=2)
        raw = r.stdout.strip() or name
    except Exception:
        raw = name
    if settings:
        s = settings.get(name, {})
        prefix_parts = []
        if s.get("emoji"):
            if name == "model":
                set_idx = s.get("emoji_set", 1)
                if not isinstance(set_idx, int) or set_idx not in (1, 2):
                    set_idx = 1
                emoji_set_map = MODEL_EMOJI_SETS[set_idx]
                raw_lower = raw.lower()
                for keyword, em in emoji_set_map.items():
                    if keyword in raw_lower:
                        prefix_parts.append(em)
                        break
            else:
                emoji = ELEMENT_EMOJIS.get(name, "")
                if emoji:
                    prefix_parts.append(emoji)
        if s.get("label"):
            lbl = ELEMENT_LABELS.get(name, "")
            if lbl:
                prefix_parts.append(lbl)
        bar_mode = s.get("bar", "off") or "off"
        if bar_mode != "off" and name in BAR_ELEMENTS:
            digits = "".join(c for c in raw if c.isdigit())
            if digits:
                pct = min(100, int(digits))
                filled = pct * BAR_WIDTH // 100
                bar = "█" * filled + "░" * (BAR_WIDTH - filled)
                if bar_mode == "multi":
                    bar_color = _bar_color_for(BAR_ELEMENTS[name], pct)
                    prefix_text = (" ".join(prefix_parts) + " ") if prefix_parts else ""
                    segs: list[tuple[str, str | None]] = []
                    if prefix_text:
                        segs.append((prefix_text, None))
                    segs.append((bar, bar_color or None))
                    segs.append((" " + raw, None))
                    return segs
                else:  # mono
                    parts = prefix_parts + [bar, raw]
                    return [(" ".join(p for p in parts if p), None)]
        text = f"{' '.join(prefix_parts)} {raw}" if prefix_parts else raw
        return [(text, None)]
    return [(raw, None)]


def load_config() -> dict:
    cfg_path = REPO_DIR / "config.json"
    with open(cfg_path) as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    cfg_path = REPO_DIR / "config.json"
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def draw_screen(stdscr, title: str, items: list[str], cursor: int, hint: str = "") -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Header
    header = f"  claude-hooks · {title}  "
    stdscr.addstr(0, 0, header[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    # Items
    for i, item in enumerate(items):
        row = 3 + i
        if row >= h - 3:
            break
        if i == cursor:
            stdscr.addstr(row, 2, f"> {item}"[:w - 2], curses.A_REVERSE)
        else:
            stdscr.addstr(row, 2, f"  {item}"[:w - 2])

    # Footer hint
    footer_row = h - 2
    if footer_row > 3 + len(items):
        stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
    if hint and footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)

    stdscr.refresh()


def draw_statusline_editor(
    stdscr,
    lines: list[list[str]],
    current_line: int,
    cursor: int,
    elements: list[str],
    status_msg: str,
    element_settings: dict | None = None,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    n_lines = len(lines)

    title = f"claude-hooks · Statusline · Line {current_line + 1} of {n_lines}"
    stdscr.addstr(0, 0, f"  {title}  "[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    row = 3
    stdscr.addstr(row, 2, "Preview (all lines):"[:w - 2])
    row += 1
    for i, line_elems in enumerate(lines):
        if row >= h - 8:
            break
        prefix = "> " if i == current_line else "  "
        base_attr = curses.A_BOLD if i == current_line else curses.A_NORMAL
        stdscr.addstr(row, 2, f"{prefix}Line {i + 1}:  "[:w - 2], base_attr)
        col = 2 + len(f"{prefix}Line {i + 1}:  ")
        if line_elems:
            for ei, e in enumerate(line_elems):
                if ei > 0:
                    sep = " | "
                    if col + len(sep) < w:
                        stdscr.addstr(row, col, sep, base_attr)
                    col += len(sep)
                segments = run_element(e, element_settings)
                text_color = (element_settings or {}).get(e, {}).get("color")
                for seg_text, seg_color in segments:
                    color_name = seg_color if seg_color is not None else text_color
                    pair_idx = CURSES_COLOR_MAP.get(color_name or "", 0)
                    attr = curses.color_pair(pair_idx) | base_attr if pair_idx else base_attr
                    seg_w = display_width(seg_text)
                    if col + seg_w < w:
                        stdscr.addstr(row, col, seg_text, attr)
                    col += seg_w
        else:
            stdscr.addstr(row, col, "(empty)", base_attr)
        row += 1

    row += 1
    stdscr.addstr(row, 2, "─" * min(w - 4, 56))
    row += 1

    # All elements used on other lines (not current)
    used_elsewhere: set[str] = set()
    for i, line_elems in enumerate(lines):
        if i != current_line:
            used_elsewhere.update(line_elems)

    for i, elem in enumerate(elements):
        if row >= h - 4:
            break
        checked = elem in lines[current_line]
        grayed = elem in used_elsewhere
        if checked:
            marker = "[x]"
        elif grayed:
            marker = "[~]"
        else:
            marker = "[ ]"
        es = (element_settings or {}).get(elem, {})
        prefix_parts = []
        if es.get("emoji"):
            if elem == "model":
                set_idx = es.get("emoji_set", 1)
                if not isinstance(set_idx, int) or set_idx not in (1, 2):
                    set_idx = 1
                e_icon = next(iter(MODEL_EMOJI_SETS[set_idx].values()), "")
            else:
                e_icon = ELEMENT_EMOJIS.get(elem, "")
            if e_icon:
                prefix_parts.append(e_icon)
        if es.get("label"):
            e_lbl = ELEMENT_LABELS.get(elem, "")
            if e_lbl:
                prefix_parts.append(e_lbl)
        prefix = " ".join(prefix_parts) + " " if prefix_parts else ""
        color_indicator = f" ({es['color']})" if es.get("color") else ""
        bar_mode = es.get("bar", "off") or "off"
        bar_indicator = f" [bar:{bar_mode}]" if bar_mode != "off" and elem in BAR_ELEMENTS else ""
        label = f"{marker} {prefix}{elem}{color_indicator}{bar_indicator}"
        if grayed:
            label += "  ← used on another line"
        elem_color = CURSES_COLOR_MAP.get(es.get("color", ""), 0)
        if i == cursor:
            stdscr.addstr(row, 2, f"> {label}"[:w - 2], curses.A_REVERSE)
        elif grayed:
            stdscr.addstr(row, 2, f"  {label}"[:w - 2], curses.A_DIM)
        else:
            attr = curses.color_pair(elem_color) if elem_color else curses.A_NORMAL
            stdscr.addstr(row, 2, f"  {label}"[:w - 2], attr)
        row += 1

    row += 1
    if row < h - 3:
        stdscr.addstr(row, 2, "─" * min(w - 4, 56))

    footer_row = h - 2
    if status_msg and footer_row < h:
        stdscr.addstr(footer_row - 1, 2, status_msg[:w - 2], curses.A_BOLD)
    hint = "1-9/Tab/←/→ line   ↑↓ navigate   Enter toggle   c config   s save   q cancel"
    if footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)

    stdscr.refresh()


def draw_element_config(
    stdscr,
    element: str,
    emoji_on: bool,
    label_on: bool,
    color_name: str | None,
    cursor: int,
    bar: str = "off",
    emoji_set: int = 1,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    if element == "model":
        cur_set = MODEL_EMOJI_SETS[emoji_set] if emoji_set in (1, 2) else MODEL_EMOJI_SETS[1]
        emoji_char = " ".join(cur_set.values())
    else:
        emoji_char = ELEMENT_EMOJIS.get(element, "")
    label_word = ELEMENT_LABELS.get(element, "")
    title = f"claude-hooks · Element: {element}"
    stdscr.addstr(0, 0, f"  {title}  "[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    row = 3
    # Emoji toggle (index 0)
    emoji_text = f"{'[x]' if emoji_on else '[ ]'} Emoji: {emoji_char}" if emoji_char else "[ ] Emoji: (none available)"
    if cursor == 0:
        stdscr.addstr(row, 2, f"> {emoji_text}"[:w - 2], curses.A_REVERSE)
    else:
        stdscr.addstr(row, 2, f"  {emoji_text}"[:w - 2])
    row += 1

    # Label toggle (index 1)
    label_text = f"{'[x]' if label_on else '[ ]'} Label: {label_word}" if label_word else "[ ] Label: (none available)"
    if cursor == 1:
        stdscr.addstr(row, 2, f"> {label_text}"[:w - 2], curses.A_REVERSE)
    else:
        stdscr.addstr(row, 2, f"  {label_text}"[:w - 2])
    row += 2

    stdscr.addstr(row, 2, "Color:"[:w - 2], curses.A_BOLD)
    row += 1

    for i, (cname, _) in enumerate(COLOR_OPTIONS):
        list_idx = i + 2  # cursor index (0=emoji, 1=label, 2..N=colors)
        marker = "●" if cname == (color_name or "none") else "○"
        label = f"{marker} {cname}"
        if list_idx == cursor:
            stdscr.addstr(row, 2, f"> {label}"[:w - 2], curses.A_REVERSE)
        else:
            stdscr.addstr(row, 2, f"  {label}"[:w - 2])
        row += 1

    if element == "model" and row < h - 5:
        row += 1
        stdscr.addstr(row, 2, "Emoji set:"[:w - 2], curses.A_BOLD)
        row += 1
        model_set_start = 2 + len(COLOR_OPTIONS)
        for i, set_map in enumerate(MODEL_EMOJI_SETS[1:], start=1):
            list_idx = model_set_start + (i - 1)
            marker = "●" if emoji_set == i else "○"
            icons = " ".join(set_map.values())
            opt_label = f"{marker} set {i}  {icons}"
            if list_idx == cursor:
                stdscr.addstr(row, 2, f"> {opt_label}"[:w - 2], curses.A_REVERSE)
            else:
                stdscr.addstr(row, 2, f"  {opt_label}"[:w - 2])
            row += 1

    if element in BAR_ELEMENTS and row < h - 6:
        row += 1
        stdscr.addstr(row, 2, "Bar:"[:w - 2], curses.A_BOLD)
        row += 1
        bar_option_start = 2 + len(COLOR_OPTIONS)
        for i, opt in enumerate(BAR_OPTIONS):
            list_idx = bar_option_start + i
            marker = "●" if opt == (bar or "off") else "○"
            opt_label = f"{marker} {opt}"
            if list_idx == cursor:
                stdscr.addstr(row, 2, f"> {opt_label}"[:w - 2], curses.A_REVERSE)
            else:
                stdscr.addstr(row, 2, f"  {opt_label}"[:w - 2])
            row += 1

    footer_row = h - 2
    if footer_row > row + 1:
        stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
    hint = "↑↓ navigate   Enter toggle/select   q back"
    if footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)

    stdscr.refresh()


def _play_preview(event: str, sounds: list[str], cursor: int) -> None:
    name = sounds[cursor]
    if name == "(none)":
        return
    sound_file = REPO_DIR / EVENT_DIRS[event] / f"{name}.mp3"
    preview_sound(sound_file)


def run(stdscr) -> None:
    curses.curs_set(0)
    try:
        curses.use_default_colors()
    except Exception:
        pass
    init_colors()

    cfg = load_config()
    stack: list[tuple[str, int]] = []  # (screen_id, cursor)
    screen = "main"
    cursor = 0
    sounds: list[str] = []  # populated when in sound_picker screen

    # Statusline editor state
    sl_lines: list[list[str]] = []
    sl_current_line: int = 0
    sl_elem_cursor: int = 0
    sl_elements: list[str] = []
    sl_status_msg: str = ""

    # Element config state
    ec_elem: str = ""
    ec_emoji_on: bool = False
    ec_label_on: bool = False
    ec_color: str | None = None
    ec_bar: str = "off"
    ec_model_set: int = 1
    ec_cursor: int = 0

    while True:
        # --- Build display for current screen ---
        if screen == "main":
            title = "Main"
            items = MAIN_ITEMS
            hint = "↑↓ navigate   Enter select   q quit"

        elif screen == "hooks":
            title = "Hooks"
            items = []
            for event in HOOKS_ITEMS:
                val = cfg["sounds"].get(event) or "(none)"
                label = EVENT_LABELS[event]
                items.append(f"{label:<22} [{val}]")
            hint = "↑↓ navigate   Enter select   ← back   q quit"

        elif screen.startswith("sound_picker:"):
            event = screen.split(":", 1)[1]
            title = f"Hooks › {EVENT_LABELS[event]}"
            sounds = list_sounds(EVENT_DIRS[event])
            current = cfg["sounds"].get(event) or "(none)"
            items = [f"{s} ✓" if s == current else s for s in sounds]
            hint = "↑↓ navigate + preview   Enter confirm   ← back   q quit"

        elif screen == "statusline_lines":
            title = "Statusline"
            items = ["0 — disabled", "1", "2", "3", "4", "5", "6"]
            hint = "↑↓ navigate   Enter confirm   ← back   q quit"

        elif screen == "statusline_editor":
            draw_statusline_editor(
                stdscr, sl_lines, sl_current_line, sl_elem_cursor, sl_elements, sl_status_msg,
                cfg.get("statusline", {}).get("element_settings"),
            )
            key = stdscr.getch()

            # Handle ESC sequences manually as fallback for broken keypad mode.
            # Arrow keys send: ESC [ A/B/C/D. If keypad(True) isn't decoding
            # them, getch() returns 27 (ESC) first.
            if key == 27:
                stdscr.nodelay(True)
                k2 = stdscr.getch()
                k3 = stdscr.getch()
                stdscr.nodelay(False)
                if k2 == ord("["):
                    if k3 == ord("A"):
                        key = curses.KEY_UP
                    elif k3 == ord("B"):
                        key = curses.KEY_DOWN
                    elif k3 == ord("C"):
                        key = curses.KEY_RIGHT
                    elif k3 == ord("D"):
                        key = curses.KEY_LEFT
                    elif k3 == ord("Z"):
                        key = curses.KEY_BTAB
                # else: stray ESC, ignore


            if key in (curses.KEY_UP, ord("k")):
                sl_elem_cursor = max(0, sl_elem_cursor - 1)
                sl_status_msg = ""

            elif key in (curses.KEY_DOWN, ord("j")):
                sl_elem_cursor = min(len(sl_elements) - 1, sl_elem_cursor + 1)
                sl_status_msg = ""

            elif key in (curses.KEY_LEFT, ord("h"), curses.KEY_BTAB):
                sl_current_line = max(0, sl_current_line - 1)
                sl_elem_cursor = 0
                sl_status_msg = ""

            elif key in (curses.KEY_RIGHT, ord("l"), ord("\t")):  # Tab = next line
                sl_current_line = min(len(sl_lines) - 1, sl_current_line + 1)
                sl_elem_cursor = 0
                sl_status_msg = ""

            elif ord("1") <= key <= ord("9"):
                n = key - ord("1")  # key "1" → index 0
                if n < len(sl_lines):
                    sl_current_line = n
                    sl_elem_cursor = 0
                    sl_status_msg = ""

            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                elem = sl_elements[sl_elem_cursor]
                used_elsewhere: set[str] = set()
                for i, line_elems in enumerate(sl_lines):
                    if i != sl_current_line:
                        used_elsewhere.update(line_elems)
                if elem in used_elsewhere:
                    sl_status_msg = f"'{elem}' is already used on another line"
                elif elem in sl_lines[sl_current_line]:
                    sl_lines[sl_current_line].remove(elem)
                    sl_status_msg = ""
                else:
                    if len(sl_lines[sl_current_line]) >= MAX_ELEMENTS_PER_LINE:
                        sl_status_msg = f"Max {MAX_ELEMENTS_PER_LINE} elements per line"
                    else:
                        sl_lines[sl_current_line].append(elem)
                        sl_status_msg = ""

            elif key == ord("c"):
                # Open element config
                elem = sl_elements[sl_elem_cursor]
                ec_elem = elem
                settings = cfg.get("statusline", {}).get("element_settings", {}).get(elem, {})
                ec_emoji_on = settings.get("emoji", False)
                ec_label_on = settings.get("label", False)
                ec_color = settings.get("color", None)
                ec_bar = settings.get("bar", "off") or "off"
                raw_set = settings.get("emoji_set", 1)
                ec_model_set = raw_set if isinstance(raw_set, int) and raw_set in (1, 2) else 1
                ec_cursor = 0
                stack.append((screen, cursor))
                screen = "element_config"
                cursor = 0

            elif key == ord("s"):
                # Compact: drop empty lines
                compacted = [line for line in sl_lines if line]
                cfg.setdefault("statusline", {})["lines"] = compacted
                # Remove old flat format if present
                cfg["statusline"].pop("elements", None)
                save_config(cfg)
                if stack:
                    screen, cursor = stack.pop()

            elif key == ord("q"):
                if stack:
                    screen, cursor = stack.pop()

            continue

        elif screen == "element_config":
            draw_element_config(stdscr, ec_elem, ec_emoji_on, ec_label_on, ec_color, ec_cursor, ec_bar, ec_model_set)
            key = stdscr.getch()

            # ESC sequence handling
            if key == 27:
                stdscr.nodelay(True)
                k2 = stdscr.getch()
                k3 = stdscr.getch()
                stdscr.nodelay(False)
                if k2 == ord("["):
                    if k3 == ord("A"):
                        key = curses.KEY_UP
                    elif k3 == ord("B"):
                        key = curses.KEY_DOWN
                    elif k3 == ord("D"):
                        key = curses.KEY_LEFT

            max_idx = 1 + len(COLOR_OPTIONS)  # 0=emoji, 1=label, 2..N=colors
            if ec_elem == "model":
                max_idx += len(MODEL_EMOJI_SETS) - 1  # set1, set2
            if ec_elem in BAR_ELEMENTS:
                max_idx += len(BAR_OPTIONS)
            if key in (curses.KEY_UP, ord("k")):
                ec_cursor = max(0, ec_cursor - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                ec_cursor = min(max_idx, ec_cursor + 1)
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                model_set_start = 2 + len(COLOR_OPTIONS)
                bar_option_start = model_set_start + (len(MODEL_EMOJI_SETS) - 1 if ec_elem == "model" else 0)
                if ec_cursor == 0:
                    ec_emoji_on = not ec_emoji_on
                elif ec_cursor == 1:
                    ec_label_on = not ec_label_on
                elif ec_elem == "model" and model_set_start <= ec_cursor < bar_option_start:
                    ec_model_set = (ec_cursor - model_set_start) + 1
                elif ec_elem in BAR_ELEMENTS and ec_cursor >= bar_option_start:
                    ec_bar = BAR_OPTIONS[ec_cursor - bar_option_start]
                else:
                    cname, _ = COLOR_OPTIONS[ec_cursor - 2]
                    ec_color = None if cname == "none" else cname
                # Save immediately
                sl_settings = cfg.setdefault("statusline", {}).setdefault("element_settings", {})
                entry = {"emoji": ec_emoji_on, "label": ec_label_on, "color": ec_color, "bar": ec_bar}
                if ec_elem == "model":
                    entry["emoji_set"] = ec_model_set
                sl_settings[ec_elem] = entry
                save_config(cfg)
            elif key in (ord("q"), curses.KEY_LEFT, ord("h"), 27):
                if stack:
                    screen, cursor = stack.pop()

            continue

        else:
            title = screen.capitalize()
            items = ["(coming soon)"]
            hint = "← back   q quit"

        draw_screen(stdscr, title, items, cursor, hint)

        key = stdscr.getch()

        # Navigation
        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
            if screen.startswith("sound_picker:"):
                _play_preview(screen.split(":", 1)[1], sounds, cursor)

        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(items) - 1, cursor + 1)
            if screen.startswith("sound_picker:"):
                _play_preview(screen.split(":", 1)[1], sounds, cursor)

        elif key in (curses.KEY_LEFT, ord("h"), 27):  # 27 = Esc
            if stack:
                screen, cursor = stack.pop()

        elif key == ord("q"):
            break

        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            if screen == "main":
                choice = MAIN_ITEMS[cursor]
                if choice == "Hooks":
                    stack.append((screen, cursor))
                    screen = "hooks"
                    cursor = 0
                else:
                    stack.append((screen, cursor))
                    screen = "statusline_lines"
                    cursor = 0

            elif screen == "hooks":
                event = HOOKS_ITEMS[cursor]
                stack.append((screen, cursor))
                screen = f"sound_picker:{event}"
                sounds = list_sounds(EVENT_DIRS[event])
                current = cfg["sounds"].get(event) or "(none)"
                try:
                    cursor = sounds.index(current)
                except ValueError:
                    cursor = 0

            elif screen.startswith("sound_picker:"):
                event = screen.split(":", 1)[1]
                chosen = sounds[cursor]
                cfg["sounds"][event] = None if chosen == "(none)" else chosen
                save_config(cfg)
                if stack:
                    screen, cursor = stack.pop()

            elif screen == "statusline_lines":
                n = cursor  # item index 0 = disabled (0 lines), 1 = 1 line, etc.
                if n == 0:
                    # disabled
                    cfg.setdefault("statusline", {})["lines"] = []
                    cfg["statusline"].pop("elements", None)
                    save_config(cfg)
                    if stack:
                        screen, cursor = stack.pop()
                else:
                    # Load existing lines from config (new format), padding/trimming to n lines
                    sl_data = cfg.get("statusline", {})
                    existing = sl_data.get("lines")
                    if existing is None:
                        # backward compat: flat elements = single line
                        elems = sl_data.get("elements", [])
                        existing = [elems] if elems else []
                    # Resize to n lines
                    sl_lines = [list(existing[i]) if i < len(existing) else [] for i in range(n)]
                    # Start on the first empty line (skip already-configured ones)
                    sl_current_line = 0
                    for idx, ln in enumerate(sl_lines):
                        if not ln:
                            sl_current_line = idx
                            break
                    sl_elem_cursor = 0
                    sl_elements = list_elements()
                    sl_status_msg = ""
                    stack.append((screen, cursor))
                    screen = "statusline_editor"
                    cursor = 0

            else:
                if stack:
                    screen, cursor = stack.pop()


def main() -> None:
    curses.wrapper(run)


if __name__ == "__main__":
    main()
