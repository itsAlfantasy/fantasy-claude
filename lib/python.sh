#!/bin/bash
# Shared helper: resolves the correct Python 3.6+ binary cached by install.sh
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PYTHON_BIN_FILE="$_LIB_DIR/../.python_bin"
if [ -f "$_PYTHON_BIN_FILE" ]; then
  PYTHON_BIN=$(tr -d '[:space:]' < "$_PYTHON_BIN_FILE")
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
