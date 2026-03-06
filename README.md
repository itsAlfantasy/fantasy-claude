# claude-hooks

Configurable statusline and sound hooks for [Claude Code](https://claude.ai/code).

## Features

- **Statusline**: compose your status bar with modular elements (git branch, cwd, time, battery, …)
- **Sound hooks**: play sounds on tool errors, stop, or notifications — sounds are bundled, no downloads needed

## Install

```bash
git clone https://github.com/yourusername/claude-hooks.git
cd claude-hooks
bash install.sh
```

Then restart Claude Code.

## Configuration

Edit `config.json` to customize:

```json
{
  "statusline": {
    "elements": ["git-branch", "cwd", "datetime"]
  },
  "sounds": {
    "on_error": "lego-break",
    "on_stop": null,
    "on_notification": null
  }
}
```

### Statusline elements

| Element | Description |
|---|---|
| `git-branch` | Current git branch |
| `cwd` | Current working directory |
| `datetime` | Current time (HH:MM) |
| `battery` | Battery percentage |

To add a custom element, create a script in `statusline/elements/<name>.sh` that prints a single line, then add `<name>` to the `elements` array in `config.json`.

### Sounds

Place `.mp3` files in:
- `sounds/error/` — for `on_error`
- `sounds/notification/` — for `on_stop` and `on_notification`

Then set the filename (without extension) in `config.json`. Set to `null` to disable.

**Supported events:**

| Event | When |
|---|---|
| `on_error` | A tool call returns an error |
| `on_stop` | Claude finishes a response |
| `on_notification` | Claude sends a notification |

## Platform support

- macOS: `afplay`
- Linux: `paplay` or `aplay`
