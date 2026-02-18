# Linux Agent Executor Spec (Recommended Baseline)

This document defines the recommended and functional baseline for a single Linux expert agent. It covers the executor daemon, transport, security model, API schema, actions, logging, and the Merlin tool integration. The design prioritizes safety, predictability, and auditability.

## Goals
- Provide a safe local executor that can inspect and operate on the host with explicit user confirmation.
- Separate reasoning and planning from execution.
- Support dry-run by default.
- Keep actions structured and allowlisted.
- Produce auditable logs with request IDs.

## Non-Goals
- Remote control across the network.
- Arbitrary shell execution.
- Automatic execution without explicit user confirmation.

## Architecture Overview
- Merlin (agent brain) generates diagnosis and plan.
- Merlin calls a local tool `linux_tool` for dry-run.
- The executor daemon receives the request via Unix socket.
- The user confirms.
- Merlin calls `linux_tool` again with `dry_run=false`.
- The executor executes the action and returns logs and results.

## Recommended Decisions
- Transport: Unix Domain Socket only.
- API style: structured actions, not free-form shell.
- Executor user: dedicated `linux-agent` user.
- Default mode: read-only, write actions disabled.
- Confirmation: required before any non-read action.

## Executor Responsibilities
- Validate inputs.
- Map structured actions to fixed command templates.
- Enforce allowlists.
- Enforce timeouts and output limits.
- Record audit logs.
- Return structured results as JSON.

## Transport and Access
- The daemon listens on a Unix socket, for example `/run/linux-agent/agent.sock`.
- Socket permissions must allow only the intended caller group.
- The daemon should verify peer credentials via `SO_PEERCRED` when possible.
- No TCP listener is exposed.

## API Schema
### GET /whoami
Returns the effective executor identity and host metadata.

Response
```json
{
  "ok": true,
  "whoami": {
    "user": "linux-agent",
    "uid": 1001,
    "gid": 1001,
    "group": "linux-agent",
    "distro": {
      "NAME": "Ubuntu",
      "VERSION_ID": "24.04"
    },
    "pkg_mgr": "apt"
  }
}
```

### POST /run
Structured execution request.

Request
```json
{
  "request_id": "req-2026-02-18T12:00:00Z",
  "type": "read.os_release",
  "args": {},
  "dry_run": true
}
```

Response (dry-run)
```json
{
  "ok": true,
  "dry_run": true,
  "cmd": "cat /etc/os-release"
}
```

Response (execution)
```json
{
  "ok": true,
  "rc": 0,
  "stdout": "...",
  "stderr": ""
}
```

### POST /reload_acl
Reload the ACL policy from disk.

Response
```json
{
  "ok": true,
  "count": 13
}
```

## Action Catalog (Read-Only Baseline)
All read actions are enabled by default.

### read.os_release
Command template: `cat /etc/os-release`

### read.lsb_release
Command template: `lsb_release -a`

### read.packages
Args
```json
{"manager": "auto"}
```
Command template
- apt: `dpkg -l`
- dnf or yum: `rpm -qa`
- pacman: `pacman -Q`

### read.service_status
Args
```json
{"service": "ssh"}
```
Command template: `systemctl status <service>`

### read.service_enabled
Args
```json
{"service": "ssh"}
```
Command template: `systemctl is-enabled <service>`

### read.journalctl
Args
```json
{"service": "ssh", "lines": 200}
```
Command template: `journalctl -u <service> -n <lines> --no-pager`

### read.ss_listen
Command template: `ss -tuln`

### read.df
Command template: `df -h`

### read.free
Command template: `free -m`

### read.lsblk
Command template: `lsblk`

## Write Actions (Disabled by Default)
Write actions are available only when explicitly enabled by config.
Dry-run for write actions is allowed even when write actions are disabled, so the agent can preview commands safely.

### service.control
Args
```json
{"service": "nginx", "operation": "restart"}
```
Allowed operations: `start`, `stop`, `restart`, `enable`, `disable`

### pkg.install
Args
```json
{"packages": ["curl"]}
```
Command templates
- apt: `apt-get update` then `apt-get install -y <pkg>`
- dnf: `dnf install -y <pkg>`
- pacman: `pacman -S --noconfirm <pkg>`

### ansible.playbook
Args
```json
{"playbook": "/opt/linux-agent/playbooks/hardening.yml", "extra_vars": {"mode": "audit"}}
```
Command template: `ansible-playbook <playbook> -c local -e <extra_vars>`

## Validation Rules
- Services must match `^[a-zA-Z0-9@._:-]+$`.
- Package names must match `^[a-zA-Z0-9._+-]+$`.
- Journal lines are clamped to a safe range, for example `1..500`.
- Playbooks must be under a fixed allowlisted directory.

## Timeouts and Output Limits
- Default action timeout: 300 seconds.
- `ansible.playbook` timeout: 900 seconds.
- Output is truncated above a fixed limit, for example 1 MB.
- On timeout, the subprocess must be terminated.

## Logging and Audit
- Each request logs `request_id`, `type`, `args`, `dry_run`, and `rc`.
- Logs are JSONL for easy parsing.
- Sensitive data is avoided or redacted.

## Configuration (Recommended)
Config should be read from environment or a simple config file.

```text
SOCK_PATH=/run/linux-agent/agent.sock
LOG_DIR=/var/log/linux-agent
ALLOW_WRITE_ACTIONS=false
USE_SUDO=true
SUDO_BIN=/usr/bin/sudo
WRAPPERS_DIR=/opt/linux-agent/wrappers
REQUIRE_WRAPPERS=true
REQUIRE_PEER_UID=true
ALLOWED_PEER_UIDS=linux-agent
ALLOWED_PEER_GIDS=linux-agent
ACL_POLICY_PATH=/opt/linux-agent/acl_policy.json
ACL_RELOAD_ON_EACH_REQUEST=false
ALLOWED_WRITE_UIDS=
ALLOWED_WRITE_GIDS=
ANSIBLE_PREVIEW_EXECUTE=false
MAX_OUTPUT_BYTES=1048576
DEFAULT_TIMEOUT=300
ANSIBLE_TIMEOUT=900
PLAYBOOKS_DIR=/opt/linux-agent/playbooks
```

## Requirements
Minimum Python requirements for the executor and tool client.

```text
aiohttp>=3.8
requests-unixsocket>=0.2
ansible>=2.9
```

Note: for production hosts, prefer system packages where possible. For development, a virtualenv is fine.

## Merlin Tool Integration
The Merlin tool should implement the following behaviors.

1. Translate the plan into a sequence of structured actions.
2. Call the executor with `dry_run=true`.
3. Show the exact commands and expected impact to the user.
4. Require explicit confirmation before any write action.
5. Call the executor with `dry_run=false`.
6. Store the response logs in Merlin memory.

## Merlin Tool Client (Example)
Below is a minimal client example for a Merlin tool module. Treat it as a reference and adapt it to the structured action catalog defined in this spec.

Key points:
- Default all calls to `dry_run=true`.
- Only execute with `dry_run=false` after explicit user confirmation.
- Use Unix socket transport and short timeouts for reads.
- Map high-level actions to structured `type` and `args`.

Example client (requests-unixsocket):
```python
# merlin/tools/linux_tool.py
# Requires: requests_unixsocket
import requests_unixsocket
import uuid

class LinuxTool:
    def __init__(self, socket_path="/run/linux-agent/agent.sock"):
        self.s = requests_unixsocket.Session()
        self.base = f"http+unix://{requests_unixsocket.utils.quote_plus(socket_path)}"

    def whoami(self):
        r = self.s.get(f"{self.base}/whoami", timeout=10)
        return r.json()

    def run(self, action_type, args=None, dry_run=True, timeout=60):
        payload = {
            "type": action_type,
            "args": args or {},
            "dry_run": bool(dry_run),
            "request_id": str(uuid.uuid4()),
        }
        r = self.s.post(f"{self.base}/run", json=payload, timeout=timeout)
        return r.json()

    # Examples (structured action catalog)
    def read_os_release(self, dry_run=True):
        return self.run("read.os_release", {}, dry_run=dry_run, timeout=10)

    def read_service_status(self, service, dry_run=True):
        return self.run("read.service_status", {"service": service}, dry_run=dry_run, timeout=20)

    def install_package(self, package, dry_run=True):
        return self.run("pkg.install", {"packages": [package]}, dry_run=dry_run, timeout=300)

    def run_playbook(self, playbook, extra_vars=None, dry_run=True):
        return self.run("ansible.playbook", {"playbook": playbook, "extra_vars": extra_vars or {}}, dry_run=dry_run, timeout=900)
```

Note: if you choose to keep the earlier `read_cmd` style, restrict it to a strict allowlist and consider using `fullmatch` + explicit argument validation. The structured action catalog above is the recommended path.

## Recommended Usage Flow (Example)
This is the operational flow the agent should follow. No changes are executed without explicit user confirmation.

### Diagnostics
User: "Check nginx status and last 200 log events."

Merlin (dry-run):
- Call `linux_tool.read_cmd("systemctl status nginx", dry_run=True)`
- Call `linux_tool.read_cmd("journalctl -u nginx -n 200 --no-pager", dry_run=True)`
- Present outputs.

### Proposed Change (Dry-Run)
User: "Install nginx and enable it."

Merlin (dry-run):
- Call `linux_tool.install_package("nginx", dry_run=True)`
- Call `linux_tool.manage_service("nginx", "enable", dry_run=True)`
- Show the plan and the exact commands that would run.

### Explicit Confirmation
Merlin asks: "To confirm execution, type: `CONFIRM EXECUTE <request_id>`."

User confirms. Merlin executes with `dry_run=false`, then stores and shows logs.

Rule: without explicit textual confirmation (or a dedicated button), the agent never executes changes.

Note: read-only actions are safe to execute immediately. The executor may execute `read.*` actions even when `dry_run=true`. For write actions, `dry_run=true` returns the command without executing.
For `ansible.playbook`, dry-run returns a preview command with `--check --diff`.

## CLI Logging (Merlin)
The CLI can optionally log Linux tool actions to `data/linux_actions.jsonl`.
You can control this with environment variables:

```text
LINUX_LOG_ACTIONS=1
LINUX_LOG_MAX_CHARS=2000
LINUX_RAG_INDEX=1
LINUX_RAG_MAX_CHARS=2000
LINUX_IMPACT_CMD_CHARS=300
LINUX_READ_ONLY=1
```

Pending actions are persisted in `data/linux_pending.json` to allow recovery after CLI restart.

## Tests / Validation Environment
Use containers or VMs to avoid touching the real host during early validation.

### Docker (basic smoke tests)
Example flow for Ubuntu:
```bash
docker run -it --rm --privileged --name test-ubuntu ubuntu:22.04 /bin/bash
# Inside the container, install python3, pip, ansible, then copy the executor.
```

Recommended tests:
- `GET /whoami`
- `read.*` actions with `dry_run=true`
- `pkg.install` with `dry_run=true`, then with `dry_run=false` inside the container

For deeper coverage, use Vagrant boxes (Ubuntu/Debian + CentOS/RHEL family).

## Security Checklist (Pre-Deploy)
- Executor runs as `linux-agent` (not root).
- Socket `/var/run/linux-agent.sock` owned by `linux-agent:linux-agent` with mode `660`.
- `sudoers.d/linux-agent` limits exact commands (prefer wrappers).
- Executor does not accept arbitrary shell execution.
- `dry_run` is default and enforced.
- Logs are written to `/var/log/linux-agent` and rotated (logrotate).
- Before critical ops (kernel, partitions, major upgrades), create snapshot/backup.
- Automated tests in VMs/containers, with rollback validation.
- Update policy defined (package-based or deploy-based).

## Wiring to Merlin (Concrete Steps)
1. Place executor files under `/opt/linux-agent/` (or `infra/linux-agent` in the repo).
2. Add `merlin/tools/linux_tool.py` to the Merlin repository.
3. Create `linux-agent` user and set permissions.
4. Install dependencies (`pip3 install -r requirements.txt` or system packages).
5. Install systemd unit, sudoers, and playbooks.
6. Register `LinuxTool` in the Merlin tool registry, exposing methods like `whoami`, `read.*`, `pkg.install`, `service.control`, `ansible.playbook`.
7. Add prompts/handlers for intents (`linux.diagnose`, `linux.install`, `linux.harden`) that generate plans and request confirmation.
8. Validate in containers with dry-run and real execution.
9. Review logs/audit and tighten allowlists.

## Suggested Integration Tasks (When Reviewing the Repo)
When we move to implementation, the likely tasks will include:
- Add `LinuxTool` to the tools module and register it in the agent loop.
- Create prompt templates in the existing Merlin format (YAML/JSON/MD).
- Implement handlers that map intents to `linux_tool.*` calls.
- Add pytest cases for tool calls using a temporary Unix socket.

## Final Notes and Next Steps
- This package is safe for local use if you follow the security checklist.
- The chosen strategy (Unix socket + dedicated user + dry-run + allowlists + Ansible playbooks) balances flexibility and safety.
- When you want, we can apply the patches directly in your repository and wire the tool into the agent loop.
  - For that, we will need the relevant Merlin folders (`merlin/agent`, `merlin/tools`, `merlin/prompts`, and dependency files like `pyproject.toml` or `requirements.txt`).

## Rollout Plan
1. Phase 1: read-only actions only, socket local, logging enabled.
2. Phase 2: add write actions behind `ALLOW_WRITE_ACTIONS=true`.
3. Phase 3: add Ansible playbooks for complex changes.

## Systemd Notes (Recommended)
Use systemd to manage socket permissions and runtime directories. The unit should run as a dedicated `linux-agent` user and create `/run/linux-agent` with restricted permissions. Keep the socket readable only to the intended group.
The executor supports socket activation via `LISTEN_FDS` if you choose to use a `.socket` unit.

## Systemd Unit (Example)
Place the service unit at `/etc/systemd/system/linux-agent.service`.

```ini
[Unit]
Description=Linux Agent Executor
After=network.target

[Service]
User=linux-agent
Group=linux-agent
ExecStart=/usr/bin/python3 /opt/linux-agent/executor/executor.py
Restart=on-failure
RuntimeDirectory=linux-agent
RuntimeDirectoryMode=0750
LogsDirectory=linux-agent
LogsDirectoryMode=0750
AmbientCapabilities=
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=yes
ReadOnlyPaths=/usr
ProtectKernelModules=yes
ProtectKernelTunables=yes
PrivateDevices=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
MemoryDenyWriteExecute=yes

[Install]
WantedBy=multi-user.target
```

## Systemd Socket (Example)
Place the socket unit at `/etc/systemd/system/linux-agent.socket`.

```ini
[Unit]
Description=Linux Agent Executor Socket

[Socket]
ListenStream=/run/linux-agent/agent.sock
SocketUser=linux-agent
SocketGroup=linux-agent
SocketMode=0660
RemoveOnStop=yes
DirectoryMode=0750

[Install]
WantedBy=sockets.target
```

## User and Directory Setup (Example)
Create a dedicated system user and restrict file ownership.

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin linux-agent
sudo mkdir -p /opt/linux-agent
sudo chown -R linux-agent:linux-agent /opt/linux-agent
sudo mkdir -p /var/log/linux-agent
sudo chown linux-agent:linux-agent /var/log/linux-agent
```

If you are not using systemd socket activation, ensure the socket file ownership is restricted.

```bash
sudo chown linux-agent:linux-agent /var/run/linux-agent.sock
```

## Sudoers (Optional, Restricted)
Optional configuration to allow a constrained set of privileged commands.
Prefer wrappers with argument validation instead of allowing binaries directly.

File: `/etc/sudoers.d/linux-agent`

```text
linux-agent ALL=(root) NOPASSWD: /opt/linux-agent/wrappers/linux-agent-systemctl, /opt/linux-agent/wrappers/linux-agent-pkg-install, /opt/linux-agent/wrappers/linux-agent-ansible-playbook
```

Security note: the safest approach is to use explicit wrapper scripts with absolute paths and argument checks, and allow only those wrappers in sudoers.

## Ansible Playbooks (Examples)
These examples are intended to live under the allowlisted playbooks directory (for example `/opt/linux-agent/playbooks`).

### install_package.yml
```yaml
- hosts: localhost
  connection: local
  become: yes
  vars:
    pkg_name: "{{ pkg_name }}"
  tasks:
    - name: Ensure package is installed
      package:
        name: "{{ pkg_name }}"
        state: present
```

### ssh_hardening.yml
```yaml
- hosts: localhost
  connection: local
  become: yes
  tasks:
    - name: Backup sshd_config
      copy:
        src: /etc/ssh/sshd_config
        dest: "/var/backups/sshd_config.{{ lookup('pipe','date +%s') }}"
        remote_src: yes
    - name: Set PermitRootLogin no
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^#?PermitRootLogin'
        line: 'PermitRootLogin no'
        create: no
    - name: Restart sshd
      service:
        name: ssh
        state: restarted
```

### configure_firewall.yml
```yaml
- hosts: localhost
  connection: local
  become: yes
  tasks:
    - name: Ensure ufw is installed (Debian)
      apt:
        name: ufw
        state: present
      when: ansible_facts['pkg_mgr'] == 'apt'
    - name: Allow ssh
      ufw:
        rule: allow
        name: OpenSSH
    - name: Enable ufw
      ufw:
        state: enabled
```
