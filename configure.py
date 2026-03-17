#!/usr/bin/env python3
"""Interactive TUI configurator for claude-hooks."""

import curses
import json
import platform
import subprocess
import unicodedata
from pathlib import Path

REPO_DIR = Path(__file__).parent
VERSION = (REPO_DIR / "VERSION").read_text().strip() if (REPO_DIR / "VERSION").exists() else "unknown"

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
MAIN_ITEMS = ["Hooks", "Statusline", "Integrations"]
MAX_ELEMENTS_PER_LINE = 4

_element_cache: dict[str, str] = {}  # name -> raw_output

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
SESSION_HOOK_SCRIPT = Path.home() / ".claude" / "hooks" / "session-git-cleanup.sh"
INTEGRATIONS_PATH = Path.home() / ".claude" / "integrations.json"

NOTIFY_SCRIPTS = {
    "permission_prompt": REPO_DIR / "hooks" / "notify-permission.sh",
    "idle_prompt":       REPO_DIR / "hooks" / "notify-idle.sh",
    "elicitation_dialog": REPO_DIR / "hooks" / "notify-elicitation.sh",
    "auth_success":      REPO_DIR / "hooks" / "notify-auth.sh",
}

NOTIFY_DESCRIPTION = [
    "Sends a notification when Claude Code needs your",
    "input. Uses iTerm2 native alerts on macOS or",
    "notify-send on Linux.",
    "",
    "To avoid duplicate notifications, disable Claude",
    "Code's built-in notifications: run /config, scroll",
    "down to Notifications, set to Disabled, then",
    "restart your Claude Code sessions.",
]

GIT_CLEANUP_DESCRIPTION = [
    "Keeps local branches in sync with remote on each",
    "session start. Fetches all remotes, prunes stale",
    "tracking refs, and safely deletes local branches",
    "whose upstream is gone (preserves unmerged changes).",
]

OBSIDIAN_FIELDS = [
    ("vault_path",         "Vault path",         True),
    ("default_folder",     "Default folder",     False),
    ("templates_folder",   "Templates folder",   False),
    ("daily_notes_folder", "Daily notes folder", False),
]

OB_IDX_VAULT_PATH   = 1
OB_IDX_DEF_FOLDER   = 2
OB_IDX_TMPL_FOLDER  = 3
OB_IDX_DAILY_FOLDER = 4
OB_IDX_INSTALL_MCP  = 5
OB_IDX_INSTRUCTIONS = 6

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
    "github-repo": "\U0001f4cd",
    "mood": "\U0001f3ad",
    "streak": "\U0001f4c8",
    "pomodoro": "\U0001f345",
    "file-entropy": "\U0001f500",
    "moon-phase": "\U0001f319",
    "haiku": "\U0001f4dc",
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
    "github-repo": "repo",
    "mood": "mood",
    "streak": "streak",
    "pomodoro": "pomo",
    "file-entropy": "files",
    "moon-phase": "phase",
    "haiku": "haiku",
}

ELEMENT_CATEGORIES = {
    "Claude / AI": ["model", "context-pct", "burn-rate", "session-cost", "session-duration", "file-entropy", "streak"],
    "Git / Project": ["git-branch", "cwd", "github-repo"],
    "System": ["battery", "datetime"],
    "Rate limits": ["usage-5h", "reset-time"],
    "Fun": ["mood", "moon-phase", "haiku", "pomodoro"],
}

MOOD_EMOJI_SETS = {
    1: ["😴", "☕", "🍕", "💻", "🌆", "🌙"],
    2: ["🥱", "⚡", "🎯", "🔥", "🍺", "🌃"],
    3: ["💤", "🌅", "☀️", "🌤️", "🌇", "🌌"],
}
POMO_DURATIONS = [15, 20, 25, 30, 45, 60]  # minutes

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


def _build_display_list(elements: list[str]) -> list[tuple]:
    """Build a flat display list interleaving category headers and element names."""
    result = []
    categorized: set[str] = set()
    for cat_name, cat_elems in ELEMENT_CATEGORIES.items():
        matching = [e for e in cat_elems if e in elements]
        if not matching:
            continue
        result.append(("header", cat_name))
        for e in matching:
            result.append(("element", e))
            categorized.add(e)
    uncategorized = [e for e in elements if e not in categorized]
    if uncategorized:
        result.append(("header", "Other"))
        for e in uncategorized:
            result.append(("element", e))
    return result


def _clamp_elem_scroll(scroll: int, cursor: int, elements: list[str], avail_rows: int) -> int:
    """Adjust scroll so the cursor element is visible in the element list."""
    if not elements or avail_rows < 1:
        return 0
    cursor_elem = elements[cursor]
    display_items = _build_display_list(elements)
    cursor_di = 0
    for di, item in enumerate(display_items):
        if item[0] == "element" and item[1] == cursor_elem:
            cursor_di = di
            break
    if cursor_di < scroll:
        scroll = cursor_di
    elif cursor_di >= scroll + avail_rows:
        scroll = cursor_di - avail_rows + 1
    return max(0, scroll)


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
    if name in _element_cache:
        raw = _element_cache[name]
    else:
        try:
            r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=2)
            raw = r.stdout.strip() or name
        except Exception:
            raw = name
        _element_cache[name] = raw
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


def clear_element_cache() -> None:
    _element_cache.clear()


def load_config() -> dict:
    cfg_path = REPO_DIR / "config.json"
    with open(cfg_path) as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    cfg_path = REPO_DIR / "config.json"
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def load_integrations() -> dict:
    try:
        with open(INTEGRATIONS_PATH) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("obsidian", {})
    ob = data["obsidian"]
    for key, _label, _required in OBSIDIAN_FIELDS:
        ob.setdefault(key, "")
    return data


def save_integrations(integ: dict) -> None:
    INTEGRATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INTEGRATIONS_PATH, "w") as f:
        json.dump(integ, f, indent=2)
        f.write("\n")


def check_obsidian_cli() -> bool:
    return subprocess.run(["which", "obsidian"], capture_output=True).returncode == 0


def run_mcp_install() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["claude", "mcp", "add", "obsidian-local-rest-api"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            return True, "MCP provider installed successfully"
        msg = (r.stderr.strip() or r.stdout.strip() or "Install failed")
        return False, msg
    except FileNotFoundError:
        return False, "claude not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "Install timed out"


OBSIDIAN_INSTRUCTIONS = [
    "Setup Instructions",
    "",
    "1. Install obsidian-cli",
    "   macOS:  brew install obsidian-cli",
    "",
    "2. Enable 'Local REST API' community plugin in Obsidian",
    "   Settings > Community plugins > Browse > Local REST API",
    "   Copy the API key from the plugin settings.",
    "",
    "3. Keep Obsidian open — CLI and MCP require it running.",
    "",
    "4. Set vault path in this screen, then press",
    "   [Install MCP provider] to register the MCP server.",
    "",
    "5. What configure.py CANNOT do (must be done manually):",
    "   - Install the Local REST API Obsidian plugin",
    "   - Provide the API key to the MCP server",
    "   - Install obsidian-cli itself",
    "   - Restart Claude Code after MCP install",
    "     (required for MCP to take effect)",
    "",
    "  ESC / q to go back",
]


def _load_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text())
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def is_git_cleanup_enabled() -> bool:
    settings = _load_settings()
    hooks = settings.get("hooks", {})
    for entry in hooks.get("SessionStart", []):
        cmd = entry if isinstance(entry, str) else entry.get("command", "")
        if "session-git-cleanup" in cmd:
            return True
    return False


def toggle_git_cleanup(enable: bool) -> None:
    settings = _load_settings()
    hooks = settings.setdefault("hooks", {})
    session_hooks = hooks.get("SessionStart", [])
    cmd = str(SESSION_HOOK_SCRIPT)

    # Remove existing entry
    session_hooks = [
        e for e in session_hooks
        if "session-git-cleanup" not in (e if isinstance(e, str) else e.get("command", ""))
    ]

    if enable:
        session_hooks.append({"command": cmd})

    hooks["SessionStart"] = session_hooks
    settings["hooks"] = hooks
    _save_settings(settings)


NOTIFY_LABELS = {
    "permission_prompt": "🔐 Permission prompt",
    "idle_prompt":       "💤 Idle prompt",
    "elicitation_dialog": "❓ Elicitation dialog",
    "auth_success":      "✅ Auth success",
}


def get_notify_states() -> dict[str, bool]:
    """Return enabled state for each notification type."""
    settings = _load_settings()
    hooks = settings.get("hooks", {})
    states = {k: False for k in NOTIFY_SCRIPTS}
    for entry in hooks.get("Notification", []):
        matcher = entry.get("matcher", "")
        for h in (entry.get("hooks", []) if isinstance(entry, dict) else []):
            cmd = h.get("command", "")
            if "notify-" in cmd and cmd.endswith(".sh") and matcher in NOTIFY_SCRIPTS:
                states[matcher] = True
    return states


def is_notify_enabled() -> bool:
    return any(get_notify_states().values())


def toggle_notify_type(ntype: str, enable: bool) -> None:
    """Toggle a single notification type on or off."""
    settings = _load_settings()
    hooks = settings.setdefault("hooks", {})
    notif_hooks = hooks.get("Notification", [])

    # Remove existing entry for this type (and legacy notify.sh)
    notif_hooks = [
        e for e in notif_hooks
        if not (
            e.get("matcher", "") == ntype
            and any(
                ("notify-" in h.get("command", "") or "notify.sh" in h.get("command", ""))
                for h in (e.get("hooks", []) if isinstance(e, dict) else [])
            )
        )
    ]

    if enable:
        script = NOTIFY_SCRIPTS[ntype]
        notif_hooks.append({
            "matcher": ntype,
            "hooks": [{"type": "command", "command": f"bash {script}"}]
        })

    hooks["Notification"] = notif_hooks
    settings["hooks"] = hooks
    _save_settings(settings)


def draw_notify_config(stdscr, states: dict[str, bool], cursor: int) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    header = "  claude-hooks · Hooks › Notifications  "
    stdscr.addstr(0, 0, header[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    row = 3
    for line in NOTIFY_DESCRIPTION:
        if row >= h - 4:
            break
        stdscr.addstr(row, 4, line[:w - 4], curses.A_DIM)
        row += 1

    row += 1
    ntypes = list(NOTIFY_SCRIPTS.keys())
    for i, ntype in enumerate(ntypes):
        if row >= h - 4:
            break
        marker = "x" if states.get(ntype, False) else " "
        label = NOTIFY_LABELS[ntype]
        text = f"[{marker}] {label}"
        attr = curses.A_REVERSE if i == cursor else 0
        stdscr.addstr(row, 4, text[:w - 4], attr)
        row += 1

    # Warning if tool not found (Linux only)
    row += 1
    if row < h - 3 and platform.system() != "Darwin":
        if not _check_command("notify-send"):
            stdscr.addstr(row, 4, "⚠ notify-send not found"[:w - 4], curses.A_DIM)

    footer_row = h - 2
    if footer_row > row + 1:
        stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
    hint = "↑↓ navigate   Enter toggle   ← back   q quit"
    if footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)

    stdscr.refresh()


def _check_command(name: str) -> bool:
    try:
        subprocess.run(["which", name], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def draw_git_cleanup_config(stdscr, enabled: bool) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    header = "  claude-hooks · Hooks › Session Git Cleanup  "
    stdscr.addstr(0, 0, header[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    row = 3
    for line in GIT_CLEANUP_DESCRIPTION:
        if row >= h - 4:
            break
        stdscr.addstr(row, 4, line[:w - 4], curses.A_DIM)
        row += 1

    row += 1
    if row < h - 3:
        marker = "x" if enabled else " "
        text = f"[{marker}] Enabled"
        stdscr.addstr(row, 4, text[:w - 4], curses.A_REVERSE)

    footer_row = h - 2
    if footer_row > row + 1:
        stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
    hint = "Enter toggle   ← back   q quit"
    if footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)

    stdscr.refresh()


def draw_obsidian_instructions(stdscr, scroll: int) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(0, 0, "  claude-hooks · Integrations › Obsidian › Instructions  "[:w], curses.A_BOLD)
        stdscr.addstr(1, 0, "─" * min(w, 60))
    except curses.error:
        pass
    visible = h - 5
    for i, line in enumerate(OBSIDIAN_INSTRUCTIONS[scroll:scroll + visible]):
        try:
            stdscr.addstr(3 + i, 2, line[:w - 2])
        except curses.error:
            pass
    if scroll > 0:
        try:
            stdscr.addstr(2, w - 5, " ↑ ", curses.A_DIM)
        except curses.error:
            pass
    if scroll + visible < len(OBSIDIAN_INSTRUCTIONS):
        try:
            stdscr.addstr(h - 3, w - 5, " ↓ ", curses.A_DIM)
        except curses.error:
            pass
    try:
        stdscr.addstr(h - 2, 2, "↑↓ scroll   ESC / q back"[:w - 2], curses.A_DIM)
    except curses.error:
        pass
    stdscr.refresh()


def draw_obsidian_config(
    stdscr,
    cli_installed: bool,
    integ: dict,
    cursor: int,
    edit_field: str | None,
    edit_buf: str,
    status_msg: str,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(0, 0, "  claude-hooks · Integrations › Obsidian  "[:w], curses.A_BOLD)
        stdscr.addstr(1, 0, "─" * min(w, 60))
    except curses.error:
        pass

    row = 3
    cli_str = "✓ installed" if cli_installed else "✗ not found"
    cli_pair = CURSES_COLOR_MAP.get("green" if cli_installed else "red", 0)
    try:
        stdscr.addstr(row, 2, "obsidian CLI:       "[:w - 2])
        if cli_pair and 22 < w:
            stdscr.addstr(row, 22, cli_str[:w - 22], curses.color_pair(cli_pair))
        elif 22 < w:
            stdscr.addstr(row, 22, cli_str[:w - 22])
    except curses.error:
        pass
    row += 2

    ob = integ.get("obsidian", {})
    label_col = 22
    for idx, (key, label, _required) in enumerate(OBSIDIAN_FIELDS, start=OB_IDX_VAULT_PATH):
        val = ob.get(key, "")
        is_cursor = cursor == idx
        if edit_field == key:
            display = edit_buf + "_"
            val_attr = curses.A_REVERSE
        elif val:
            max_val_w = w - label_col - 2
            display = val if len(val) <= max_val_w else "…" + val[-(max_val_w - 1):]
            val_attr = curses.A_NORMAL
        else:
            display = "(empty)"
            val_attr = curses.A_DIM
        try:
            line_label = f"{label:<20}"
            if is_cursor:
                stdscr.addstr(row, 2, f"> {line_label}"[:w - 2], curses.A_BOLD)
            else:
                stdscr.addstr(row, 2, f"  {line_label}"[:w - 2])
            if label_col < w:
                stdscr.addstr(row, label_col, display[:w - label_col - 1], val_attr)
        except curses.error:
            pass
        row += 1

    row += 1
    actions = [
        (OB_IDX_INSTALL_MCP,  "[Install MCP provider]"),
        (OB_IDX_INSTRUCTIONS, "[View setup instructions]"),
    ]
    for act_idx, act_label in actions:
        is_cursor = cursor == act_idx
        try:
            if is_cursor:
                stdscr.addstr(row, 2, f"> {act_label}"[:w - 2], curses.A_REVERSE)
            else:
                stdscr.addstr(row, 2, f"  {act_label}"[:w - 2])
        except curses.error:
            pass
        row += 1

    footer_row = h - 2
    if status_msg:
        try:
            stdscr.addstr(footer_row - 1, 2, status_msg[:w - 2], curses.A_BOLD)
        except curses.error:
            pass
    elif footer_row - 1 > row + 1:
        try:
            stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
        except curses.error:
            pass
    try:
        stdscr.addstr(footer_row, 2, "↑↓ navigate   Enter edit/action   ESC back"[:w - 2], curses.A_DIM)
    except curses.error:
        pass
    stdscr.refresh()


def draw_screen(stdscr, title: str, items: list[str], cursor: int, hint: str = "") -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Header
    header = f"  claude-hooks v{VERSION} · {title}  "
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
    elem_scroll: int = 0,
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
    try:
        stdscr.addstr(row, 2, "─" * min(w - 4, 56))
    except curses.error:
        pass
    row += 1

    list_start_row = row

    # Build display list with category headers
    display_items = _build_display_list(elements)
    total_display = len(display_items)

    used_elsewhere: set[str] = set()
    for i, line_elems in enumerate(lines):
        if i != current_line:
            used_elsewhere.update(line_elems)

    cursor_elem = elements[cursor] if elements else ""

    # Scroll up indicator
    if elem_scroll > 0 and list_start_row < h:
        try:
            stdscr.addstr(list_start_row - 1, w - 5, " ↑ ", curses.A_DIM)
        except curses.error:
            pass

    last_visible_di = -1
    for di, item in enumerate(display_items):
        if di < elem_scroll:
            continue
        if row >= h - 4:
            break
        last_visible_di = di

        if item[0] == "header":
            cat_label = f" {item[1]} "
            line_fill = "─" * max(0, min(w - 6, 38) - len(cat_label))
            header_str = f"──{cat_label}{line_fill}"
            try:
                stdscr.addstr(row, 2, header_str[:w - 2], curses.A_DIM)
            except curses.error:
                pass
        else:
            elem = item[1]
            checked = elem in lines[current_line]
            grayed = elem in used_elsewhere
            marker = "[x]" if checked else ("[~]" if grayed else "[ ]")
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
            is_cursor = elem == cursor_elem
            if is_cursor:
                try:
                    stdscr.addstr(row, 2, f"> {label}"[:w - 2], curses.A_REVERSE)
                except curses.error:
                    pass
            elif grayed:
                try:
                    stdscr.addstr(row, 2, f"  {label}"[:w - 2], curses.A_DIM)
                except curses.error:
                    pass
            else:
                attr = curses.color_pair(elem_color) if elem_color else curses.A_NORMAL
                try:
                    stdscr.addstr(row, 2, f"  {label}"[:w - 2], attr)
                except curses.error:
                    pass
        row += 1

    # Scroll down indicator
    if last_visible_di >= 0 and last_visible_di < total_display - 1:
        try:
            stdscr.addstr(row - 1, w - 5, " ↓ ", curses.A_DIM)
        except curses.error:
            pass

    if row < h - 3:
        try:
            stdscr.addstr(row, 2, "─" * min(w - 4, 56))
        except curses.error:
            pass

    footer_row = h - 2
    if status_msg and footer_row < h:
        try:
            stdscr.addstr(footer_row - 1, 2, status_msg[:w - 2], curses.A_BOLD)
        except curses.error:
            pass
    hint = "1-9/Tab/←/→ line   ↑↓ navigate   Enter toggle   c config   s save   q cancel"
    if footer_row < h:
        try:
            stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)
        except curses.error:
            pass

    stdscr.refresh()


def draw_save_confirm(
    stdscr,
    lines: list[list[str]],
    element_settings: dict | None = None,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    title = "claude-hooks · Save Statusline"
    stdscr.addstr(0, 0, f"  {title}  "[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    row = 3
    stdscr.addstr(row, 2, "Preview:"[:w - 2], curses.A_BOLD)
    row += 1

    compacted = [line for line in lines if line]
    if compacted:
        for line_elems in compacted:
            if row >= h - 6:
                break
            col = 4
            stdscr.addstr(row, 2, "│ ")
            for ei, e in enumerate(line_elems):
                if ei > 0:
                    sep = " | "
                    if col + len(sep) < w:
                        stdscr.addstr(row, col, sep)
                    col += len(sep)
                segments = run_element(e, element_settings)
                text_color = (element_settings or {}).get(e, {}).get("color")
                for seg_text, seg_color in segments:
                    color_name = seg_color if seg_color is not None else text_color
                    pair_idx = CURSES_COLOR_MAP.get(color_name or "", 0)
                    attr = curses.color_pair(pair_idx) if pair_idx else curses.A_NORMAL
                    seg_w = display_width(seg_text)
                    if col + seg_w < w:
                        stdscr.addstr(row, col, seg_text, attr)
                    col += seg_w
            row += 1
    else:
        stdscr.addstr(row, 4, "(statusline disabled — all lines empty)"[:w - 4], curses.A_DIM)
        row += 1

    row += 1
    if row < h - 4:
        stdscr.addstr(row, 2, "─" * min(w - 4, 56))

    footer_row = h - 2
    hint = "Save?  [y] yes   [n / Del] cancel"
    if footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2])

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
    mood_set: int = 1,
    pomo_duration: int = 25,
    streak_unit: bool = True,
    moon_name: bool = False,
    cwd_basename: bool = False,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    if element == "model":
        cur_set = MODEL_EMOJI_SETS[emoji_set] if emoji_set in (1, 2) else MODEL_EMOJI_SETS[1]
        emoji_char = " ".join(cur_set.values())
    elif element == "mood":
        emoji_char = " ".join(MOOD_EMOJI_SETS.get(1, []))
    else:
        emoji_char = ELEMENT_EMOJIS.get(element, "")
    label_word = ELEMENT_LABELS.get(element, "")
    title = f"claude-hooks · Element: {element}"
    stdscr.addstr(0, 0, f"  {title}  "[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    row = 3
    emoji_text = f"{'[x]' if emoji_on else '[ ]'} Emoji: {emoji_char}" if emoji_char else "[ ] Emoji: (none available)"
    if cursor == 0:
        stdscr.addstr(row, 2, f"> {emoji_text}"[:w - 2], curses.A_REVERSE)
    else:
        stdscr.addstr(row, 2, f"  {emoji_text}"[:w - 2])
    row += 1

    label_text = f"{'[x]' if label_on else '[ ]'} Label: {label_word}" if label_word else "[ ] Label: (none available)"
    if cursor == 1:
        stdscr.addstr(row, 2, f"> {label_text}"[:w - 2], curses.A_REVERSE)
    else:
        stdscr.addstr(row, 2, f"  {label_text}"[:w - 2])
    row += 2

    stdscr.addstr(row, 2, "Color:"[:w - 2], curses.A_BOLD)
    row += 1

    for i, (cname, _) in enumerate(COLOR_OPTIONS):
        list_idx = i + 2
        marker = "●" if cname == (color_name or "none") else "○"
        label = f"{marker} {cname}"
        if list_idx == cursor:
            stdscr.addstr(row, 2, f"> {label}"[:w - 2], curses.A_REVERSE)
        else:
            stdscr.addstr(row, 2, f"  {label}"[:w - 2])
        row += 1

    extra_start = 2 + len(COLOR_OPTIONS)

    if element == "model" and row < h - 5:
        row += 1
        stdscr.addstr(row, 2, "Emoji set:"[:w - 2], curses.A_BOLD)
        row += 1
        for i, set_map in enumerate(MODEL_EMOJI_SETS[1:], start=1):
            list_idx = extra_start + (i - 1)
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
        for i, opt in enumerate(BAR_OPTIONS):
            list_idx = extra_start + i
            marker = "●" if opt == (bar or "off") else "○"
            opt_label = f"{marker} {opt}"
            if list_idx == cursor:
                stdscr.addstr(row, 2, f"> {opt_label}"[:w - 2], curses.A_REVERSE)
            else:
                stdscr.addstr(row, 2, f"  {opt_label}"[:w - 2])
            row += 1

    if element == "mood" and row < h - 5:
        row += 1
        stdscr.addstr(row, 2, "Emoji set:"[:w - 2], curses.A_BOLD)
        row += 1
        for i, emojis in MOOD_EMOJI_SETS.items():
            list_idx = extra_start + (i - 1)
            marker = "●" if mood_set == i else "○"
            preview = " ".join(emojis)
            opt_label = f"{marker} set {i}  {preview}"
            if list_idx == cursor:
                stdscr.addstr(row, 2, f"> {opt_label}"[:w - 2], curses.A_REVERSE)
            else:
                stdscr.addstr(row, 2, f"  {opt_label}"[:w - 2])
            row += 1

    if element == "pomodoro" and row < h - 5:
        row += 1
        stdscr.addstr(row, 2, "Duration:"[:w - 2], curses.A_BOLD)
        row += 1
        for i, mins in enumerate(POMO_DURATIONS):
            list_idx = extra_start + i
            marker = "●" if pomo_duration == mins else "○"
            opt_label = f"{marker} {mins} min"
            if list_idx == cursor:
                stdscr.addstr(row, 2, f"> {opt_label}"[:w - 2], curses.A_REVERSE)
            else:
                stdscr.addstr(row, 2, f"  {opt_label}"[:w - 2])
            row += 1

    if element == "streak" and row < h - 5:
        row += 1
        list_idx = extra_start
        marker = "[x]" if streak_unit else "[ ]"
        unit_label = f"{marker} Show unit  (e.g. '5 days' vs '5d')"
        if list_idx == cursor:
            stdscr.addstr(row, 2, f"> {unit_label}"[:w - 2], curses.A_REVERSE)
        else:
            stdscr.addstr(row, 2, f"  {unit_label}"[:w - 2])
        row += 1

    if element == "moon-phase" and row < h - 5:
        row += 1
        list_idx = extra_start
        marker = "[x]" if moon_name else "[ ]"
        name_label = f"{marker} Show phase name  (e.g. '🌗 Last Quarter')"
        if list_idx == cursor:
            stdscr.addstr(row, 2, f"> {name_label}"[:w - 2], curses.A_REVERSE)
        else:
            stdscr.addstr(row, 2, f"  {name_label}"[:w - 2])
        row += 1

    if element == "cwd" and row < h - 5:
        row += 1
        list_idx = extra_start
        marker = "[x]" if cwd_basename else "[ ]"
        bn_label = f"{marker} Basename only  (e.g. 'my-project' vs '~/Dev/my-project')"
        if list_idx == cursor:
            stdscr.addstr(row, 2, f"> {bn_label}"[:w - 2], curses.A_REVERSE)
        else:
            stdscr.addstr(row, 2, f"  {bn_label}"[:w - 2])
        row += 1

    footer_row = h - 2
    if footer_row > row + 1:
        stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
    hint = "↑↓ navigate   Enter toggle/select   q back"
    if footer_row < h:
        stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)

    stdscr.refresh()


def draw_statusline_settings(
    stdscr,
    section: int,
    line_cursor: int,
    color_cursor: int,
    current_lines: int,
    default_color: str | None,
    separator_color: str | None,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(0, 0, "  claude-hooks · Statusline Settings  "[:w], curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * min(w, 60))

    # Section tabs
    tab0 = "  [ Number of lines ]  "
    tab1 = "  [ General color ]  "
    row = 3
    try:
        if section == 0:
            stdscr.addstr(row, 2, tab0, curses.A_REVERSE)
            stdscr.addstr(row, 2 + len(tab0), tab1)
        else:
            stdscr.addstr(row, 2, tab0)
            stdscr.addstr(row, 2 + len(tab0), tab1, curses.A_REVERSE)
    except curses.error:
        pass

    row += 1
    try:
        stdscr.addstr(row, 0, "─" * min(w, 60))
    except curses.error:
        pass

    row += 2  # row 6

    if section == 0:
        try:
            stdscr.addstr(row, 2, "Select how many status bar rows to display:"[:w - 2])
        except curses.error:
            pass
        row += 2
        items = ["0 — disabled", "1", "2", "3", "4", "5", "6"]
        for i, item in enumerate(items):
            if row >= h - 3:
                break
            marker = "✓ " if i == current_lines else "  "
            label = f"{marker}{item}"
            try:
                if i == line_cursor:
                    stdscr.addstr(row, 2, f"> {label}"[:w - 2], curses.A_REVERSE)
                else:
                    stdscr.addstr(row, 2, f"  {label}"[:w - 2])
            except curses.error:
                pass
            row += 1
    else:
        try:
            stdscr.addstr(row, 2, "Set fallback colors for elements and separators:"[:w - 2])
        except curses.error:
            pass
        row += 2
        color_rows = [
            ("Default element color:", default_color),
            ("Separator color:      ", separator_color),
        ]
        for i, (label, val) in enumerate(color_rows):
            if row >= h - 4:
                break
            val_str = val or "none"
            line_str = f"{label}  [ {val_str} ]"
            try:
                if i == color_cursor:
                    stdscr.addstr(row, 2, f"> {line_str}"[:w - 2], curses.A_REVERSE)
                else:
                    stdscr.addstr(row, 2, f"  {line_str}"[:w - 2])
            except curses.error:
                pass
            row += 1
        if row < h - 4:
            try:
                stdscr.addstr(row + 1, 2, "(Enter cycles through color options)"[:w - 2], curses.A_DIM)
            except curses.error:
                pass

    footer_row = h - 2
    if footer_row > row + 2:
        try:
            stdscr.addstr(footer_row - 1, 2, "─" * min(w - 4, 56))
        except curses.error:
            pass
    hint = "←→ switch section   ↑↓ navigate   Enter select   ESC back   q quit"
    if footer_row < h:
        try:
            stdscr.addstr(footer_row, 2, hint[:w - 2], curses.A_DIM)
        except curses.error:
            pass

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
    sl_elem_scroll: int = 0

    # Element config state
    ec_elem: str = ""
    ec_emoji_on: bool = False
    ec_label_on: bool = False
    ec_color: str | None = None
    ec_bar: str = "off"
    ec_model_set: int = 1
    ec_mood_set: int = 1
    ec_pomo_duration: int = 25
    ec_streak_unit: bool = True
    ec_moon_name: bool = False
    ec_cwd_basename: bool = False
    ec_cursor: int = 0

    # Statusline settings screen state
    sl_settings_section: int = 0      # 0 = Number of lines, 1 = General color
    sl_settings_color_cursor: int = 0  # 0 = default_color, 1 = separator_color

    # Obsidian integration state
    ob_cli_installed: bool = False
    ob_cursor: int = OB_IDX_VAULT_PATH
    ob_edit_field: str | None = None
    ob_edit_buf: str = ""
    ob_edit_orig: str = ""
    ob_status_msg: str = ""
    ob_integ: dict = {}
    ob_instr_scroll: int = 0

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
            gc_status = "enabled" if is_git_cleanup_enabled() else "disabled"
            items.append(f"{'Session Git Cleanup':<22} [{gc_status}]")
            nf_states = get_notify_states()
            nf_count = sum(nf_states.values())
            notify_status = f"{nf_count}/{len(nf_states)}" if nf_count else "disabled"
            items.append(f"{'Notifications':<22} [{notify_status}]")
            hint = "↑↓ navigate   Enter select   ← back   q quit"

        elif screen.startswith("sound_picker:"):
            event = screen.split(":", 1)[1]
            title = f"Hooks › {EVENT_LABELS[event]}"
            sounds = list_sounds(EVENT_DIRS[event])
            current = cfg["sounds"].get(event) or "(none)"
            items = [f"{s} ✓" if s == current else s for s in sounds]
            hint = "↑↓ navigate + preview   Enter confirm   ← back   q quit"

        elif screen == "statusline_editor":
            draw_statusline_editor(
                stdscr, sl_lines, sl_current_line, sl_elem_cursor, sl_elements, sl_status_msg,
                cfg.get("statusline", {}).get("element_settings"),
                sl_elem_scroll,
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
                _h, _ = stdscr.getmaxyx()
                _avail = _h - (6 + len(sl_lines)) - 5
                sl_elem_scroll = _clamp_elem_scroll(sl_elem_scroll, sl_elem_cursor, sl_elements, max(1, _avail))

            elif key in (curses.KEY_DOWN, ord("j")):
                sl_elem_cursor = min(len(sl_elements) - 1, sl_elem_cursor + 1)
                sl_status_msg = ""
                _h, _ = stdscr.getmaxyx()
                _avail = _h - (6 + len(sl_lines)) - 5
                sl_elem_scroll = _clamp_elem_scroll(sl_elem_scroll, sl_elem_cursor, sl_elements, max(1, _avail))

            elif key in (curses.KEY_LEFT, ord("h"), curses.KEY_BTAB):
                sl_current_line = max(0, sl_current_line - 1)
                sl_elem_cursor = 0
                sl_elem_scroll = 0
                sl_status_msg = ""

            elif key in (curses.KEY_RIGHT, ord("l"), ord("\t")):  # Tab = next line
                sl_current_line = min(len(sl_lines) - 1, sl_current_line + 1)
                sl_elem_cursor = 0
                sl_elem_scroll = 0
                sl_status_msg = ""

            elif ord("1") <= key <= ord("9"):
                n = key - ord("1")  # key "1" → index 0
                if n < len(sl_lines):
                    sl_current_line = n
                    sl_elem_cursor = 0
                    sl_elem_scroll = 0
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
                raw_mood = settings.get("mood_set", 1)
                ec_mood_set = raw_mood if isinstance(raw_mood, int) and raw_mood in MOOD_EMOJI_SETS else 1
                raw_dur = settings.get("duration", 25)
                ec_pomo_duration = raw_dur if raw_dur in POMO_DURATIONS else 25
                ec_streak_unit = settings.get("show_unit", True)
                ec_moon_name = settings.get("show_name", False)
                ec_cwd_basename = settings.get("basename_only", False)
                ec_cursor = 0
                stack.append((screen, cursor))
                screen = "element_config"
                cursor = 0

            elif key == ord("s"):
                stack.append((screen, cursor))
                screen = "statusline_save_confirm"

            elif key == ord("q"):
                if stack:
                    screen, cursor = stack.pop()

            continue

        elif screen == "statusline_save_confirm":
            draw_save_confirm(
                stdscr, sl_lines,
                cfg.get("statusline", {}).get("element_settings"),
            )
            key = stdscr.getch()
            if key in (ord("y"), ord("Y")):
                compacted = [line for line in sl_lines if line]
                cfg.setdefault("statusline", {})["lines"] = compacted
                cfg["statusline"].pop("elements", None)
                save_config(cfg)
                stack.clear()
                screen = "main"
                cursor = 0
            elif key in (ord("n"), ord("N"), curses.KEY_BACKSPACE, 127, curses.KEY_DC, 27, ord("q")):
                if stack:
                    screen, cursor = stack.pop()
            continue

        elif screen == "element_config":
            draw_element_config(stdscr, ec_elem, ec_emoji_on, ec_label_on, ec_color, ec_cursor, ec_bar, ec_model_set, ec_mood_set, ec_pomo_duration, ec_streak_unit, ec_moon_name, ec_cwd_basename)
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

            extra_start = 2 + len(COLOR_OPTIONS)
            max_idx = extra_start - 1
            if ec_elem == "model":
                max_idx = extra_start + len(MODEL_EMOJI_SETS) - 2
            elif ec_elem in BAR_ELEMENTS:
                max_idx = extra_start + len(BAR_OPTIONS) - 1
            elif ec_elem == "mood":
                max_idx = extra_start + len(MOOD_EMOJI_SETS) - 1
            elif ec_elem == "pomodoro":
                max_idx = extra_start + len(POMO_DURATIONS) - 1
            elif ec_elem in ("streak", "moon-phase", "cwd"):
                max_idx = extra_start
            if key in (curses.KEY_UP, ord("k")):
                ec_cursor = max(0, ec_cursor - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                ec_cursor = min(max_idx, ec_cursor + 1)
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                _extra = 2 + len(COLOR_OPTIONS)
                if ec_cursor == 0:
                    ec_emoji_on = not ec_emoji_on
                elif ec_cursor == 1:
                    ec_label_on = not ec_label_on
                elif ec_cursor >= _extra:
                    idx = ec_cursor - _extra
                    if ec_elem == "model":
                        ec_model_set = idx + 1
                    elif ec_elem in BAR_ELEMENTS:
                        ec_bar = BAR_OPTIONS[idx]
                    elif ec_elem == "mood":
                        ec_mood_set = idx + 1
                    elif ec_elem == "pomodoro":
                        ec_pomo_duration = POMO_DURATIONS[idx]
                    elif ec_elem == "streak":
                        ec_streak_unit = not ec_streak_unit
                    elif ec_elem == "moon-phase":
                        ec_moon_name = not ec_moon_name
                    elif ec_elem == "cwd":
                        ec_cwd_basename = not ec_cwd_basename
                else:
                    cname, _ = COLOR_OPTIONS[ec_cursor - 2]
                    ec_color = None if cname == "none" else cname
                # Save immediately
                sl_settings = cfg.setdefault("statusline", {}).setdefault("element_settings", {})
                entry = {"emoji": ec_emoji_on, "label": ec_label_on, "color": ec_color, "bar": ec_bar}
                if ec_elem == "model":
                    entry["emoji_set"] = ec_model_set
                if ec_elem == "mood":
                    entry["mood_set"] = ec_mood_set
                if ec_elem == "pomodoro":
                    entry["duration"] = ec_pomo_duration
                if ec_elem == "streak":
                    entry["show_unit"] = ec_streak_unit
                if ec_elem == "moon-phase":
                    entry["show_name"] = ec_moon_name
                if ec_elem == "cwd":
                    entry["basename_only"] = ec_cwd_basename
                sl_settings[ec_elem] = entry
                save_config(cfg)
                clear_element_cache()
            elif key in (ord("q"), curses.KEY_LEFT, ord("h"), 27):
                if stack:
                    screen, cursor = stack.pop()

            continue

        elif screen == "statusline_lines":
            _sl_cfg = cfg.get("statusline", {})
            _cur_lines = len(_sl_cfg.get("lines") or [])
            draw_statusline_settings(
                stdscr,
                sl_settings_section,
                cursor,
                sl_settings_color_cursor,
                _cur_lines,
                _sl_cfg.get("default_color"),
                _sl_cfg.get("separator_color"),
            )
            key = stdscr.getch()

            # ESC sequence decoding
            _bare_esc = False
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
                else:
                    _bare_esc = True

            if _bare_esc or key == ord("q"):
                if stack:
                    screen, cursor = stack.pop()
                sl_settings_section = 0
                sl_settings_color_cursor = 0
            elif key in (curses.KEY_LEFT,):
                sl_settings_section = (sl_settings_section - 1) % 2
            elif key in (curses.KEY_RIGHT,):
                sl_settings_section = (sl_settings_section + 1) % 2
            elif key in (curses.KEY_UP, ord("k")):
                if sl_settings_section == 0:
                    cursor = max(0, cursor - 1)
                else:
                    sl_settings_color_cursor = max(0, sl_settings_color_cursor - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                if sl_settings_section == 0:
                    cursor = min(6, cursor + 1)
                else:
                    sl_settings_color_cursor = min(1, sl_settings_color_cursor + 1)
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                if sl_settings_section == 0:
                    n = cursor  # 0 = disabled, 1–6 = line count
                    if n == 0:
                        cfg.setdefault("statusline", {})["lines"] = []
                        cfg["statusline"].pop("elements", None)
                        save_config(cfg)
                        if stack:
                            screen, cursor = stack.pop()
                        sl_settings_section = 0
                        sl_settings_color_cursor = 0
                    else:
                        sl_data = cfg.get("statusline", {})
                        existing = sl_data.get("lines")
                        if existing is None:
                            elems = sl_data.get("elements", [])
                            existing = [elems] if elems else []
                        sl_lines = [list(existing[i]) if i < len(existing) else [] for i in range(n)]
                        sl_current_line = 0
                        for idx, ln in enumerate(sl_lines):
                            if not ln:
                                sl_current_line = idx
                                break
                        sl_elem_cursor = 0
                        sl_elem_scroll = 0
                        sl_elements = [
                            item[1] for item in _build_display_list(list_elements())
                            if item[0] == "element"
                        ]
                        sl_status_msg = ""
                        stack.append((screen, cursor))
                        screen = "statusline_editor"
                        cursor = 0
                else:
                    # Cycle color for focused row
                    sl_cfg = cfg.setdefault("statusline", {})
                    key_name = "default_color" if sl_settings_color_cursor == 0 else "separator_color"
                    cur_val = sl_cfg.get(key_name)
                    cur_names = [c[0] for c in COLOR_OPTIONS]
                    cur_name = cur_val or "none"
                    try:
                        idx = cur_names.index(cur_name)
                    except ValueError:
                        idx = 0
                    next_name, _ = COLOR_OPTIONS[(idx + 1) % len(COLOR_OPTIONS)]
                    sl_cfg[key_name] = None if next_name == "none" else next_name
                    save_config(cfg)

            continue

        elif screen == "obsidian_config":
            draw_obsidian_config(stdscr, ob_cli_installed, ob_integ, ob_cursor, ob_edit_field, ob_edit_buf, ob_status_msg)
            key = stdscr.getch()

            # ESC sequence decoding
            _bare_esc = False
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
                else:
                    _bare_esc = True

            if ob_edit_field is not None:
                # Text input mode
                if key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                    ob_integ.setdefault("obsidian", {})[ob_edit_field] = ob_edit_buf
                    save_integrations(ob_integ)
                    ob_status_msg = "Saved"
                    ob_edit_field = None
                    ob_edit_buf = ""
                elif _bare_esc:
                    ob_integ.setdefault("obsidian", {})[ob_edit_field] = ob_edit_orig
                    ob_edit_field = None
                    ob_edit_buf = ""
                    ob_status_msg = ""
                elif key in (127, curses.KEY_BACKSPACE):
                    ob_edit_buf = ob_edit_buf[:-1]
                elif 32 <= key <= 126:
                    ob_edit_buf += chr(key)
            else:
                # Navigation mode
                if _bare_esc or key == ord("q"):
                    if stack:
                        screen, cursor = stack.pop()
                elif key in (curses.KEY_UP, ord("k")):
                    ob_cursor = max(OB_IDX_VAULT_PATH, ob_cursor - 1)
                    ob_status_msg = ""
                elif key in (curses.KEY_DOWN, ord("j")):
                    ob_cursor = min(OB_IDX_INSTRUCTIONS, ob_cursor + 1)
                    ob_status_msg = ""
                elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                    if OB_IDX_VAULT_PATH <= ob_cursor <= OB_IDX_DAILY_FOLDER:
                        field_key = OBSIDIAN_FIELDS[ob_cursor - OB_IDX_VAULT_PATH][0]
                        ob_edit_field = field_key
                        ob_edit_buf = ob_integ.get("obsidian", {}).get(field_key, "")
                        ob_edit_orig = ob_edit_buf
                        ob_status_msg = ""
                    elif ob_cursor == OB_IDX_INSTALL_MCP:
                        ob_status_msg = "Installing…"
                        draw_obsidian_config(stdscr, ob_cli_installed, ob_integ, ob_cursor, None, "", ob_status_msg)
                        success, msg = run_mcp_install()
                        ob_status_msg = msg
                    elif ob_cursor == OB_IDX_INSTRUCTIONS:
                        ob_instr_scroll = 0
                        stack.append((screen, cursor))
                        screen = "obsidian_instructions"
                        cursor = 0

            continue

        elif screen == "obsidian_instructions":
            draw_obsidian_instructions(stdscr, ob_instr_scroll)
            key = stdscr.getch()

            _bare_esc = False
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
                else:
                    _bare_esc = True

            max_scroll = max(0, len(OBSIDIAN_INSTRUCTIONS) - (stdscr.getmaxyx()[0] - 5))
            if key in (curses.KEY_UP, ord("k")):
                ob_instr_scroll = max(0, ob_instr_scroll - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                ob_instr_scroll = min(max_scroll, ob_instr_scroll + 1)
            elif _bare_esc or key == ord("q"):
                if stack:
                    screen, cursor = stack.pop()

            continue

        elif screen == "git_cleanup_config":
            gc_enabled = is_git_cleanup_enabled()
            draw_git_cleanup_config(stdscr, gc_enabled)
            key = stdscr.getch()

            _bare_esc = False
            if key == 27:
                stdscr.nodelay(True)
                k2 = stdscr.getch()
                k3 = stdscr.getch()
                stdscr.nodelay(False)
                if k2 == ord("["):
                    if k3 == ord("D"):
                        key = curses.KEY_LEFT
                else:
                    _bare_esc = True

            if key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                toggle_git_cleanup(not gc_enabled)
            elif _bare_esc or key in (ord("q"), curses.KEY_LEFT):
                if stack:
                    screen, cursor = stack.pop()

            continue

        elif screen == "notify_config":
            nf_states = get_notify_states()
            ntypes = list(NOTIFY_SCRIPTS.keys())
            n_items = len(ntypes)
            draw_notify_config(stdscr, nf_states, cursor)
            key = stdscr.getch()

            _bare_esc = False
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
                else:
                    _bare_esc = True

            if key == curses.KEY_UP:
                cursor = (cursor - 1) % n_items
            elif key == curses.KEY_DOWN:
                cursor = (cursor + 1) % n_items
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                ntype = ntypes[cursor]
                toggle_notify_type(ntype, not nf_states[ntype])
            elif _bare_esc or key in (ord("q"), curses.KEY_LEFT):
                if stack:
                    screen, cursor = stack.pop()

            continue

        elif screen == "integrations":
            title = "Integrations"
            items = ["Obsidian"]
            hint = "↑↓ navigate   Enter select   ESC back   q quit"

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
                elif choice == "Integrations":
                    stack.append((screen, cursor))
                    screen = "integrations"
                    cursor = 0
                else:
                    stack.append((screen, cursor))
                    screen = "statusline_lines"
                    cursor = 0
                    sl_settings_section = 0
                    sl_settings_color_cursor = 0

            elif screen == "integrations":
                # Only one item: Obsidian
                ob_integ = load_integrations()
                ob_cli_installed = check_obsidian_cli()
                ob_cursor = OB_IDX_VAULT_PATH
                ob_edit_field = None
                ob_edit_buf = ""
                ob_status_msg = ""
                stack.append((screen, cursor))
                screen = "obsidian_config"
                cursor = 0

            elif screen == "hooks":
                if cursor < len(HOOKS_ITEMS):
                    event = HOOKS_ITEMS[cursor]
                    stack.append((screen, cursor))
                    screen = f"sound_picker:{event}"
                    sounds = list_sounds(EVENT_DIRS[event])
                    current = cfg["sounds"].get(event) or "(none)"
                    try:
                        cursor = sounds.index(current)
                    except ValueError:
                        cursor = 0
                elif cursor == len(HOOKS_ITEMS):
                    # Session Git Cleanup item
                    stack.append((screen, cursor))
                    screen = "git_cleanup_config"
                    cursor = 0
                elif cursor == len(HOOKS_ITEMS) + 1:
                    # Notifications item
                    stack.append((screen, cursor))
                    screen = "notify_config"
                    cursor = 0

            elif screen.startswith("sound_picker:"):
                event = screen.split(":", 1)[1]
                chosen = sounds[cursor]
                cfg["sounds"][event] = None if chosen == "(none)" else chosen
                save_config(cfg)
                if stack:
                    screen, cursor = stack.pop()

            else:
                if stack:
                    screen, cursor = stack.pop()


def main() -> None:
    curses.wrapper(run)


if __name__ == "__main__":
    main()
