#!/bin/bash
# Thin wrapper — launches the interactive TUI configurator
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$REPO_DIR/configure.py" "$@"
