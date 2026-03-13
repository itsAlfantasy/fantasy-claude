#!/bin/bash
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
# shellcheck source=lib/python.sh
source "$SCRIPT_DIR/lib/python.sh"
case "${1:-}" in
  install)   exec bash "$SCRIPT_DIR/install.sh" ;;
  --version) cat "$SCRIPT_DIR/VERSION" ;;
  *)         exec $PYTHON_BIN "$SCRIPT_DIR/configure.py" ;;
esac
