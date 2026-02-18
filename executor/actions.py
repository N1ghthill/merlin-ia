from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shutil
from typing import Callable, Dict, List, Tuple, Optional

from .config import Config


SERVICE_RE = re.compile(r"^[a-zA-Z0-9@._:-]+$")
PKG_RE = re.compile(r"^[a-zA-Z0-9._+-]+$")


def _reject_unknown_keys(args: Dict[str, object], allowed: set, required: set) -> Tuple[bool, str]:
    extra = set(args.keys()) - allowed
    if extra:
        return False, f"unknown args: {', '.join(sorted(extra))}"
    missing = [k for k in required if k not in args]
    if missing:
        return False, f"missing args: {', '.join(missing)}"
    return True, ""


def detect_package_manager() -> str:
    if shutil.which("apt-get") or shutil.which("apt"):
        return "apt"
    if shutil.which("dnf") or shutil.which("yum"):
        return "dnf"
    if shutil.which("pacman"):
        return "pacman"
    return "unknown"


def _validate_service(args: Dict[str, object], _cfg: Config) -> Tuple[bool, str]:
    ok, msg = _reject_unknown_keys(args, {"service"}, {"service"})
    if not ok:
        return ok, msg
    svc = str(args.get("service", "")).strip()
    if not SERVICE_RE.fullmatch(svc):
        return False, "invalid service name"
    return True, ""


def _validate_journalctl(args: Dict[str, object], _cfg: Config) -> Tuple[bool, str]:
    ok, msg = _reject_unknown_keys(args, {"service", "lines"}, {"service"})
    if not ok:
        return ok, msg
    svc = str(args.get("service", "")).strip()
    if not SERVICE_RE.fullmatch(svc):
        return False, "invalid service name"
    if "lines" in args:
        try:
            lines = int(args["lines"])
        except (TypeError, ValueError):
            return False, "lines must be an integer"
        if lines < 1 or lines > 500:
            return False, "lines must be between 1 and 500"
    return True, ""


def _validate_packages(args: Dict[str, object], _cfg: Config) -> Tuple[bool, str]:
    ok, msg = _reject_unknown_keys(args, {"manager"}, set())
    if not ok:
        return ok, msg
    manager = str(args.get("manager", "auto")).strip().lower()
    if manager not in {"auto", "apt", "dnf", "yum", "pacman"}:
        return False, "invalid package manager"
    return True, ""


def _validate_no_args(args: Dict[str, object], _cfg: Config) -> Tuple[bool, str]:
    return _reject_unknown_keys(args, set(), set())


def _validate_service_control(args: Dict[str, object], _cfg: Config) -> Tuple[bool, str]:
    ok, msg = _reject_unknown_keys(args, {"service", "operation"}, {"service", "operation"})
    if not ok:
        return ok, msg
    svc = str(args.get("service", "")).strip()
    op = str(args.get("operation", "")).strip()
    if not SERVICE_RE.fullmatch(svc):
        return False, "invalid service name"
    if op not in {"start", "stop", "restart", "enable", "disable"}:
        return False, "invalid operation"
    return True, ""


def _validate_pkg_install(args: Dict[str, object], _cfg: Config) -> Tuple[bool, str]:
    ok, msg = _reject_unknown_keys(args, {"packages", "manager"}, {"packages"})
    if not ok:
        return ok, msg
    packages = args.get("packages")
    if not isinstance(packages, list) or not packages:
        return False, "packages must be a non-empty list"
    for pkg in packages:
        if not isinstance(pkg, str) or not PKG_RE.fullmatch(pkg.strip()):
            return False, "invalid package name"
    manager = str(args.get("manager", "auto")).strip().lower()
    if manager not in {"auto", "apt", "dnf", "yum", "pacman"}:
        return False, "invalid package manager"
    return True, ""


def _validate_playbook(args: Dict[str, object], cfg: Config) -> Tuple[bool, str]:
    ok, msg = _reject_unknown_keys(args, {"playbook", "extra_vars"}, {"playbook"})
    if not ok:
        return ok, msg
    playbook = str(args.get("playbook", "")).strip()
    if not playbook:
        return False, "playbook required"
    extra_vars = args.get("extra_vars", {})
    if extra_vars is not None and not isinstance(extra_vars, dict):
        return False, "extra_vars must be an object"

    base = os.path.abspath(cfg.playbooks_dir)
    candidate = playbook
    if not os.path.isabs(candidate):
        candidate = os.path.join(base, candidate)
    candidate = os.path.abspath(candidate)

    if os.path.commonpath([candidate, base]) != base:
        return False, "playbook outside allowlisted directory"
    if not os.path.exists(candidate):
        return False, "playbook not found"
    return True, ""


def _resolve_cmd(cfg: Config, wrapper_name: str, binary_name: str) -> str:
    wrapper = os.path.join(cfg.wrappers_dir, wrapper_name)
    if os.path.isfile(wrapper):
        return wrapper
    if cfg.require_wrappers:
        return ""
    return shutil.which(binary_name) or binary_name


def _with_sudo(cfg: Config, cmd: List[str]) -> List[str]:
    if cfg.use_sudo:
        return [cfg.sudo_bin, "-n"] + cmd
    return cmd


@dataclass(frozen=True)
class Action:
    name: str
    validate: Callable[[Dict[str, object], Config], Tuple[bool, str]]
    build_cmd: Callable[[Dict[str, object], Config], List[str]]
    timeout_override: Optional[int] = None
    write_action: bool = False


def _cmd_os_release(_: Dict[str, object], _cfg: Config) -> List[str]:
    return ["cat", "/etc/os-release"]


def _cmd_lsb_release(_: Dict[str, object], _cfg: Config) -> List[str]:
    return ["lsb_release", "-a"]


def _cmd_packages(args: Dict[str, object], _cfg: Config) -> List[str]:
    manager = str(args.get("manager", "auto")).strip().lower()
    if manager == "auto":
        manager = detect_package_manager()
    if manager == "unknown":
        return []
    if manager in {"dnf", "yum"}:
        return ["rpm", "-qa"]
    if manager == "pacman":
        return ["pacman", "-Q"]
    return ["dpkg", "-l"]


def _cmd_service_status(args: Dict[str, object], _cfg: Config) -> List[str]:
    svc = str(args.get("service", "")).strip()
    return ["systemctl", "status", svc, "--no-pager"]


def _cmd_service_enabled(args: Dict[str, object], _cfg: Config) -> List[str]:
    svc = str(args.get("service", "")).strip()
    return ["systemctl", "is-enabled", svc]


def _cmd_journalctl(args: Dict[str, object], _cfg: Config) -> List[str]:
    svc = str(args.get("service", "")).strip()
    lines = int(args.get("lines", 200))
    lines = max(1, min(500, lines))
    return ["journalctl", "-u", svc, "-n", str(lines), "--no-pager"]


def _cmd_ss_listen(_: Dict[str, object], _cfg: Config) -> List[str]:
    return ["ss", "-tuln"]


def _cmd_df(_: Dict[str, object], _cfg: Config) -> List[str]:
    return ["df", "-h"]


def _cmd_free(_: Dict[str, object], _cfg: Config) -> List[str]:
    return ["free", "-m"]


def _cmd_lsblk(_: Dict[str, object], _cfg: Config) -> List[str]:
    return ["lsblk"]


def _cmd_service_control(args: Dict[str, object], cfg: Config) -> List[str]:
    svc = str(args.get("service", "")).strip()
    op = str(args.get("operation", "")).strip()
    systemctl_cmd = _resolve_cmd(cfg, "linux-agent-systemctl", "systemctl")
    if not systemctl_cmd:
        return []
    return _with_sudo(cfg, [systemctl_cmd, op, svc])


def _cmd_pkg_install(args: Dict[str, object], cfg: Config) -> List[str]:
    packages = [str(p).strip() for p in args.get("packages", [])]
    manager = str(args.get("manager", "auto")).strip().lower()
    if manager == "auto":
        manager = detect_package_manager()

    wrapper = _resolve_cmd(cfg, "linux-agent-pkg-install", "linux-agent-pkg-install")
    if wrapper:
        return _with_sudo(cfg, [wrapper, manager] + packages)

    if manager in {"dnf", "yum"}:
        base = shutil.which("dnf") or shutil.which("yum") or "dnf"
        return _with_sudo(cfg, [base, "install", "-y"] + packages)
    if manager == "pacman":
        base = shutil.which("pacman") or "pacman"
        return _with_sudo(cfg, [base, "-S", "--noconfirm"] + packages)
    base = shutil.which("apt-get") or "apt-get"
    return _with_sudo(cfg, [base, "install", "-y"] + packages)


def _cmd_ansible_playbook(args: Dict[str, object], cfg: Config) -> List[str]:
    playbook = str(args.get("playbook", "")).strip()
    base = os.path.abspath(cfg.playbooks_dir)
    candidate = playbook
    if not os.path.isabs(candidate):
        candidate = os.path.join(base, candidate)
    candidate = os.path.abspath(candidate)

    ansible_cmd = _resolve_cmd(cfg, "linux-agent-ansible-playbook", "ansible-playbook")
    if not ansible_cmd:
        return []

    cmd = [ansible_cmd, candidate, "-c", "local"]
    extra_vars = args.get("extra_vars") or {}
    if extra_vars:
        cmd += ["-e", json.dumps(extra_vars)]
    return _with_sudo(cfg, cmd)


def build_action_registry(cfg: Config) -> Dict[str, Action]:
    return {
        "read.os_release": Action("read.os_release", _validate_no_args, _cmd_os_release),
        "read.lsb_release": Action("read.lsb_release", _validate_no_args, _cmd_lsb_release),
        "read.packages": Action("read.packages", _validate_packages, _cmd_packages),
        "read.service_status": Action("read.service_status", _validate_service, _cmd_service_status),
        "read.service_enabled": Action("read.service_enabled", _validate_service, _cmd_service_enabled),
        "read.journalctl": Action("read.journalctl", _validate_journalctl, _cmd_journalctl),
        "read.ss_listen": Action("read.ss_listen", _validate_no_args, _cmd_ss_listen),
        "read.df": Action("read.df", _validate_no_args, _cmd_df),
        "read.free": Action("read.free", _validate_no_args, _cmd_free),
        "read.lsblk": Action("read.lsblk", _validate_no_args, _cmd_lsblk),
        "service.control": Action("service.control", _validate_service_control, _cmd_service_control, write_action=True),
        "pkg.install": Action("pkg.install", _validate_pkg_install, _cmd_pkg_install, write_action=True),
        "ansible.playbook": Action(
            "ansible.playbook",
            _validate_playbook,
            _cmd_ansible_playbook,
            timeout_override=cfg.ansible_timeout,
            write_action=True,
        ),
    }
