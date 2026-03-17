from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "merlin-ia"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_path(name: str) -> Path | None:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _xdg_dir(env_name: str, fallback: Path) -> Path:
    return _env_path(env_name) or fallback


def _writable_target(path: Path) -> Path:
    current = path if path.exists() else path.parent
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def _is_writable(path: Path) -> bool:
    target = _writable_target(path)
    return os.access(target, os.W_OK)


def storage_mode() -> str:
    explicit_mode = (os.getenv("MERLIN_STORAGE_MODE") or "").strip().lower()
    if explicit_mode in {"project", "user"}:
        return explicit_mode

    project_data = PROJECT_ROOT / "data"
    project_scrolls = PROJECT_ROOT / "scrolls"
    if (PROJECT_ROOT / ".git").exists() and _is_writable(project_data) and _is_writable(project_scrolls):
        return "project"
    return "user"


def data_dir() -> Path:
    explicit = _env_path("MERLIN_DATA_DIR")
    if explicit is not None:
        return explicit
    if storage_mode() == "project":
        return PROJECT_ROOT / "data"
    xdg_data = _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share")
    return xdg_data / APP_NAME


def state_dir() -> Path:
    explicit = _env_path("MERLIN_STATE_DIR")
    if explicit is not None:
        return explicit
    if storage_mode() == "project":
        return PROJECT_ROOT / "data"
    xdg_state = _xdg_dir("XDG_STATE_HOME", Path.home() / ".local" / "state")
    return xdg_state / APP_NAME


def scrolls_dir() -> Path:
    explicit = _env_path("MERLIN_SCROLLS_DIR")
    if explicit is not None:
        return explicit
    if storage_mode() == "project":
        return PROJECT_ROOT / "scrolls"
    return data_dir() / "scrolls"


def chroma_dir() -> Path:
    explicit = _env_path("MERLIN_CHROMA_DIR")
    if explicit is not None:
        return explicit
    return data_dir() / "chroma"


def history_path() -> Path:
    explicit = _env_path("MERLIN_HISTORY_PATH")
    if explicit is not None:
        return explicit
    return state_dir() / "history.jsonl"


def profile_path() -> Path:
    explicit = _env_path("MERLIN_PROFILE_PATH")
    if explicit is not None:
        return explicit
    return scrolls_dir() / "perfil_usuario.md"


def scrolls_manifest_path() -> Path:
    explicit = _env_path("MERLIN_SCROLLS_MANIFEST_PATH")
    if explicit is not None:
        return explicit
    return state_dir() / "scrolls_index.json"


def linux_actions_path() -> Path:
    explicit = _env_path("MERLIN_LINUX_ACTIONS_PATH")
    if explicit is not None:
        return explicit
    return state_dir() / "linux_actions.jsonl"


def linux_pending_path() -> Path:
    explicit = _env_path("MERLIN_LINUX_PENDING_PATH")
    if explicit is not None:
        return explicit
    return state_dir() / "linux_pending.json"


def audit_fallback_path() -> Path:
    explicit = _env_path("MERLIN_AUDIT_FALLBACK_PATH")
    if explicit is not None:
        return explicit
    return state_dir() / "merlin_audit.log"


def auto_index_scrolls_enabled() -> bool:
    raw = os.getenv("MERLIN_AUTO_INDEX_SCROLLS")
    if raw is None:
        return True
    return _truthy(raw)


def describe_paths() -> dict[str, str]:
    return {
        "storage_mode": storage_mode(),
        "project_root": str(PROJECT_ROOT),
        "data_dir": str(data_dir()),
        "state_dir": str(state_dir()),
        "scrolls_dir": str(scrolls_dir()),
        "history_path": str(history_path()),
        "chroma_dir": str(chroma_dir()),
        "profile_path": str(profile_path()),
        "scrolls_manifest_path": str(scrolls_manifest_path()),
        "linux_actions_path": str(linux_actions_path()),
        "linux_pending_path": str(linux_pending_path()),
        "audit_fallback_path": str(audit_fallback_path()),
    }
