# Linux Agent Validation Checklist

## Pre-Deploy
- [ ] `bash scripts/check_requirements.sh`
- [ ] `python3 -m pip install pytest` (if needed)
- [ ] `python3 -m pytest -q`

## Deploy
- [ ] `bash scripts/deploy_linux_agent.sh`
- [ ] `sudo systemctl status linux-agent.socket`
- [ ] `ls -l /run/linux-agent/agent.sock`
- [ ] If service fails with `executor is not a package`, use `python3 -m executor.executor` in systemd and restart the socket

## UID/GID Configuration
- [ ] `sudo systemctl edit linux-agent.service`
- [ ] `Environment=ALLOWED_PEER_UIDS=<your_user>`
- [ ] `Environment=ALLOWED_PEER_GIDS=<your_group>`
- [ ] `sudo systemctl daemon-reload && sudo systemctl restart linux-agent.socket`

## Health Check
- [ ] `bash scripts/post_deploy_check.sh`

## CLI (Read-Only)
- [ ] `export LINUX_READ_ONLY=1`
- [ ] `python3 merlin_cli.py`
- [ ] `/linux-diagnose ssh 50`

## Dry-Run Write
- [ ] `/linux-install nginx`
- [ ] Verify `request_id` and impact summary

## Write (Staging Only)
- [ ] `export LINUX_READ_ONLY=0`
- [ ] `ALLOW_WRITE_ACTIONS=true`
- [ ] `NoNewPrivileges=no`
- [ ] Filesystem protections adjusted (`ProtectSystem=off` or `ReadWritePaths=/usr /etc /var`)
- [ ] `ALLOWED_WRITE_UIDS/GIDS` configured
- [ ] `/linux-install nginx`
- [ ] `CONFIRM EXECUTE <request_id>`
- [ ] Ansible temp dir writable (wrapper uses `/var/tmp/ansible`)

## Logs & ACL
- [ ] `tail -n 20 /var/log/linux-agent/executor.jsonl`
- [ ] `/linux-reload-acl`

## Rollback (if needed)
- [ ] `bash scripts/rollback_linux_agent.sh`
