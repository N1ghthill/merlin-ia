# Linux Agent Roadmap (Executable)

This roadmap translates requirements into a staged, executable plan with clear entry and exit criteria.

## Phase 0: Alignment and Safety Baseline
Goal: finalize scope and lock the safety posture.

Deliverables:
- Confirm action catalog for read-only scope.
- Confirm transport and privilege model (Unix socket + `linux-agent` user).
- Confirm confirmation flow and request_id TTL.

Exit Criteria:
- Sign-off on `docs/04-linux-agent-executor.md` and `docs/05-linux-agent-requirements.md`.
- Action catalog frozen for Phase 1.

## Phase 1: Read-Only Executor MVP
Goal: safe inspection-only executor with strict validation.

Milestones:
1. Executor skeleton with Unix socket, `GET /whoami`, `POST /run`.
2. Structured action routing for `read.*`.
3. Strict argument validation and allowlists.
4. Timeouts with subprocess termination.
5. Output truncation.
6. JSONL audit logging.

Deliverables:
- `executor/executor.py` implementing `read.*` actions only.
- Config values for socket path, timeouts, output caps.

Exit Criteria:
- All Phase 1 acceptance criteria in `docs/05-linux-agent-requirements.md` met.
- Smoke tests pass in Docker.

## Phase 2: Merlin Integration (Dry-Run Only)
Goal: connect Merlin to the executor and enforce confirmations.

Milestones:
1. LinuxTool client with Unix socket transport.
2. Tool registration in Merlin agent loop.
3. Confirmation flow in prompts/handlers.
4. Request_id storage and confirmation TTL.
5. Logging of results into Merlin history.

Deliverables:
- `merlin/tools/linux_tool.py`.
- Prompt templates or handlers for `linux.diagnose`.

Exit Criteria:
- Merlin uses dry-run by default.
- Explicit confirmation required before any write action.

## Phase 3: Write Actions (Controlled)
Goal: enable controlled, privileged actions behind config gates.

Milestones:
1. Wrapper scripts or restricted sudoers.
2. `service.control` and `pkg.install` actions.
3. `ansible.playbook` with allowlisted paths.
4. Updated playbooks and policy.
5. Expanded tests for execution and rollback.

Deliverables:
- `sudoers.d/linux-agent` with wrappers.
- Playbooks under allowlisted directory.

Exit Criteria:
- Write actions disabled by default and gated by config.
- All Phase 3 acceptance criteria met.

## Phase 4: Hardening and Operations
Goal: operational readiness.

Milestones:
1. Systemd unit + socket activation.
2. Log rotation and redaction rules.
3. Release/update policy.
4. Security review checklist completed.

Deliverables:
- Systemd units in `infra/` or deployment notes.
- `logrotate` config and operational docs.

Exit Criteria:
- Security checklist complete.
- Repeatable deploy process documented.

## Dependency Notes
- Phase 2 depends on Phase 1 executor stability.
- Phase 3 depends on a safe confirmation flow and access controls.
- Phase 4 depends on validated read/write execution in controlled environments.

