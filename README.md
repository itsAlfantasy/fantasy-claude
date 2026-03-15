# fantasy-claude

Statusline and sound hooks for [Claude Code](https://claude.ai/code).

---

<!-- screenshot: full statusline in action, ideally 2-3 rows visible in Claude Code's status bar -->

---

## Features

- **Modular statusline** — pick from 18+ elements and arrange them in up to 6 rows. Each element is independently styled with colors, emoji, labels, and progress bars.
- **Sound hooks** — plays sounds when Claude errors, stops, or sends a notification. Sounds are bundled — nothing to download.
- **Interactive TUI configurator** — a terminal UI for changing layout and settings visually, with a live statusline preview.

## Install

Install via npm, then restart Claude Code:

```
npx fantasy-claude install
```

## Configure

Open the TUI configurator with:

```
npx fantasy-claude
```

Navigate with arrow keys, confirm with Enter, go back with ←, quit with q.

---

<!-- screenshot: TUI configurator main screen, showing element list and preview -->

---

## Statusline

The statusline is composed of **rows** (up to 6), each containing any number of **elements** separated by `|`. You choose which elements appear in which row and in what order.

---

<!-- screenshot: example of a 3-row statusline layout -->

---

### Available elements

| Element | Description |
|---|---|
| `model` | Active Claude model |
| `context-pct` | Context window usage, with optional color-coded progress bar |
| `burn-rate` | Token burn rate for the current session |
| `session-cost` | Estimated cost of the current session in USD |
| `session-duration` | Time elapsed since the session started |
| `usage-5h` | Token usage over the last 5 hours |
| `reset-time` | Countdown to the next usage reset |
| `streak` | How many consecutive days Claude Code has been used |
| `cwd` | Current working directory (full path or basename only) |
| `git-branch` | Current git branch |
| `github-repo` | GitHub repository name |
| `battery` | Battery level, with optional progress bar |
| `datetime` | Current time |
| `pomodoro` | Pomodoro timer with configurable interval |
| `file-entropy` | Entropy score of files currently in scope |
| `moon-phase` | Current moon phase, with optional phase name |
| `mood` | A mood indicator |
| `haiku` | A haiku |

### Per-element styling

Every element supports:

- **Emoji** — a leading emoji that varies by value or state
- **Label** — a text label prefix
- **Color** — one of: `green`, `red`, `orange`, `cyan`, `yellow`, `light gray`, `dark gray`
- **Progress bar** — `mono` (single color) or `multi` (color shifts with value), or `off`

Some elements have additional settings — for example, `cwd` can show only the folder name, `pomodoro` has a configurable duration, and `model` supports multiple emoji sets.

### Custom elements

Any shell script placed in `statusline/elements/` that prints a single line becomes a usable element — no reinstall needed, just add it to the layout in the configurator or in `config.json`.

## Sounds

A sound can be assigned to each of these events:

| Event | When it fires |
|---|---|
| `on_error` | A tool call returns an error |
| `on_stop` | Claude finishes a response |
| `on_notification` | Claude sends a notification |

Sounds are configured via the TUI or `config.json`. Any `.mp3` placed in the `sounds/` directory can be used. Set an event to `null` to silence it.

Playback uses `afplay` on macOS and `paplay`/`aplay` on Linux.

## License

MIT
