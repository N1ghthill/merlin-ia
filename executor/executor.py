#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import pwd
import grp
import sys
import socket
import struct
from datetime import datetime
from typing import Dict

from aiohttp import web

if __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from executor.actions import build_action_registry, detect_package_manager
from executor.config import load_config
from executor.runner import run_command
from executor.audit import ensure_log_dir, log_event
from executor.acl import is_action_allowed, load_acl_policy, parse_id_list


def _parse_os_release() -> Dict[str, str]:
    distro: Dict[str, str] = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                distro[k] = v.strip().strip('"')
    except Exception:
        return {}
    return distro


async def handle_whoami(request: web.Request) -> web.Response:
    u = pwd.getpwuid(os.geteuid())
    g = grp.getgrgid(u.pw_gid)
    info = {
        "user": u.pw_name,
        "uid": os.geteuid(),
        "gid": u.pw_gid,
        "group": g.gr_name,
        "distro": _parse_os_release(),
        "pkg_mgr": detect_package_manager(),
    }
    return web.json_response({"ok": True, "whoami": info})

def _diff_summary(stdout: str) -> str:
    add = 0
    delete = 0
    for line in (stdout or "").splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            add += 1
        elif line.startswith("-"):
            delete += 1
    if add or delete:
        return f"+{add} -{delete}"
    return ""


def _check_peer(request: web.Request, cfg) -> tuple[bool, str, int | None, int | None]:
    if not cfg.require_peer_uid:
        return True, "", None, None
    try:
        peer_uids_raw = cfg.allowed_peer_uids
        allowed = set()
        for tok in (peer_uids_raw or "").split(","):
            tok = tok.strip()
            if not tok:
                continue
            if tok.isdigit():
                allowed.add(int(tok))
            else:
                try:
                    allowed.add(pwd.getpwnam(tok).pw_uid)
                except KeyError:
                    continue
        peer_gids_raw = cfg.allowed_peer_gids
        allowed_gids = set()
        for tok in (peer_gids_raw or "").split(","):
            tok = tok.strip()
            if not tok:
                continue
            if tok.isdigit():
                allowed_gids.add(int(tok))
            else:
                try:
                    allowed_gids.add(grp.getgrnam(tok).gr_gid)
                except KeyError:
                    continue
        if not allowed and not allowed_gids:
            return False, "no allowed peer ids configured", None, None
        peer = request.transport.get_extra_info("socket")
        if peer is None:
            return False, "no peer socket info", None, None
        ucred = peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, gid = struct.unpack("3i", ucred)
        if allowed and uid in allowed:
            return True, "", uid, gid
        if allowed_gids and gid in allowed_gids:
            return True, "", uid, gid
        return False, "peer uid/gid not allowed", uid, gid
    except Exception:
        return False, "peer verification failed", None, None


async def handle_run(request: web.Request) -> web.Response:
    cfg = request.app["config"]
    actions = request.app["actions"]
    log_path = request.app["log_path"]
    acl_policy = request.app.get("acl_policy") or {}

    ok_peer, peer_err, peer_uid, peer_gid = _check_peer(request, cfg)
    if not ok_peer:
        return web.json_response({"ok": False, "error": peer_err}, status=403)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    action_type = data.get("type")
    if not isinstance(action_type, str) or not action_type:
        return web.json_response({"ok": False, "error": "missing type"}, status=400)

    args = data.get("args") or {}
    if not isinstance(args, dict):
        return web.json_response({"ok": False, "error": "args must be an object"}, status=400)

    dry_run = bool(data.get("dry_run", True))
    request_id = data.get("request_id") or f"req-{datetime.utcnow().isoformat()}Z"

    action = actions.get(action_type)
    if not action:
        return web.json_response({"ok": False, "error": "unknown action"}, status=400)

    ok, err = action.validate(args, cfg)
    if not ok:
        return web.json_response({"ok": False, "error": err}, status=400)

    if cfg.acl_reload_on_each_request:
        acl_policy = load_acl_policy(cfg.acl_policy_path)

    if not is_action_allowed(action_type, cfg.allow_write_actions, acl_policy) and not dry_run:
        return web.json_response({"ok": False, "error": "action not allowed"}, status=403)

    if action.write_action and not dry_run:
        allow_uids = parse_id_list(cfg.allowed_write_uids)
        allow_gids = parse_id_list(cfg.allowed_write_gids)
        if allow_uids or allow_gids:
            if peer_uid is None or peer_gid is None:
                return web.json_response({"ok": False, "error": "peer identity unavailable"}, status=403)
            if allow_uids and peer_uid in allow_uids:
                pass
            elif allow_gids and peer_gid in allow_gids:
                pass
            else:
                return web.json_response({"ok": False, "error": "write not allowed for this uid/gid"}, status=403)

    cmd = action.build_cmd(args, cfg)
    if not cmd:
        return web.json_response({"ok": False, "error": "command unavailable"}, status=500)

    effective_dry_run = dry_run and action.write_action
    if effective_dry_run:
        preview_cmd = list(cmd)
        if action_type == "ansible.playbook":
            if "--check" not in preview_cmd:
                preview_cmd.append("--check")
            if "--diff" not in preview_cmd:
                preview_cmd.append("--diff")
            if cfg.ansible_preview_execute:
                res = await run_command(preview_cmd, timeout=cfg.ansible_timeout, max_output_bytes=cfg.max_output_bytes)
                diff = _diff_summary(res.get("stdout", ""))
                log_event(log_path, {
                    "request_id": request_id,
                    "type": action_type,
                    "args": args,
                    "dry_run": True,
                    "cmd": " ".join(preview_cmd),
                    "rc": res.get("rc"),
                    "preview_executed": True,
                    "diff_summary": diff or None,
                })
                payload = {"ok": True, "dry_run": True, "preview_executed": True, "cmd": " ".join(preview_cmd), **res}
                if diff:
                    payload["diff_summary"] = diff
                return web.json_response(payload)
        log_event(log_path, {
            "request_id": request_id,
            "type": action_type,
            "args": args,
            "dry_run": True,
            "cmd": " ".join(preview_cmd),
            "rc": None,
        })
        return web.json_response({"ok": True, "dry_run": True, "cmd": " ".join(preview_cmd)})

    timeout = action.timeout_override or cfg.default_timeout
    res = await run_command(cmd, timeout=timeout, max_output_bytes=cfg.max_output_bytes)

    log_event(log_path, {
        "request_id": request_id,
        "type": action_type,
        "args": args,
        "dry_run": False,
        "cmd": " ".join(cmd),
        "rc": res.get("rc"),
    })

    return web.json_response({"ok": True, "cmd": " ".join(cmd), **res})


async def handle_reload_acl(request: web.Request) -> web.Response:
    cfg = request.app["config"]
    ok_peer, peer_err, _, _ = _check_peer(request, cfg)
    if not ok_peer:
        return web.json_response({"ok": False, "error": peer_err}, status=403)
    policy = load_acl_policy(cfg.acl_policy_path)
    request.app["acl_policy"] = policy
    return web.json_response({"ok": True, "count": len(policy)})


async def _start_server() -> None:
    cfg = load_config()
    log_path = ensure_log_dir(cfg.log_dir)
    actions = build_action_registry(cfg)
    acl_policy = load_acl_policy(cfg.acl_policy_path)

    app = web.Application()
    app["config"] = cfg
    app["actions"] = actions
    app["log_path"] = log_path
    app["acl_policy"] = acl_policy

    app.router.add_get("/whoami", handle_whoami)
    app.router.add_post("/run", handle_run)
    app.router.add_post("/reload_acl", handle_reload_acl)

    runner = web.AppRunner(app)
    await runner.setup()
    site = None

    listen_fds = int(os.environ.get("LISTEN_FDS", "0") or "0")
    listen_pid = int(os.environ.get("LISTEN_PID", "0") or "0")
    if listen_fds >= 1 and listen_pid == os.getpid():
        sock = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
        site = web.SockSite(runner, sock)
        await site.start()
    else:
        if os.path.exists(cfg.sock_path):
            os.remove(cfg.sock_path)
        site = web.UnixSite(runner, path=cfg.sock_path)
        await site.start()
        try:
            os.chmod(cfg.sock_path, cfg.sock_mode)
        except Exception:
            pass

    print(f"linux-agent executor listening on {cfg.sock_path}")
    await asyncio.Event().wait()


def main() -> None:
    asyncio.run(_start_server())


if __name__ == "__main__":
    main()
