# Wrapper Scripts

These wrappers provide an extra safety layer for privileged actions.

## Installation (Example)
```bash
sudo mkdir -p /opt/linux-agent/wrappers
sudo cp infra/wrappers/linux-agent-* /opt/linux-agent/wrappers/
sudo chown root:root /opt/linux-agent/wrappers/linux-agent-*
sudo chmod 0755 /opt/linux-agent/wrappers/linux-agent-*
```

Set the executor config:
```text
WRAPPERS_DIR=/opt/linux-agent/wrappers
REQUIRE_WRAPPERS=true
USE_SUDO=true
```

Then allow these wrappers in sudoers instead of the raw binaries.

Notes:
- The `linux-agent-ansible-playbook` wrapper sets `ANSIBLE_LOCAL_TEMP` and `ANSIBLE_REMOTE_TMP`
  to `/var/tmp/ansible` to avoid writes under `/root` when `ProtectHome=yes`.
- It also sets `HOME=/var/tmp/ansible-home` to keep `~/.ansible` writable.
