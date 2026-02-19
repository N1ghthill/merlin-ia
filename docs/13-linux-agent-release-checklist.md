# Linux Agent Release Checklist

Use this checklist before and after deploying to a real host.

## Pre-Deploy
- [ ] Tests run locally (`python3 -m pytest -q`).
- [ ] Docker/VM validation completed.
- [ ] ACL policy reviewed (`infra/acl_policy.json`).
- [ ] Sudoers uses wrappers only.
- [ ] `ALLOW_WRITE_ACTIONS` is set correctly.
- [ ] `REQUIRE_PEER_UID` and allowed UID/GID set.
- [ ] `WRAPPERS_DIR` and `PLAYBOOKS_DIR` correct.
- [ ] Executor logs directory is writable by `linux-agent`.
- [ ] Logrotate installed.
- [ ] If write actions enabled: `NoNewPrivileges=no` and filesystem protections adjusted (`ProtectSystem=off` or `ReadWritePaths=/usr /etc /var`).
- [ ] For Ansible: wrapper temp dir `/var/tmp/ansible` available (or equivalent).

## Deploy
- [ ] Executor and wrappers copied to `/opt/linux-agent`.
- [ ] `linux-agent` user exists.
- [ ] Systemd unit + socket installed.
- [ ] Socket permissions correct (`660`).
- [ ] Service/socket enabled and running.
- [ ] ExecStart uses module invocation (`python3 -m executor.executor`) with `WorkingDirectory=/opt/linux-agent`.

## Post-Deploy
- [ ] `GET /whoami` succeeds.
- [ ] `read.*` action works.
- [ ] Dry-run for write actions returns expected commands.
- [ ] Confirmed execution works (if enabled).
- [ ] Logs written to `/var/log/linux-agent/`.
- [ ] Pending actions persist across CLI restart.
- [ ] Smoke CLI script passes.
