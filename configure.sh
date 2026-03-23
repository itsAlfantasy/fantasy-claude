#!/bin/bash
# Thin wrapper — launches the interactive TUI configurator
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-}" in
  --help|-h)
    echo "Usage: bash configure.sh [OPTIONS]"
    echo ""
    echo "Launch the interactive TUI configurator for fantasy-claude."
    echo "Use arrow keys to navigate, Enter to select, q to quit."
    echo ""
    echo "Options:"
    echo "  --help, -h       Show this help message"
    echo "  --version, -v    Show version"
    exit 0
    ;;
  --version|-v)
    cat "$REPO_DIR/VERSION"
    exit 0
    ;;
esac

source "$REPO_DIR/lib/python.sh"
exec $PYTHON_BIN "$REPO_DIR/configure.py" "$@"
