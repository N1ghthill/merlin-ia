# Linux Agent Executor Design (Historical Draft)

This document captures a design-stage view of the executor.
For current operational reference, prefer `docs/04-linux-agent-executor.md` and `docs/11-linux-agent-deploy.md`.

This design outlines the executor structure that satisfies the requirements in `docs/05-linux-agent-requirements.md`.

## Design Goals
- Structured actions only.
- Strict validation and allowlists.
- Safe timeouts and output limits.
- Clear audit logging.
- Local-only access via Unix socket.

## High-Level Modules
- `config`: loads environment/config file.
- `server`: aiohttp app, routes, and middleware.
- `actions`: action registry and validators.
- `runner`: subprocess execution with timeout and output caps.
- `logging`: JSONL audit log writer.

## Configuration
Recommended environment variables:
```text
SOCK_PATH=/run/linux-agent/agent.sock
LOG_DIR=/var/log/linux-agent
ALLOW_WRITE_ACTIONS=false
USE_SUDO=true
SUDO_BIN=/usr/bin/sudo
WRAPPERS_DIR=/opt/linux-agent/wrappers
REQUIRE_WRAPPERS=true
MAX_OUTPUT_BYTES=1048576
DEFAULT_TIMEOUT=300
ANSIBLE_TIMEOUT=900
PLAYBOOKS_DIR=/opt/linux-agent/playbooks
```

## API Contracts
### GET /whoami
Returns user, uid, gid, group, distro, and detected package manager.

### POST /run
Request:
```json
{"type":"read.os_release","args":{},"dry_run":true,"request_id":"req-..."}
```

Response:
```json
{"ok":true,"dry_run":true,"cmd":"cat /etc/os-release"}
```

## Action Registry
Actions are registered with:
- `type`: string identifier (ex: `read.os_release`)
- `validate(args)`: strict validation
- `build_cmd(args)`: returns argv list
- `timeout`: optional override
- `write_action`: bool

Example (pseudo):
```text
action: read.service_status
validate: service matches ^[a-zA-Z0-9@._:-]+$
build_cmd: ["systemctl", "status", service]
```

## Validation Rules
- Use `fullmatch` for regex validation.
- Clamp numeric values (example `lines=1..500`).
- Reject unknown keys in `args`.
- Fail closed with 400 responses.

## Execution Rules
- Use `asyncio.create_subprocess_exec` only.
- On timeout, terminate the subprocess.
- Capture stdout/stderr and cap output size.
- Return `rc`, `stdout`, `stderr`.

## Output Truncation
Strategy:
- Read stdout/stderr and truncate to `MAX_OUTPUT_BYTES`.
- If truncated, append a marker line.

Example marker:
```text
[output truncated at 1048576 bytes]
```

## Audit Logging
Log format (JSONL):
```json
{"request_id":"req-...","type":"read.os_release","args":{},"dry_run":true,"rc":0}
```

## Socket Permissions
Prefer systemd socket activation to set permissions and ownership.
If not used, apply `chown` and `chmod` to the socket after creation.

## Privileged Actions
- Disabled by default.
- Require explicit config `ALLOW_WRITE_ACTIONS=true`.
- Prefer wrapper scripts with fixed arguments.

## Error Handling
- 400 for validation errors.
- 500 for internal errors.
- Always return JSON with `ok=false` and an error message.

## Extension Points
- Add new `read.*` actions without changing routing logic.
- Add `pkg.install` and `service.control` once write actions are enabled.
- Add `ansible.playbook` with allowlisted playbooks directory.
