#!/usr/bin/env python3
"""Interactive TUI configurator for claude-hooks."""

import curses
import json
import platform
import subprocess
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


def list_elements() -> list[str]:
    d = REPO_DIR / "statusline/elements"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.sh"))


def run_element(name: str) -> str:
    script = REPO_DIR / "statusline/elements" / f"{name}.sh"
    try:
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=2)
        return r.stdout.strip() or name
    except Exception:
        return name


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
        if line_elems:
            preview = " | ".join(run_element(e) for e in line_elems)
        else:
            preview = "(empty)"
        if i == current_line:
            # Highlight the line currently being edited
            label = f"> Line {i + 1}:  {preview}"
            stdscr.addstr(row, 2, label[:w - 2], curses.A_BOLD)
        else:
            label = f"  Line {i + 1}:  {preview}"
            stdscr.addstr(row, 2, label[:w - 2])
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
        label = f"{marker} {elem}"
        if grayed:
            label += "  ← used on another line"
        if i == cursor:
            stdscr.addstr(row, 2, f"> {label}"[:w - 2], curses.A_REVERSE)
        else:
            attr = curses.A_DIM if grayed else curses.A_NORMAL
            stdscr.addstr(row, 2, f"  {label}"[:w - 2], attr)
        row += 1

    row += 1
    if row < h - 3:
        stdscr.addstr(row, 2, "─" * min(w - 4, 56))

    footer_row = h - 2
    if status_msg and footer_row < h:
        stdscr.addstr(footer_row - 1, 2, status_msg[:w - 2], curses.A_BOLD)
    hint = "1-9/Tab/←/→ line   ↑↓ navigate   Enter toggle   s save   q cancel"
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
                stdscr, sl_lines, sl_current_line, sl_elem_cursor, sl_elements, sl_status_msg
            )
            key = stdscr.getch()

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
                    sl_current_line = 0
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
