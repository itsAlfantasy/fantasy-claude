#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"

VERSION=$(cat "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")
echo "Installing claude-hooks v$VERSION from $REPO_DIR"

detect_python() {
  local candidates=("python3.13" "python3.12" "python3.11" "python3.10" "python3.9" "python3.8" "python3.7" "python3.6" "python3" "python")
  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" &>/dev/null; then
      local ver
      ver=$("$candidate" -c "import sys; v=sys.version_info; print(v.major*100+v.minor)" 2>/dev/null)
      if [ -n "$ver" ] && [ "$ver" -ge 306 ]; then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

echo "Detecting Python 3.6+..."
PYTHON_PATH=$(detect_python) || {
  echo "ERROR: Python 3.6+ not found."
  echo "Install Python 3 from https://www.python.org/downloads/ and re-run install.sh"
  exit 1
}
echo "Using Python: $PYTHON_PATH ($("$PYTHON_PATH" --version))"
echo "$PYTHON_PATH" > "$REPO_DIR/.python_bin"

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

"$PYTHON_PATH" - <<EOF
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
