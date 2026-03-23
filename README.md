# fantasy-claude

Configurable statusline and sound hooks for [Claude Code](https://claude.ai/code).

## Features

- **Statusline**: compose your status bar from 18 modular elements across up to 6 rows — git branch, context usage, burn rate, battery, and more
- **Sound hooks**: play sounds on tool errors, stop, or notifications — ships with example sounds, add your own `.mp3` files
- **Notification hooks**: desktop notifications when Claude needs input — permission prompts, idle, questions
- **TUI configurator**: interactive terminal UI for visual customization — no JSON editing required
- **Integrations**: Obsidian vault integration via the TUI configurator

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| Bash | 3.0+ |
| Git | any |

## Platform support

| Platform | Status | Notes |
|---|---|---|
| macOS | Full support | Audio via `afplay`, battery via `pmset`, notifications via iTerm2 OSC 9 |
| Linux | Full support | Audio via `paplay` or `aplay`, battery via `/sys/class/power_supply`, notifications via `notify-send` |
| Windows | Not supported | — |

## Install

### Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/itsAlfantasy/fantasy-claude/main/install-remote.sh | bash
```

This clones the repo to `~/.fantasy-claude` and runs the installer.

### Manual install

```bash
git clone https://github.com/itsAlfantasy/fantasy-claude.git
cd fantasy-claude
bash install.sh
```

Then restart Claude Code.

`install.sh` detects your Python 3.10+ binary, makes scripts executable, and patches `~/.claude/settings.json` to register the statusline and sound hooks. It creates a symlink at `~/.claude/fantasy-claude` pointing to the repo, so you can move the repo later and just re-run install.

## Uninstall

```bash
bash uninstall.sh
```

Removes hook entries from `~/.claude/settings.json`, removes the symlink at `~/.claude/fantasy-claude`, and cleans up the Python cache. Does not delete the repo.

## Configuration

### Interactive configurator

```bash
bash configure.sh
```

Use `↑↓` to navigate, `Enter` to select, `←` to go back, `q` to quit.
Changes are written to `config.json` immediately on confirmation.

### Manual config

Edit `config.json` directly. The schema has two top-level sections:

```json
{
  "statusline": {
    "lines": [
      ["model", "cwd", "git-branch"],
      ["context-pct", "session-cost", "battery"]
    ],
    "element_settings": {
      "battery": { "emoji": true, "label": false, "color": "green", "bar": "multi" }
    }
  },
  "sounds": {
    "on_error": "lego-break",
    "on_stop": null,
    "on_notification": null
  }
}
```

- `statusline.lines`: 2D array of element names (up to 6 rows, up to 4 elements per row)
- `statusline.element_settings`: per-element options — `emoji`, `label`, `color`, `bar`, plus element-specific keys (`emoji_set`, `duration`, `show_unit`, `show_name`, `basename_only`)
- `sounds`: maps event names to filenames (without `.mp3` extension) in `sounds/error/` or `sounds/notification/`

### CLI

`cli.sh` is a unified entry point for all operations:

```
fantasy-claude install      # install into Claude Code
fantasy-claude uninstall    # remove from Claude Code
fantasy-claude configure    # launch TUI configurator (default)
fantasy-claude --version
fantasy-claude --help
```

All scripts (`install.sh`, `uninstall.sh`, `configure.sh`) also support `--help` and `--version` individually.

## Statusline elements

| Element | Description |
|---|---|
| `model` | Active Claude model name |
| `context-pct` | Context window usage percentage |
| `burn-rate` | Token burn rate (tokens/min) |
| `session-cost` | Cumulative session cost in USD |
| `session-duration` | Time since session started |
| `file-entropy` | Number of files changed in the session |
| `streak` | Consecutive days of Claude Code usage |
| `git-branch` | Current git branch |
| `cwd` | Current working directory |
| `github-repo` | GitHub repository name |
| `battery` | Battery percentage |
| `datetime` | Current time (HH:MM) |
| `usage-5h` | API usage in the last 5 hours |
| `reset-time` | Time until rate limit reset |
| `mood` | Time-of-day mood emoji |
| `moon-phase` | Current lunar phase |
| `haiku` | Random haiku |
| `pomodoro` | Pomodoro timer |

To add a custom element: create a script in `statusline/elements/<name>.sh` that prints a single line to stdout, make it executable, then add `<name>` to a `lines` array in `config.json`.

## Sound hooks

Ships with example sounds (`lego-break.mp3`, `FFAAAAH.mp3` in `sounds/error/`). Add your own `.mp3` files to:
- `sounds/error/` — for `on_error`
- `sounds/notification/` — for `on_stop` and `on_notification`

Set the filename (without extension) in `config.json`. Set to `null` to disable.

| Event | When |
|---|---|
| `on_error` | A tool call returns an error |
| `on_stop` | Claude finishes a response |
| `on_notification` | Claude sends a notification |

## Notification hooks

Desktop notifications for when Claude needs your attention. Five scripts in `hooks/`:

| Script | Triggers on |
|---|---|
| `notify.sh` | All notification types (universal handler) |
| `notify-permission.sh` | Permission prompts only |
| `notify-idle.sh` | Idle/input prompts only |
| `notify-elicitation.sh` | Questions/dialogs only |
| `notify-auth.sh` | Auth success only |

**Platform support**: iTerm2 OSC 9 on macOS, `notify-send` on Linux.

These are **not** auto-registered by `install.sh`. Add them manually via Claude Code settings or the TUI configurator, depending on which notification types you want.

## Integrations

The TUI configurator includes an **Integrations** screen for setting up external tool connections.

### Obsidian

Configure your Obsidian vault for use with Claude Code:
- **Vault path** — path to your Obsidian vault
- **Default folder** — where new notes are created
- **Templates folder** — folder containing note templates
- **Daily notes folder** — folder for daily notes

The TUI can install the **Obsidian Local REST API** MCP server directly.

**Requirements**: [`obsidian-cli`](https://github.com/Yakitrak/obsidian-cli) and the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) community plugin enabled in Obsidian.

## OS-specific dependencies

| Command | Platform | Used by |
|---|---|---|
| `afplay` | macOS | Sound playback |
| `paplay` / `aplay` | Linux | Sound playback (`pulseaudio-utils` or `alsa-utils`) |
| `pmset` | macOS | Battery element |
| `/sys/class/power_supply` | Linux | Battery element |
| `notify-send` | Linux | Notification hooks (`libnotify`) |

## License

MIT
