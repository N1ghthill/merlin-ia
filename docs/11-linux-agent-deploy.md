# Linux Agent Deploy Guide (Draft)

This guide describes a safe, minimal deployment for the executor + Merlin integration.

## 1) Create user and directories
```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin linux-agent
sudo mkdir -p /opt/linux-agent
sudo mkdir -p /var/log/linux-agent
sudo chown -R linux-agent:linux-agent /opt/linux-agent
sudo chown -R linux-agent:linux-agent /var/log/linux-agent
```

## 2) Install executor and wrappers
```bash
# copy repo files to /opt/linux-agent
sudo rsync -a executor/ /opt/linux-agent/executor/
sudo rsync -a infra/wrappers/ /opt/linux-agent/wrappers/
sudo rsync -a infra/acl_policy.json /opt/linux-agent/acl_policy.json

# permissions for wrappers
sudo chown root:root /opt/linux-agent/wrappers/linux-agent-*
sudo chmod 0755 /opt/linux-agent/wrappers/linux-agent-*
```

## 3) Configure sudoers (wrappers only)
```bash
sudo cp infra/sudoers.d/linux-agent /etc/sudoers.d/linux-agent
sudo chmod 0440 /etc/sudoers.d/linux-agent
```

## 4) Systemd units (service + socket)
```bash
sudo cp infra/systemd/linux-agent.service /etc/systemd/system/linux-agent.service
sudo cp infra/systemd/linux-agent.socket /etc/systemd/system/linux-agent.socket
sudo systemctl daemon-reload
sudo systemctl enable --now linux-agent.socket
```

## 5) Log rotation
```bash
sudo cp infra/logrotate/linux-agent /etc/logrotate.d/linux-agent
```

## 6) Environment config (optional)
Set env vars in a systemd drop-in (example):
```bash
sudo systemctl edit linux-agent.service
```
Then add:
```ini
[Service]
Environment=ALLOW_WRITE_ACTIONS=false
Environment=REQUIRE_PEER_UID=true
Environment=ALLOWED_PEER_UIDS=linux-agent
Environment=ALLOWED_PEER_GIDS=linux-agent
Environment=WRAPPERS_DIR=/opt/linux-agent/wrappers
Environment=PLAYBOOKS_DIR=/opt/linux-agent/playbooks
Environment=ANSIBLE_PREVIEW_EXECUTE=false
Environment=ACL_POLICY_PATH=/opt/linux-agent/acl_policy.json
Environment=ACL_RELOAD_ON_EACH_REQUEST=false
Environment=ALLOWED_WRITE_UIDS=
Environment=ALLOWED_WRITE_GIDS=
```

## 7) Validate the socket
```bash
sudo systemctl status linux-agent.socket
ls -l /run/linux-agent/agent.sock
```

## 8) Merlin CLI integration
Run the Merlin CLI:
```bash
python3 merlin_cli.py
```
Then use:
```
/linux-diagnose nginx
/linux-install nginx
CONFIRM EXECUTE <request_id>
```

## 9) Container/VM validation
Prefer Docker or VM tests before running on a real host.
Use `tests/docker-test.md` as a baseline.

## Rollback
- Stop service: `sudo systemctl stop linux-agent.socket`
- Remove unit files and sudoers
- Remove `/opt/linux-agent` if desired
