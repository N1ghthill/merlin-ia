#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

SOCK="${LINUX_AGENT_SOCK:-/run/linux-agent/agent.sock}"

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
  echo "Python não encontrado. Ative a venv ou defina PYTHON_BIN."
  exit 1
fi

echo "==> Checking python dependencies"
"$PYTHON_BIN" - <<'PY'
import importlib
for mod in ("requests_unixsocket",):
    try:
        importlib.import_module(mod)
    except Exception:
        print(f"missing python module: {mod}")
        raise
PY

if [ ! -S "$SOCK" ]; then
  echo "Socket not found: $SOCK"
  exit 1
fi

echo "==> Checking executor socket"
ls -l "$SOCK"

echo "==> Checking whoami endpoint"
"$PYTHON_BIN" - <<'PY'
import os
import requests_unixsocket
try:
    quote_plus = requests_unixsocket.utils.quote_plus
except Exception:
    from urllib.parse import quote_plus
sock = os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
base = "http+unix://" + quote_plus(sock)
s = requests_unixsocket.Session()
r = s.get(base + "/whoami", timeout=10)
print(r.json())
PY

echo "==> Reload ACL"
"$PYTHON_BIN" - <<'PY'
import os
import requests_unixsocket
try:
    quote_plus = requests_unixsocket.utils.quote_plus
except Exception:
    from urllib.parse import quote_plus
sock = os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
base = "http+unix://" + quote_plus(sock)
s = requests_unixsocket.Session()
r = s.post(base + "/reload_acl", timeout=10)
print(r.json())
PY

echo "==> Dry-run read.os_release"
"$PYTHON_BIN" - <<'PY'
import os
import requests_unixsocket
try:
    quote_plus = requests_unixsocket.utils.quote_plus
except Exception:
    from urllib.parse import quote_plus
sock = os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
base = "http+unix://" + quote_plus(sock)
s = requests_unixsocket.Session()
payload = {"type": "read.os_release", "args": {}, "dry_run": True, "request_id": "post-deploy-check"}
r = s.post(base + "/run", json=payload, timeout=10)
print(r.json())
PY

echo "==> Done."
