# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A customization suite for Claude Code that provides:
- A modular statusline with 18+ elements displayed in Claude Code's status bar
- Sound hooks for tool errors, stops, and notifications
- An interactive TUI configurator (`configure.py`) for visual customization

## Common Commands

```bash
# Install (patches ~/.claude/settings.json and makes scripts executable)
bash install.sh

# Launch interactive TUI configurator
bash configure.sh
```

No build step, no tests, no linter.

## Architecture

### Configuration: `config.json`
Single source of truth. Two sections:
- `statusline.lines`: 2D array of element names defining layout (up to 6 rows)
- `statusline.element_settings`: Per-element options (`emoji`, `label`, `color`, `bar`, plus element-specific keys like `emoji_set`, `duration`, `show_unit`)
- `sounds`: Maps event names (`on_error`, `on_stop`, `on_notification`) to filenames in `sounds/error/` or `sounds/notification/`

### Statusline: `statusline/statusline.sh`
The rendering engine called by Claude Code on every status bar update:
1. A Python subprocess reads `config.json` and emits tab-separated directives (`element|prefix|color|bar_mode|bar_rule`)
2. The shell loop executes each element script (e.g., `statusline/elements/battery.sh`)
3. Applies emoji, labels, colors (ANSI), and progress bars (8-char `█`/`░` blocks)
4. Joins elements with ` | ` and outputs one line per configured row

### Element Scripts: `statusline/elements/*.sh`
Each is a standalone bash script that prints one value to stdout. Elements that need session data (model, context-pct, streak, burn-rate, session-cost) read `~/.claude/projects/**/*.jsonl` via inline Python. Battery uses `pmset` on macOS, `/sys/class/power_supply` on Linux.

To add a new element: create a `.sh` file in `statusline/elements/`, make it executable, then add it to `config.json` lines.

### Sound Hooks: `hooks/sounds.sh`
Called by Claude Code on `PostToolUse`, `Stop`, and `Notification` events. Reads JSON input from stdin, determines event type, looks up sound filename from `config.json`, and plays it in the background (`afplay` on macOS, `paplay`/`aplay` on Linux).

### TUI Configurator: `configure.py`
~1100-line Python `curses` app. Reads and writes `config.json` directly. Supports live statusline preview by shelling out to `statusline.sh`. Arrow keys are decoded manually (ESC sequence fallback) for compatibility.

### Integration: `install.sh`
Patches `~/.claude/settings.json` to register:
- `statusLine`: points to `statusline/statusline.sh`
- Hooks: `PostToolUse`, `Stop`, `Notification` → `hooks/sounds.sh`

## Key Constants & Paths

- Context window hard-coded to `200_000` tokens in `context-pct.sh`
- Burn rate cache: `/tmp/claude_burn_cache_<uid>`
- Session data: `~/.claude/projects/**/*.jsonl`
- Colors: `green`, `red`, `orange`, `cyan`, `yellow`, `light gray`, `dark gray` (mapped to ANSI in `statusline.sh`)
- Bar modes: `off`, `mono`, `multi`
