#!/bin/bash
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

case "${1:-}" in
  --help|-h)
    echo "Usage: fantasy-claude <command> [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  install      Install fantasy-claude into Claude Code"
    echo "  uninstall    Remove fantasy-claude from Claude Code"
    echo "  configure    Launch interactive TUI configurator (default)"
    echo ""
    echo "Options:"
    echo "  --help, -h       Show this help message"
    echo "  --version, -v    Show version"
    exit 0
    ;;
  --version|-v)
    echo "fantasy-claude v$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "unknown")"
    exit 0
    ;;
  install)
    exec bash "$SCRIPT_DIR/install.sh" "${@:2}"
    ;;
  uninstall)
    exec bash "$SCRIPT_DIR/uninstall.sh" "${@:2}"
    ;;
  *)
    # shellcheck source=lib/python.sh
    source "$SCRIPT_DIR/lib/python.sh"
    exec $PYTHON_BIN "$SCRIPT_DIR/configure.py" "$@"
    ;;
esac
