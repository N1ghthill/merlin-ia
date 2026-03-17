#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SOCK="${LINUX_AGENT_SOCK:-/run/linux-agent/agent.sock}"
if [ ! -S "$SOCK" ]; then
  echo "Socket não encontrado em $SOCK"
  echo "Inicie o executor antes de rodar este smoke test."
  exit 1
fi

export LINUX_READ_ONLY=1
export LINUX_AUTO_INTENTS=0

python3 -m merlin_cli <<'EOF'
/linux read.os_release {}
/linux-diagnose ssh 50
/linux-pending
exit
EOF
