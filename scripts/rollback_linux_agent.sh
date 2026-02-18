#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping linux-agent socket"
sudo systemctl stop linux-agent.socket || true
sudo systemctl disable linux-agent.socket || true

echo "==> Removing systemd units"
sudo rm -f /etc/systemd/system/linux-agent.service
sudo rm -f /etc/systemd/system/linux-agent.socket
sudo systemctl daemon-reload || true

echo "==> Removing sudoers and logrotate configs"
sudo rm -f /etc/sudoers.d/linux-agent
sudo rm -f /etc/logrotate.d/linux-agent

echo "==> Optional: remove /opt/linux-agent (executor + wrappers)"
echo "Run manually if desired: sudo rm -rf /opt/linux-agent"

echo "==> Done."
