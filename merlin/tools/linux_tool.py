from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

import requests_unixsocket
from urllib.parse import quote_plus


class LinuxTool:
    def __init__(self, socket_path: Optional[str] = None):
        sock = socket_path or os.getenv("LINUX_AGENT_SOCK", "/run/linux-agent/agent.sock")
        self.session = requests_unixsocket.Session()
        try:
            quoted = requests_unixsocket.utils.quote_plus(sock)
        except Exception:
            quoted = quote_plus(sock)
        self.base = f"http+unix://{quoted}"

    def whoami(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base}/whoami", timeout=10)
        return r.json()

    def run(
        self,
        action_type: str,
        args: Optional[Dict[str, Any]] = None,
        dry_run: bool = True,
        timeout: int = 60,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "type": action_type,
            "args": args or {},
            "dry_run": bool(dry_run),
            "request_id": request_id or str(uuid.uuid4()),
        }
        r = self.session.post(f"{self.base}/run", json=payload, timeout=timeout)
        return r.json()

    # Convenience helpers (read-only)
    def read_os_release(self, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.os_release", {}, dry_run=dry_run, timeout=10)

    def read_lsb_release(self, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.lsb_release", {}, dry_run=dry_run, timeout=10)

    def read_packages(self, manager: str = "auto", dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.packages", {"manager": manager}, dry_run=dry_run, timeout=60)

    def read_service_status(self, service: str, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.service_status", {"service": service}, dry_run=dry_run, timeout=20)

    def read_service_enabled(self, service: str, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.service_enabled", {"service": service}, dry_run=dry_run, timeout=20)

    def read_journalctl(self, service: str, lines: int = 200, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.journalctl", {"service": service, "lines": lines}, dry_run=dry_run, timeout=60)

    def read_ss_listen(self, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.ss_listen", {}, dry_run=dry_run, timeout=10)

    def read_df(self, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.df", {}, dry_run=dry_run, timeout=10)

    def read_free(self, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.free", {}, dry_run=dry_run, timeout=10)

    def read_lsblk(self, dry_run: bool = True) -> Dict[str, Any]:
        return self.run("read.lsblk", {}, dry_run=dry_run, timeout=10)

    # Write actions (require explicit confirmation and executor config)
    def service_control(self, service: str, operation: str, dry_run: bool = True) -> Dict[str, Any]:
        return self.run(
            "service.control",
            {"service": service, "operation": operation},
            dry_run=dry_run,
            timeout=60,
        )

    def pkg_install(self, packages: list[str], manager: str = "auto", dry_run: bool = True) -> Dict[str, Any]:
        return self.run(
            "pkg.install",
            {"packages": packages, "manager": manager},
            dry_run=dry_run,
            timeout=300,
        )

    def ansible_playbook(self, playbook: str, extra_vars: Optional[Dict[str, Any]] = None, dry_run: bool = True) -> Dict[str, Any]:
        return self.run(
            "ansible.playbook",
            {"playbook": playbook, "extra_vars": extra_vars or {}},
            dry_run=dry_run,
            timeout=900,
        )
