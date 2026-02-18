#!/usr/bin/env bash
set -euo pipefail

missing=0

check_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing: $1"
    missing=1
  fi
}

check_cmd python3
check_cmd pip3

python3 - <<'PY' || missing=1
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
