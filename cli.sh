#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  install)   exec bash "$SCRIPT_DIR/install.sh" ;;
  --version) cat "$SCRIPT_DIR/VERSION" ;;
  *)         exec python3 "$SCRIPT_DIR/configure.py" ;;
esac
