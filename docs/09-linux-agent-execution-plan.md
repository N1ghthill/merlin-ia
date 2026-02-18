# Linux Agent Execution Plan (Tasks and Order)

This plan breaks the roadmap into actionable tasks with order and dependencies.

## Phase 0: Alignment
1. Confirm action catalog for read-only scope.
2. Confirm confirmation flow and request_id TTL policy.
3. Confirm socket path and runtime locations.

## Phase 1: Read-Only Executor MVP
1. Create `executor/` skeleton (`executor.py`, `config.py`, `actions.py`, `runner.py`, `logging.py`).
2. Implement config loader (env + defaults).
3. Implement Unix socket server (`GET /whoami`, `POST /run`).
4. Implement action registry for `read.*`.
5. Implement strict validation (regex fullmatch, numeric clamps).
6. Implement subprocess runner with timeouts and kill-on-timeout.
7. Implement output truncation and markers.
8. Implement JSONL audit logging.
9. Add read-only smoke tests (Docker).

## Phase 2: Merlin Integration (Dry-Run)
1. Add `merlin/tools/linux_tool.py` client.
2. Register `LinuxTool` in the agent loop.
3. Add prompt templates for `linux.diagnose`.
4. Add confirmation flow with request_id and TTL.
5. Persist responses into Merlin history.
6. Add tool tests with a temporary Unix socket.

## Phase 3: Controlled Write Actions
1. Define wrapper scripts for privileged actions.
2. Add `sudoers.d/linux-agent` for wrappers only.
3. Implement `service.control` and `pkg.install`.
4. Implement `ansible.playbook` with allowlisted paths.
5. Add playbooks under allowlisted directory.
6. Add tests for write actions in container or VM.

## Phase 4: Hardening and Ops
1. Add systemd unit and optional socket activation unit.
2. Add logrotate config for executor logs.
3. Document update policy and rollback plan.
4. Run full security checklist and record results.

## Optional Milestones
- Add `read.*` actions for network and storage diagnostics.
- Add OS compatibility matrix (Ubuntu/Debian, RHEL, Arch).

