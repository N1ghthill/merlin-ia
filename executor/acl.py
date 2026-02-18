from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Dict


@dataclass(frozen=True)
class ACL:
    allow_read: bool = True
    allow_write: bool = False


def resolve_acl(action_type: str) -> ACL:
    if action_type.startswith("read."):
        return ACL(allow_read=True, allow_write=False)
    if action_type in {"pkg.install", "service.control", "ansible.playbook"}:
        return ACL(allow_read=False, allow_write=True)
    return ACL(allow_read=False, allow_write=False)


def load_acl_policy(path: str) -> Dict[str, Dict[str, bool]]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    policy: Dict[str, Dict[str, bool]] = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        allow_read = bool(v.get("allow_read", False))
        allow_write = bool(v.get("allow_write", False))
        policy[str(k)] = {"allow_read": allow_read, "allow_write": allow_write}
    return policy


def parse_id_list(raw: str) -> set[int]:
    ids: set[int] = set()
    for tok in (raw or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok.isdigit():
            ids.add(int(tok))
    return ids


def is_action_allowed(action_type: str, allow_write_actions: bool, policy: Dict[str, Dict[str, bool]] | None = None) -> bool:
    if policy and action_type in policy:
        cfg = policy[action_type]
        acl = ACL(allow_read=bool(cfg.get("allow_read")), allow_write=bool(cfg.get("allow_write")))
    else:
        acl = resolve_acl(action_type)
    if acl.allow_write and not allow_write_actions:
        return False
    if acl.allow_read:
        return True
    return acl.allow_write and allow_write_actions
