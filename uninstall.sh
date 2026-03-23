#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"
SYMLINK="$CLAUDE_DIR/fantasy-claude"

VERSION=$(cat "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")

case "${1:-}" in
  --help|-h)
    echo "Usage: bash uninstall.sh [OPTIONS]"
    echo ""
    echo "Remove fantasy-claude from Claude Code."
    echo ""
    echo "Removes hook entries from ~/.claude/settings.json,"
    echo "removes the symlink at ~/.claude/fantasy-claude,"
    echo "and cleans up the Python cache. Does NOT delete the repo."
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

echo "Uninstalling fantasy-claude..."

# Detect Python for JSON manipulation
source "$REPO_DIR/lib/python.sh"

# Remove hooks and statusLine from settings.json
if [ -f "$SETTINGS" ]; then
  $PYTHON_BIN - <<PYEOF
import json

settings_path = "$SETTINGS"
repo_dir = "$REPO_DIR"
symlink = "$SYMLINK"

with open(settings_path) as f:
    try:
        settings = json.load(f)
    except json.JSONDecodeError:
        print(f"WARNING: {settings_path} contains invalid JSON, skipping")
        exit(0)

changed = False

# Remove statusLine if it points to fantasy-claude
sl = settings.get("statusLine", {})
cmd = sl.get("command", "") if isinstance(sl, dict) else ""
if "fantasy-claude" in cmd or repo_dir in cmd:
    del settings["statusLine"]
    print("Removed statusLine entry")
    changed = True

# Remove hook entries containing fantasy-claude or repo_dir
hooks = settings.get("hooks", {})
for event in list(hooks.keys()):
    event_hooks = hooks[event]
    filtered = [
        entry for entry in event_hooks
        if not any(
            "fantasy-claude" in h.get("command", "") or repo_dir in h.get("command", "")
            for h in entry.get("hooks", [])
        )
    ]
    if len(filtered) != len(event_hooks):
        hooks[event] = filtered
        print(f"Removed fantasy-claude entries from {event}")
        changed = True
    # Clean up empty event arrays
    if not hooks[event]:
        del hooks[event]

if not hooks:
    settings.pop("hooks", None)

if changed:
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    print("settings.json updated.")
else:
    print("No fantasy-claude entries found in settings.json.")
PYEOF
fi

# Remove symlink
if [ -L "$SYMLINK" ]; then
  rm "$SYMLINK"
  echo "Removed symlink: $SYMLINK"
elif [ -e "$SYMLINK" ]; then
  echo "WARNING: $SYMLINK exists but is not a symlink, skipping"
fi

# Remove Python cache
if [ -f "$REPO_DIR/.python_bin" ]; then
  rm "$REPO_DIR/.python_bin"
  echo "Removed .python_bin cache"
fi

echo ""
echo "Done! Restart Claude Code to apply changes."
echo "The repo at $REPO_DIR has not been deleted — remove it manually if desired."
