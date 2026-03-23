#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"
SYMLINK="$CLAUDE_DIR/fantasy-claude"

VERSION=$(cat "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")

case "${1:-}" in
  --help|-h)
    echo "Usage: bash install.sh [OPTIONS]"
    echo ""
    echo "Install fantasy-claude into Claude Code."
    echo ""
    echo "Creates a symlink at ~/.claude/fantasy-claude pointing to this repo,"
    echo "registers the statusline and sound hooks in ~/.claude/settings.json,"
    echo "and detects a compatible Python 3.10+ binary."
    echo ""
    echo "Options:"
    echo "  --help, -h       Show this help message"
    echo "  --version, -v    Show version"
    exit 0
    ;;
  --version|-v)
    echo "fantasy-claude v$VERSION"
    exit 0
    ;;
esac

echo "Installing fantasy-claude v$VERSION from $REPO_DIR"

detect_python() {
  local candidates=("python3.13" "python3.12" "python3.11" "python3.10" "python3" "python")
  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" &>/dev/null; then
      local ver
      ver=$("$candidate" -c "import sys; v=sys.version_info; print(v.major*100+v.minor)" 2>/dev/null)
      if [ -n "$ver" ] && [ "$ver" -ge 310 ]; then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

echo "Detecting Python 3.10+..."
PYTHON_PATH=$(detect_python) || {
  echo "ERROR: Python 3.10+ not found."
  echo "Install Python 3.10+ from https://www.python.org/downloads/ and re-run install.sh"
  exit 1
}
echo "Using Python: $PYTHON_PATH ($("$PYTHON_PATH" --version))"
echo "$PYTHON_PATH" > "$REPO_DIR/.python_bin"

# Make all scripts executable
chmod +x "$REPO_DIR/statusline/statusline.sh"
chmod +x "$REPO_DIR/statusline/elements/"*.sh
chmod +x "$REPO_DIR/hooks/sounds.sh"
chmod +x "$REPO_DIR/hooks/burn-rate-update.sh"
chmod +x "$REPO_DIR/hooks/notify-permission.sh"
chmod +x "$REPO_DIR/hooks/notify-idle.sh"
chmod +x "$REPO_DIR/hooks/notify-elicitation.sh"
chmod +x "$REPO_DIR/hooks/notify-auth.sh"

# Create ~/.claude if needed
mkdir -p "$CLAUDE_DIR"

# Create/update symlink
if [ -e "$SYMLINK" ] && [ ! -L "$SYMLINK" ]; then
  echo "ERROR: $SYMLINK exists but is not a symlink."
  echo "Remove it manually and re-run install.sh."
  exit 1
fi
ln -sfn "$REPO_DIR" "$SYMLINK"
echo "Symlink: $SYMLINK -> $REPO_DIR"

# Use symlink path in settings.json
HOOK_BASE="$SYMLINK"

# Patch settings.json
if [ ! -f "$SETTINGS" ]; then
    echo "{}" > "$SETTINGS"
fi

"$PYTHON_PATH" - <<PYEOF
import json
import shutil

settings_path = "$SETTINGS"
hook_base = "$HOOK_BASE"
repo_dir = "$REPO_DIR"

with open(settings_path) as f:
    try:
        settings = json.load(f)
    except json.JSONDecodeError:
        shutil.copy2(settings_path, settings_path + ".bak")
        print(f"WARNING: {settings_path} contains invalid JSON — backed up to {settings_path}.bak, starting fresh")
        settings = {}

settings["statusLine"] = {
    "type": "command",
    "command": f"bash {hook_base}/statusline/statusline.sh"
}

sound_command = f"bash {hook_base}/hooks/sounds.sh"
burn_command = f"bash {hook_base}/hooks/burn-rate-update.sh"

hooks = settings.setdefault("hooks", {})

# Helper: remove old entries that reference the repo by its real path (pre-symlink installs)
def strip_old_entries(event_hooks, old_path):
    return [
        entry for entry in event_hooks
        if not any(old_path in h.get("command", "") for h in entry.get("hooks", []))
    ]

for event in ["PostToolUse", "Stop", "Notification"]:
    event_hooks = hooks.setdefault(event, [])
    # Remove old hardcoded-path entries if repo was moved or pre-symlink
    if repo_dir != hook_base:
        hooks[event] = strip_old_entries(event_hooks, repo_dir)
        event_hooks = hooks[event]
    # Add sound hook if not present
    already = any(
        any(h.get("command") == sound_command for h in entry.get("hooks", []))
        for entry in event_hooks
    )
    if not already:
        event_hooks.append({
            "matcher": ".*" if event == "PostToolUse" else "",
            "hooks": [{"type": "command", "command": sound_command}]
        })

for event in ["PostToolUse", "Stop"]:
    event_hooks = hooks.setdefault(event, [])
    if repo_dir != hook_base:
        hooks[event] = strip_old_entries(event_hooks, repo_dir)
        event_hooks = hooks[event]
    already = any(
        any(h.get("command") == burn_command for h in entry.get("hooks", []))
        for entry in event_hooks
    )
    if not already:
        event_hooks.append({
            "matcher": ".*" if event == "PostToolUse" else "",
            "hooks": [{"type": "command", "command": burn_command}]
        })

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")

print("settings.json updated.")
PYEOF

# Config version migration
"$PYTHON_PATH" - <<PYEOF
import json
import shutil

config_path = "$REPO_DIR/config.json"
target_version = "$(cat "$REPO_DIR/VERSION" 2>/dev/null || echo "1.0.0")"

try:
    with open(config_path) as f:
        config = json.load(f)
except json.JSONDecodeError:
    shutil.copy2(config_path, config_path + ".bak")
    print(f"WARNING: {config_path} contains invalid JSON — backed up to {config_path}.bak")
    exit(0)

current_version = config.get("version", "0.0.0")

# Migration: flat "elements" array -> 2D "lines" array (pre-1.0.0 configs)
sl = config.get("statusline", {})
if "elements" in sl and "lines" not in sl:
    sl["lines"] = [sl.pop("elements")]
    print("Migrated statusline.elements -> statusline.lines")

if current_version != target_version:
    config["version"] = target_version
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    print(f"Config version updated to {target_version}")
else:
    print(f"Config version already at {target_version}")
PYEOF

echo ""
echo "Done! Restart Claude Code to apply changes."
echo "Edit config.json to customize statusline elements and sounds."
