# Notification Hook

macOS notification when Claude Code needs input (permission prompts, questions, etc.). Clicking the notification brings iTerm2 to focus.

## Dependencies

```bash
brew install terminal-notifier
```

## Hook Script: `notify-on-prompt.sh`

```bash
#!/bin/bash
# Sends a macOS notification when Claude needs input and brings iTerm2 to focus.

# Read JSON from stdin
input=$(cat)

# Extract fields
title=$(echo "$input" | /usr/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('title','Claude Code'))" 2>/dev/null)
message=$(echo "$input" | /usr/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','Needs your attention'))" 2>/dev/null)

# Fallbacks
[ -z "$title" ] && title="Claude Code"
[ -z "$message" ] && message="Needs your attention"

# Send macOS notification with sound — click activates iTerm2
terminal-notifier -title "$title" -message "$message" -sound default \
    -activate com.googlecode.iterm2 -sender com.googlecode.iterm2
```

## Hook Input (JSON from stdin)

The `Notification` event passes this JSON:

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Unique session identifier |
| `transcript_path` | string | Path to session transcript `.jsonl` |
| `cwd` | string | Working directory |
| `hook_event_name` | string | Always `"Notification"` |
| `message` | string | Notification text (e.g. "Claude needs your permission to use Bash") |
| `title` | string | Optional title |
| `notification_type` | string | `permission_prompt`, `idle_prompt`, `auth_success`, or `elicitation_dialog` |

## Settings (`~/.claude/settings.json`)

Add under `hooks`:

```json
"Notification": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "bash /path/to/notify-on-prompt.sh",
        "timeout": 10
      }
    ]
  }
]
```

No `matcher` needed — fires on all notification types.

## Notes

- `terminal-notifier` is used instead of `osascript` because it supports `-activate` (bring app to front on click) and `-sender` (show iTerm2 icon on the notification).
- The hook is informational only — it cannot block or modify Claude's behavior.
- On Linux, replace `terminal-notifier` with `notify-send` (no click-to-activate support).

## Future: Interactive Notifications

To add action buttons (Allow/Deny, option selection) directly in the notification, `terminal-notifier` is not enough. Options:

1. **[alerter](https://github.com/vjeantet/alerter)** — fork of terminal-notifier with `-actions "Opt1,Opt2"` support. Not in Homebrew, needs manual install.
2. **Custom Swift script** — use `UNUserNotificationCenter` with registered notification categories and actions. Most native solution but requires compilation.
3. **AppleScript dialog** — `display dialog` with buttons. Works but shows a popup window, not an inline notification.

Once interactive notifications are working, the script could send keystrokes back to iTerm2 via AppleScript `System Events` to auto-answer prompts.
