#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"

echo "Installing claude-hooks from $REPO_DIR"

# Make all scripts executable
chmod +x "$REPO_DIR/statusline/statusline.sh"
chmod +x "$REPO_DIR/statusline/elements/"*.sh
chmod +x "$REPO_DIR/hooks/sounds.sh"
chmod +x "$REPO_DIR/hooks/notify-permission.sh"
chmod +x "$REPO_DIR/hooks/notify-idle.sh"
chmod +x "$REPO_DIR/hooks/notify-elicitation.sh"
chmod +x "$REPO_DIR/hooks/notify-auth.sh"

# Create ~/.claude if needed
mkdir -p "$CLAUDE_DIR"

# Patch settings.json
if [ ! -f "$SETTINGS" ]; then
    echo "{}" > "$SETTINGS"
fi

python3 - <<EOF
import json

settings_path = "$SETTINGS"
repo_dir = "$REPO_DIR"

with open(settings_path) as f:
    settings = json.load(f)

settings["statusLine"] = {
    "type": "command",
    "command": f"bash {repo_dir}/statusline/statusline.sh"
}

hook_command = f"bash {repo_dir}/hooks/sounds.sh"

hooks = settings.setdefault("hooks", {})

for event in ["PostToolUse", "Stop", "Notification"]:
    event_hooks = hooks.setdefault(event, [])
    already = any(
        any(h.get("command") == hook_command for h in entry.get("hooks", []))
        for entry in event_hooks
    )
    if not already:
        event_hooks.append({
            "matcher": ".*" if event == "PostToolUse" else "",
            "hooks": [{"type": "command", "command": hook_command}]
        })

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")

print("settings.json updated.")
EOF

echo ""
echo "Done! Restart Claude Code to apply changes."
echo "Edit config.json to customize statusline elements and sounds."
