from __future__ import annotations

from typing import Any, Dict, List


def diagnose_service(service: str, lines: int = 200) -> List[Dict[str, Any]]:
    return [
        {"type": "read.service_status", "args": {"service": service}},
        {"type": "read.journalctl", "args": {"service": service, "lines": lines}},
    ]


def install_and_enable(service: str, manager: str = "auto") -> List[Dict[str, Any]]:
    return [
        {"type": "pkg.install", "args": {"packages": [service], "manager": manager}},
        {"type": "service.control", "args": {"service": service, "operation": "enable"}},
    ]


def harden_ssh(playbook: str = "ssh_hardening.yml") -> List[Dict[str, Any]]:
    return [
        {"type": "ansible.playbook", "args": {"playbook": playbook, "extra_vars": {}}},
    ]


def harden_firewall(playbook: str = "configure_firewall.yml") -> List[Dict[str, Any]]:
    return [
        {"type": "ansible.playbook", "args": {"playbook": playbook, "extra_vars": {}}},
    ]


def describe_action(action: Dict[str, Any]) -> str:
    action_type = action.get("type", "unknown")
    args = action.get("args", {})
    if action_type == "pkg.install":
        pkgs = args.get("packages", [])
        return f"Instalar pacotes: {', '.join(pkgs) if pkgs else '(nenhum)'}"
    if action_type == "service.control":
        return f"Service {args.get('service')} -> {args.get('operation')}"
    if action_type == "ansible.playbook":
        return f"Executar playbook: {args.get('playbook')}"
    return f"{action_type} {args}"


def summarize_actions(actions: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for action in actions:
        lines.append(describe_action(action))
    return lines
