# Linux Agent Status Snapshot (Historical)

This file is a status snapshot from the implementation phase.
Some gaps listed below reflect the validation context at the time and should be read as historical notes, not as the current public summary.

This document summarizes what is implemented, expected behavior, and what still needs testing or completion.

## Implemented
- Executor daemon with Unix socket transport.
- Structured action catalog (`read.*`, `service.control`, `pkg.install`, `ansible.playbook`).
- Strict argument validation and allowlists.
- Timeouts with process termination and output truncation.
- Audit logging to JSONL.
- Socket activation support via systemd (`linux-agent.socket`).
- Wrapper scripts for privileged actions + sudoers example for wrappers.
- Merlin Linux tool client (`merlin/tools/linux_tool.py`).
- CLI integration with dry-run + explicit confirmation.
- Pending action persistence (`data/linux_pending.json`).
- Linux action logging (`data/linux_actions.jsonl`).
- Optional RAG indexing of executed actions.
- Auto-intent detection for diagnose/install/harden flows.
- Impact summary with risk level before confirmation.
- Peer credential checks (SO_PEERCRED) for allowed UIDs.
- Logrotate template for executor logs.
- Systemd unit improved (RuntimeDirectory/LogsDirectory).
- Basic ACL for read/write action gating.
- Systemd socket example with directory permissions.
- Deploy guide drafted.
- ACL policy file (JSON) for action gating.
- Read-only lock for CLI execution (LINUX_READ_ONLY=1).
- Smoke CLI script added.
- Release checklist added.
- ACL reload and write-UID/GID gating added.
- Deploy script added.
- ACL reload endpoint added.
- Post-deploy check script added.
- Quickstart added to README.
- Requirements check script added.
- Rollback script added.
- Final report added.
- Validation checklist added.

## Expected Behavior
- Read actions execute immediately and return output.
- Write actions return dry-run commands, then require explicit confirmation.
- `ansible.playbook` dry-run returns a preview command with `--check --diff`.
- Confirmed actions execute and are logged.
- Pending actions survive CLI restarts (until TTL expires).

## Not Tested Yet
- Unit tests: pytest is not installed in the environment.
- Docker validation in `tests/docker-test.md` not executed.
- VM tests (Vagrant) not executed.
- Systemd units not installed or started.
- Sudoers and wrapper deployment not validated on a real host.
- Peer credential checks not validated in a real deployment.
- Logrotate config not installed or verified.
- ACL behavior not validated against a real system policy.
- Systemd socket activation not validated on a real deployment.
- Deploy guide steps not validated on a real host.
- ACL policy not validated in a live deployment.
- Read-only lock not validated in a real operator workflow.
- Smoke CLI script not validated.
- Release checklist not validated.
- ACL reload not validated.
- Write UID/GID gating not validated.
- Deploy script not validated.
- ACL reload endpoint not validated.
- Post-deploy check script not validated.
- Requirements check script not validated.
- Rollback script not validated.
- Validation checklist not validated.

## Known Limitations / Gaps
- No full agent loop integration (intents are CLI-driven and auto-detected).
- No RBAC or peer credential checks on the Unix socket.
- No logrotate configuration included yet.
- Playbook hardening risk warnings are basic.
- No rollback automation beyond playbooks.

## Next Steps (Recommended)
1. Install pytest and run unit tests.
2. Run Docker-based validation.
3. Deploy wrappers and sudoers on a test VM.
4. Install systemd unit + socket activation.
5. Validate permissions on `/run/linux-agent/agent.sock`.
6. Add log rotation for executor logs.
7. Add peer credential verification (SO_PEERCRED).
8. Decide on full agent loop integration for production usage.
