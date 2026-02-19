# Linux Agent Validation Report

Date: 2026-02-19

## Scope
- Executor + socket activation
- Merlin CLI integration (read + write)
- Ansible playbook execution
- Package/service install (nginx)

## Environment
- OS: Debian GNU/Linux forky/sid
- Systemd enabled
- Executor user: `linux-agent`
- CLI user: `irving`
- Socket: `/run/linux-agent/agent.sock`

## Summary
Status: **PASS**

## Validations Performed
- Executor socket is active and serving requests.
- Read actions:
  - `read.os_release`
  - `read.service_status`
  - `read.journalctl`
  - `read.df`, `read.free`, `read.lsblk`
- Write actions:
  - `pkg.install` (curl, nginx)
  - `service.control` (enable ssh/nginx)
- Ansible playbook:
  - `install_package.yml` (curl) executed successfully.
- Nginx:
  - Installed and enabled.
  - Service active (running).
  - Port 80 listening.
  - `nginx -t` successful.

## Active Write Policy (During Validation)
- `ALLOW_WRITE_ACTIONS=true`
- `ALLOWED_WRITE_UIDS=irving`
- `NoNewPrivileges=no`
- `ProtectSystem=off`
- `ProtectHome=yes`
- Ansible wrapper sets:
  - `ANSIBLE_LOCAL_TEMP=/var/tmp/ansible`
  - `ANSIBLE_REMOTE_TMP=/var/tmp/ansible`
  - `HOME=/var/tmp/ansible-home`

## Notes / Warnings (Non-Blocking)
- `debconf` warnings about non-interactive TTY during package installs.
- `ufw` trigger warning about iptables version during nginx install (did not block).
- Ansible warnings about implicit localhost inventory (expected).

## Artifacts
- Deploy guide: `docs/11-linux-agent-deploy.md`
- Troubleshooting: `docs/12-linux-agent-troubleshooting.md`
- Validation checklist: `docs/16-linux-agent-validation-checklist.md`
- Release checklist: `docs/13-linux-agent-release-checklist.md`
