# Linux Agent Troubleshooting

Common issues and quick fixes.

## Socket not found
**Symptom:** `Socket não encontrado` or connection errors.
**Fix:**
- Ensure the executor is running.
- Check socket: `ls -l /run/linux-agent/agent.sock`
- If using systemd socket activation: `systemctl status linux-agent.socket`

## Peer UID/GID not allowed
**Symptom:** `peer uid/gid not allowed`
**Fix:**
- Set `ALLOWED_PEER_UIDS` / `ALLOWED_PEER_GIDS` to include the CLI user.
- Or disable checks: `REQUIRE_PEER_UID=false` (not recommended).

## Write actions disabled
**Symptom:** `action not allowed` or `write actions disabled`
**Fix:**
- Set `ALLOW_WRITE_ACTIONS=true` in systemd env.
- Confirm that the action is enabled in `ACL_POLICY_PATH`.

## Wrapper not found / command unavailable
**Symptom:** `command unavailable`
**Fix:**
- Ensure wrappers exist in `/opt/linux-agent/wrappers`.
- Check `WRAPPERS_DIR` and `REQUIRE_WRAPPERS`.

## Journalctl permission denied
**Symptom:** `No journal files were opened due to insufficient permissions`
**Fix:**
- Add the executor user to the journal group:
  - `sudo usermod -aG systemd-journal linux-agent`
- Restart the socket/service:
  - `sudo systemctl restart linux-agent.socket`

## Executor is not a package
**Symptom:** `ModuleNotFoundError: No module named 'executor.actions'; 'executor' is not a package`
**Fix:**
- Use module execution in systemd: `ExecStart=/usr/bin/python3 -m executor.executor`
- Ensure `WorkingDirectory=/opt/linux-agent`
- `sudo systemctl daemon-reload && sudo systemctl restart linux-agent.socket`

## Sudo requires password
**Symptom:** `sudo: a password is required`
**Fix:**
- Ensure `/etc/sudoers.d/linux-agent` allows the wrapper scripts.
- Validate file permissions: `chmod 0440 /etc/sudoers.d/linux-agent`.

## Sudo blocked by NoNewPrivileges
**Symptom:** `sudo: O sinalizador "sem novos privilégios" está definido`
**Fix:**
- Disable the restriction in a systemd drop-in when write actions are enabled:
  - `NoNewPrivileges=no`
  - `sudo systemctl daemon-reload && sudo systemctl restart linux-agent.socket`

## Package install fails with read-only filesystem
**Symptom:** `dpkg: ... Sistema de arquivos somente para leitura` (e.g., `/usr/bin/*.dpkg-new`)
**Fix:**
- Relax filesystem protection for write actions:
  - Simplest: `ProtectSystem=off`
  - More strict: `ProtectSystem=full` + `ReadWritePaths=/usr /etc /var`
- Restart the socket after changes:
  - `sudo systemctl daemon-reload && sudo systemctl restart linux-agent.socket`

## Ansible temp dir is read-only
**Symptom:** `Unable to create local directories '/root/.ansible/tmp'`
**Fix:**
- Prefer the wrapper default:
  - `linux-agent-ansible-playbook` sets `ANSIBLE_LOCAL_TEMP=/var/tmp/ansible`
  - `HOME=/var/tmp/ansible-home` so `~/.ansible` is writable
  - Keep `ProtectHome=yes`
- If you use a custom temp dir, ensure it is writable and allowed by systemd:
  - `ReadWritePaths=/var/tmp`
  - `sudo systemctl daemon-reload && sudo systemctl restart linux-agent.socket`

## Playbook not found
**Symptom:** `playbook not found`
**Fix:**
- Place playbooks under `/opt/linux-agent/playbooks`.
- Ensure `PLAYBOOKS_DIR` is correct.

## ACL policy denies an action
**Symptom:** `action not allowed`
**Fix:**
- Update `ACL_POLICY_PATH` to allow the action.
- Restart the executor to reload policy, or call `/reload_acl`.

## Reload ACL fails
**Symptom:** `/reload_acl` returns error
**Fix:**
- Verify `ACL_POLICY_PATH` exists and is valid JSON.
- Check file permissions for the executor user.

## Logs not written
**Symptom:** no logs in `/var/log/linux-agent/`
**Fix:**
- Check `LOG_DIR` and permissions.
- Ensure systemd `LogsDirectory` is set or directory exists.

## pytest not found
**Symptom:** `No module named pytest`
**Fix:**
- `python3 -m pip install pytest`
- `python3 -m pytest -q`
