#!/usr/bin/env bash
set -euo pipefail

missing=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

check_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing: $1"
    missing=1
  fi
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
  elif [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "missing: python3"
  missing=1
else
  if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    echo "missing: pip (python -m pip)"
    missing=1
  fi
fi

check_cmd pip3

"$PYTHON_BIN" - <<'PY' || missing=1
import importlib
for mod in ("aiohttp", "requests_unixsocket", "ansible"):
    try:
        importlib.import_module(mod)
    except Exception:
        print(f"missing python module: {mod}")
        raise
PY

if [ "$missing" -ne 0 ]; then
  echo "Some requirements are missing."
  exit 1
fi

echo "All requirements OK."
