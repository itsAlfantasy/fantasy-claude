#!/bin/bash
set -e
INSTALL_DIR="$HOME/.claude-hooks"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating claude-hooks..."
    git -C "$INSTALL_DIR" pull origin main
else
    echo "Installing claude-hooks..."
    git clone https://github.com/itsAlfantasy/fantasy-claude.git "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
bash install.sh
echo "Done! Restart Claude Code to apply changes."
