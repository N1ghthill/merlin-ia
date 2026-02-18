#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Creating linux-agent user and directories"
sudo useradd --system --no-create-home --shell /usr/sbin/nologin linux-agent 2>/dev/null || true
sudo mkdir -p /opt/linux-agent /var/log/linux-agent
sudo chown -R linux-agent:linux-agent /opt/linux-agent /var/log/linux-agent

echo "==> Installing executor and wrappers"
sudo rsync -a executor/ /opt/linux-agent/executor/
sudo rsync -a infra/wrappers/ /opt/linux-agent/wrappers/
sudo rsync -a infra/acl_policy.json /opt/linux-agent/acl_policy.json

sudo chown root:root /opt/linux-agent/wrappers/linux-agent-*
sudo chmod 0755 /opt/linux-agent/wrappers/linux-agent-*

echo "==> Installing sudoers, systemd units, logrotate"
sudo cp infra/sudoers.d/linux-agent /etc/sudoers.d/linux-agent
sudo chmod 0440 /etc/sudoers.d/linux-agent

sudo cp infra/systemd/linux-agent.service /etc/systemd/system/linux-agent.service
sudo cp infra/systemd/linux-agent.socket /etc/systemd/system/linux-agent.socket
sudo systemctl daemon-reload
sudo systemctl enable --now linux-agent.socket

sudo cp infra/logrotate/linux-agent /etc/logrotate.d/linux-agent

echo "==> Done. Check status:"
echo "systemctl status linux-agent.socket"
echo "ls -l /run/linux-agent/agent.sock"
