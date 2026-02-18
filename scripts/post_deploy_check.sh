#!/usr/bin/env bash
set -euo pipefail

SOCK="${LINUX_AGENT_SOCK:-/run/linux-agent/agent.sock}"
if [ ! -S "$SOCK" ]; then
  echo "Socket not found: $SOCK"
  exit 1
fi

echo "==> Checking executor socket"
ls -l "$SOCK"

echo "==> Checking whoami endpoint"
python3 - <<'PY'
import os
import requests_unixsocket
sock = os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
base = "http+unix://" + requests_unixsocket.utils.quote_plus(sock)
s = requests_unixsocket.Session()
r = s.get(base + "/whoami", timeout=10)
print(r.json())
PY

echo "==> Reload ACL"
python3 - <<'PY'
import os
import requests_unixsocket
sock = os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
base = "http+unix://" + requests_unixsocket.utils.quote_plus(sock)
s = requests_unixsocket.Session()
r = s.post(base + "/reload_acl", timeout=10)
print(r.json())
PY

echo "==> Dry-run read.os_release"
python3 - <<'PY'
import os
import requests_unixsocket
sock = os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
base = "http+unix://" + requests_unixsocket.utils.quote_plus(sock)
s = requests_unixsocket.Session()
payload = {"type": "read.os_release", "args": {}, "dry_run": True, "request_id": "post-deploy-check"}
r = s.post(base + "/run", json=payload, timeout=10)
print(r.json())
PY

echo "==> Done."
