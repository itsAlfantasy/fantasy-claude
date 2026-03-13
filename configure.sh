#!/bin/bash
# Thin wrapper — launches the interactive TUI configurator
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_DIR/lib/python.sh"
exec $PYTHON_BIN "$REPO_DIR/configure.py" "$@"
