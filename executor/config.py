from __future__ import annotations

from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_octal(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val, 8)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    sock_path: str = "/run/linux-agent/agent.sock"
    sock_mode: int = 0o660
    log_dir: str = "/var/log/linux-agent"
    allow_write_actions: bool = False
    use_sudo: bool = True
    sudo_bin: str = "/usr/bin/sudo"
    wrappers_dir: str = "/opt/linux-agent/wrappers"
    require_wrappers: bool = True
    require_peer_uid: bool = True
    allowed_peer_uids: str = "linux-agent"
    allowed_peer_gids: str = ""
    acl_policy_path: str = "/opt/linux-agent/acl_policy.json"
    acl_reload_on_each_request: bool = False
    allowed_write_uids: str = ""
    allowed_write_gids: str = ""
    max_output_bytes: int = 1024 * 1024
    default_timeout: int = 300
    ansible_timeout: int = 900
    playbooks_dir: str = "/opt/linux-agent/playbooks"
    ansible_preview_execute: bool = False


def load_config() -> Config:
    return Config(
        sock_path=os.getenv("SOCK_PATH", Config.sock_path),
        sock_mode=_env_octal("SOCK_MODE", Config.sock_mode),
        log_dir=os.getenv("LOG_DIR", Config.log_dir),
        allow_write_actions=_env_bool("ALLOW_WRITE_ACTIONS", Config.allow_write_actions),
        use_sudo=_env_bool("USE_SUDO", Config.use_sudo),
        sudo_bin=os.getenv("SUDO_BIN", Config.sudo_bin),
        wrappers_dir=os.getenv("WRAPPERS_DIR", Config.wrappers_dir),
        require_wrappers=_env_bool("REQUIRE_WRAPPERS", Config.require_wrappers),
        require_peer_uid=_env_bool("REQUIRE_PEER_UID", Config.require_peer_uid),
        allowed_peer_uids=os.getenv("ALLOWED_PEER_UIDS", Config.allowed_peer_uids),
        allowed_peer_gids=os.getenv("ALLOWED_PEER_GIDS", Config.allowed_peer_gids),
        acl_policy_path=os.getenv("ACL_POLICY_PATH", Config.acl_policy_path),
        acl_reload_on_each_request=_env_bool("ACL_RELOAD_ON_EACH_REQUEST", Config.acl_reload_on_each_request),
        allowed_write_uids=os.getenv("ALLOWED_WRITE_UIDS", Config.allowed_write_uids),
        allowed_write_gids=os.getenv("ALLOWED_WRITE_GIDS", Config.allowed_write_gids),
        max_output_bytes=_env_int("MAX_OUTPUT_BYTES", Config.max_output_bytes),
        default_timeout=_env_int("DEFAULT_TIMEOUT", Config.default_timeout),
        ansible_timeout=_env_int("ANSIBLE_TIMEOUT", Config.ansible_timeout),
        playbooks_dir=os.getenv("PLAYBOOKS_DIR", Config.playbooks_dir),
        ansible_preview_execute=_env_bool("ANSIBLE_PREVIEW_EXECUTE", Config.ansible_preview_execute),
    )
