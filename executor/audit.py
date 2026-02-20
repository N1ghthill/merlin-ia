from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional


def ensure_log_dir(log_dir: str) -> str:
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "executor.jsonl")
    # Touch file to ensure it's writable.
    with open(log_path, "a", encoding="utf-8"):
        pass
    return log_path


def log_event(log_path: str, event: Dict[str, object]) -> None:
    payload = dict(event)
    payload.setdefault("ts", datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
