from __future__ import annotations

import re
from typing import Any, Dict, Optional


DIAG_RE = re.compile(r"(status|estado|logs?)\s+(?:do|da|de)\s+([a-zA-Z0-9@._:-]+)", re.IGNORECASE)
INSTALL_RE = re.compile(r"(instalar|instale|instala|instal(ar|e))\s+([a-zA-Z0-9@._:-]+)", re.IGNORECASE)
LINES_RE = re.compile(r"(?:ultim[oa]s?\s+)?(\d+)\s*(?:linhas|eventos)", re.IGNORECASE)


def _extract_manager(text: str) -> str:
    t = text.lower()
    for mgr in ("apt", "dnf", "yum", "pacman"):
        if mgr in t:
            return mgr
    return "auto"


def _extract_lines(text: str, default: int = 200) -> int:
    m = LINES_RE.search(text)
    if not m:
        return default
    try:
        val = int(m.group(1))
    except ValueError:
        return default
    return max(1, min(500, val))


def detect_intent(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = text.strip()
    if not t or t.startswith("/"):
        return None

    # Diagnose intent
    m = DIAG_RE.search(t)
    if m:
        service = m.group(2)
        return {
            "intent": "diagnose",
            "service": service,
            "lines": _extract_lines(t, default=200),
        }

    # Install intent
    m = INSTALL_RE.search(t)
    if m:
        service = m.group(3)
        return {
            "intent": "install",
            "service": service,
            "manager": _extract_manager(t),
        }

    # Hardening intent
    t_low = t.lower()
    if "ssh" in t_low and ("hardening" in t_low or "segur" in t_low or "endurec" in t_low):
        return {"intent": "harden", "target": "ssh"}
    if "firewall" in t_low or "ufw" in t_low:
        return {"intent": "harden", "target": "firewall"}

    return None
