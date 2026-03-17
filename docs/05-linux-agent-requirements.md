# Linux Agent Requirements (Historical Planning Document)

This document is kept as an implementation-phase artifact.
For the current reference set, prefer `docs/04-linux-agent-executor.md`, `docs/11-linux-agent-deploy.md`, `docs/12-linux-agent-troubleshooting.md`, `docs/14-linux-agent-compatibility.md`, and `docs/17-linux-agent-validation-report.md`.

This document translates the executor spec into implementation requirements and acceptance criteria.

## Scope
- Local-only Linux expert agent with a safe execution boundary.
- Unix socket transport.
- Read-only actions first, write actions later.

## Out of Scope
- Remote access over TCP.
- Arbitrary shell execution.
- Fully autonomous execution without explicit confirmation.

## Functional Requirements
- FR-1: Provide a daemon that listens on a Unix socket and exposes `GET /whoami` and `POST /run`.
- FR-2: Support structured action types matching the read-only catalog (`read.*`).
- FR-3: Enforce `dry_run=true` by default for all actions.
- FR-4: Return structured JSON responses with `ok`, `rc`, `stdout`, `stderr`.
- FR-5: Provide request IDs for audit and traceability.

## Security Requirements
- SR-1: Executor runs as dedicated `linux-agent` user (not root).
- SR-2: Socket file is restricted to intended user/group (mode 660).
- SR-3: No arbitrary shell execution is permitted.
- SR-4: Validate action arguments with strict allowlists and regex rules.
- SR-5: Enforce explicit user confirmation before any write action.
- SR-6: Optional sudoers rules must be minimal and prefer wrapper scripts.

## Reliability Requirements
- RR-1: Each action has a timeout with subprocess termination on expiry.
- RR-2: Output is capped and truncated above a maximum byte limit.
- RR-3: Fail closed on validation errors.

## Observability Requirements
- OR-1: Log every request as JSONL with request_id, type, args, dry_run, rc.
- OR-2: Avoid logging sensitive content where possible (redaction).

## API Requirements
- AR-1: `GET /whoami` returns user, uid, gid, group, distro, pkg_mgr.
- AR-2: `POST /run` accepts `type`, `args`, `dry_run`, `request_id`.
- AR-3: Response codes use HTTP 200 on success, 400 for validation errors, 500 for internal errors.

## Integration Requirements (Merlin)
- IR-1: Tool client uses Unix socket transport.
- IR-2: Calls default to dry-run.
- IR-3: Confirmation is required for any non-read action.
- IR-4: Logs and results are stored in Merlin history/memory.

## Testing Requirements
- TR-1: Smoke tests in Docker or VM for read-only actions.
- TR-2: Tests for validation failures (bad args, unknown actions).
- TR-3: Tests for timeout behavior and output truncation.
- TR-4: Dry-run vs execute behavior validated.

## Acceptance Criteria (Phase 1: Read-Only)
- AC-1: `/whoami` returns correct user/distro metadata.
- AC-2: All `read.*` actions execute and return output.
- AC-3: Invalid action types are rejected with 400.
- AC-4: Invalid arguments are rejected with 400.
- AC-5: Actions time out and terminate subprocesses.
- AC-6: Output truncation is enforced.
- AC-7: All requests are logged with request_id.

## Acceptance Criteria (Phase 2: Integration)
- AC-8: Merlin uses LinuxTool with dry-run by default.
- AC-9: Confirmation is required to execute changes.
- AC-10: Executed actions are logged and stored in Merlin history.

## Acceptance Criteria (Phase 3: Write Actions)
- AC-11: Write actions are disabled by default and gated by config.
- AC-12: `pkg.install`, `service.control`, and `ansible.playbook` execute with sudo wrappers.
- AC-13: Playbooks are restricted to allowlisted paths.

## Implementation Task List
- T-1: Build executor skeleton with Unix socket, endpoints, and strict validation.
- T-2: Implement action catalog for `read.*`.
- T-3: Add timeout handling with subprocess termination.
- T-4: Add output cap and truncation.
- T-5: Add JSONL audit logging.
- T-6: Add LinuxTool client in Merlin and register it.
- T-7: Add confirmation flow in agent loop.
- T-8: Write Docker-based smoke tests.
- T-9: Add playbook allowlist and sudo wrapper design.
