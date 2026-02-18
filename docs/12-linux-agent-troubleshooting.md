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

## Sudo requires password
**Symptom:** `sudo: a password is required`
**Fix:**
- Ensure `/etc/sudoers.d/linux-agent` allows the wrapper scripts.
- Validate file permissions: `chmod 0440 /etc/sudoers.d/linux-agent`.

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
