# fantasy-claude

Statusline and sound hooks for [Claude Code](https://claude.ai/code).

## Features

- **Modular statusline** — compose your status bar from 18+ elements across up to 6 rows
- **Sound hooks** — play sounds on tool errors, stops, and notifications (bundled, no downloads)
- **Interactive TUI configurator** — visual setup with live preview, no JSON editing required

## Install

**via npm (recommended):**

```bash
npx fantasy-claude install
```

**manual:**

```bash
git clone https://github.com/itsAlfantasy/fantasy-claude.git
cd fantasy-claude
bash install.sh
```

Then restart Claude Code.

## Configure

Launch the interactive TUI:

```bash
bash configure.sh
```

Use `↑↓` to navigate, `Enter` to select, `←` to go back, `q` to quit. Changes are written to `config.json` immediately.

## Statusline elements

| Element | Description |
|---|---|
| `model` | Active Claude model |
| `context-pct` | Context window usage % |
| `burn-rate` | Token burn rate |
| `session-cost` | Session cost in USD |
| `session-duration` | Time since session start |
| `usage-5h` | Token usage over last 5h |
| `reset-time` | Time until usage resets |
| `streak` | Daily usage streak |
| `cwd` | Current working directory |
| `git-branch` | Current git branch |
| `github-repo` | GitHub repo name |
| `battery` | Battery level |
| `datetime` | Current time |
| `pomodoro` | Pomodoro timer |
| `file-entropy` | Entropy of files in scope |
| `moon-phase` | Current moon phase |
| `mood` | Mood indicator |
| `haiku` | A haiku |

### Layout

`config.json` controls which elements appear and in what order. Elements are arranged in rows (`lines`):

```json
{
  "statusline": {
    "lines": [
      ["model", "cwd", "git-branch"],
      ["context-pct", "burn-rate", "session-cost"],
      ["streak", "usage-5h", "reset-time"]
    ]
  }
}
```

Up to 6 rows supported. Elements within a row are joined with ` | `.

### Per-element options

Each element can be customized in `element_settings`:

| Option | Values | Description |
|---|---|---|
| `emoji` | `true` / `false` | Show leading emoji |
| `label` | `true` / `false` | Show element label |
| `color` | `green` `red` `orange` `cyan` `yellow` `light gray` `dark gray` `null` | Text color |
| `bar` | `off` `mono` `multi` | Progress bar style |

Some elements have additional options:

- `cwd`: `basename_only` — show only the last path component
- `model`: `emoji_set` — which emoji set to use (1 or 2)
- `streak`: `show_unit` — append "days"
- `pomodoro`: `duration` — interval in minutes
- `moon-phase`: `show_name` — show phase name alongside emoji
- `mood`: `mood_set` — which mood set to use

### Custom elements

Create `statusline/elements/<name>.sh` that prints a single line to stdout, then add `<name>` to a row in `config.json`. No reinstall needed.

## Sounds

Sound events:

| Event | Trigger |
|---|---|
| `on_error` | A tool call returns an error |
| `on_stop` | Claude finishes a response |
| `on_notification` | Claude sends a notification |

Configure in `config.json`:

```json
{
  "sounds": {
    "on_error": "lego-break",
    "on_stop": null,
    "on_notification": null
  }
}
```

Set to `null` to disable. Custom sounds: place `.mp3` files in `sounds/error/` or `sounds/notification/` and reference by filename without extension.

**Platform support:** `afplay` on macOS, `paplay`/`aplay` on Linux.

## License

MIT
