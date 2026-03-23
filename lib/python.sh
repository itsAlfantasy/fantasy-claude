#!/bin/bash
# Shared helper: resolves the correct Python 3.10+ binary cached by install.sh

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PYTHON_BIN_FILE="$_LIB_DIR/../.python_bin"

_detect_python() {
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

PYTHON_BIN=""
if [ -f "$_PYTHON_BIN_FILE" ]; then
  PYTHON_BIN=$(tr -d '[:space:]' < "$_PYTHON_BIN_FILE")
  if ! command -v "$PYTHON_BIN" &>/dev/null; then
    PYTHON_BIN=""
  fi
fi

# Self-healing: if cache is missing or stale, re-detect and rewrite
if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN=$(_detect_python) || PYTHON_BIN=""
  if [ -n "$PYTHON_BIN" ]; then
    echo "$PYTHON_BIN" > "$_PYTHON_BIN_FILE"
  else
    PYTHON_BIN="python3"
  fi
fi
