# Linux Agent Implementation Checklist

This checklist provides a path-by-path implementation guide.

## Executor
Path: `executor/`

Checklist:
- Create `executor/executor.py` with aiohttp app and Unix socket binding.
- Add `executor/config.py` for env/config loading.
- Add `executor/actions.py` with action registry and validators.
- Add `executor/runner.py` with subprocess execution, timeouts, and output caps.
- Add `executor/logging.py` for JSONL audit logging.
- Ensure `read.*` actions are implemented and validated.

## Merlin Tool Client
Path: `merlin/tools/`

Checklist:
- Add `merlin/tools/linux_tool.py`.
- Register `LinuxTool` in the Merlin tool registry.
- Enforce dry-run by default.
- Implement confirmation flow in the agent loop.

## Prompts and Handlers
Path: `merlin/prompts/` or agent config location.

Checklist:
- Add prompt templates for intents: `linux.diagnose`, `linux.install`, `linux.harden`.
- Add handler mapping from intents to `linux_tool.*` actions.
- Add confirmation prompt template with `request_id` and TTL.

## Infrastructure
Path: `infra/`

Checklist:
- Add systemd unit example for `linux-agent.service`.
- Add optional `linux-agent.socket` for socket activation.
- Add sudoers wrapper policy (or wrapper scripts).
- Add playbooks to `infra/playbooks/`.

## Tests
Path: `tests/`

Checklist:
- Add Docker-based smoke tests for read-only actions.
- Add validation tests for bad args and unknown actions.
- Add timeout and truncation tests.
- Add tool tests with temporary Unix socket.

## Docs
Path: `docs/`

Checklist:
- Keep `docs/04-linux-agent-executor.md` as the main spec.
- Keep `docs/05-linux-agent-requirements.md` for acceptance criteria.
- Keep `docs/06-linux-agent-roadmap.md` as the execution plan.
- Keep `docs/07-linux-agent-executor-design.md` as the design.
- Keep `docs/08-linux-agent-implementation-checklist.md` updated.

