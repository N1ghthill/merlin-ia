"""Testes de cobertura para executor/ e fluxos Linux do Merlin."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from executor.acl import is_action_allowed
from executor.actions import build_action_registry
from executor.audit import ensure_log_dir, log_event
from executor.config import Config, load_config
from executor.runner import _truncate, run_command
import executor.executor as executor_app
import merlin_cli


class _DummyRequest:
    def __init__(self, app, payload=None, json_exc: Exception | None = None):
        self.app = app
        self._payload = payload
        self._json_exc = json_exc
        self.transport = SimpleNamespace(get_extra_info=lambda *_a, **_k: None)

    async def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._payload


def _decode_json_response(resp):
    return json.loads(resp.body.decode("utf-8"))


def _make_app(cfg: Config, log_path: str):
    return {
        "config": cfg,
        "actions": build_action_registry(cfg),
        "log_path": log_path,
        "acl_policy": {},
    }


def test_diagnose_servico():
    cfg = Config(require_wrappers=False, use_sudo=False)
    actions = build_action_registry(cfg)
    cmd = actions["read.service_status"].build_cmd({"service": "nginx"}, cfg)
    assert cmd[:3] == ["systemctl", "status", "nginx"]


def test_diagnose_servico_inexistente():
    cfg = Config()
    actions = build_action_registry(cfg)
    ok, err = actions["read.service_status"].validate({"service": "nginx;rm -rf /"}, cfg)
    assert not ok
    assert "invalid service name" in err


def test_diagnose_com_linhas_limitadas():
    cfg = Config(require_wrappers=False, use_sudo=False)
    actions = build_action_registry(cfg)
    ok, _ = actions["read.journalctl"].validate({"service": "ssh", "lines": 30}, cfg)
    cmd = actions["read.journalctl"].build_cmd({"service": "ssh", "lines": 30}, cfg)
    assert ok
    assert "-n" in cmd and "30" in cmd


def test_install_package_dry_run(tmp_path: Path, monkeypatch):
    cfg = Config(require_peer_uid=False, require_wrappers=False, use_sudo=False)
    app = _make_app(cfg, str(tmp_path / "audit.jsonl"))
    req = _DummyRequest(app, payload={"type": "pkg.install", "args": {"packages": ["nginx"]}, "dry_run": True})
    events = []
    monkeypatch.setattr(executor_app, "log_event", lambda _p, event: events.append(event))
    resp = asyncio.run(executor_app.handle_run(req))
    body = _decode_json_response(resp)
    assert resp.status == 200
    assert body["dry_run"] is True
    assert events and events[0]["dry_run"] is True


def test_install_package_real(tmp_path: Path, monkeypatch):
    cfg = Config(require_peer_uid=False, require_wrappers=False, use_sudo=False, allow_write_actions=True)
    app = _make_app(cfg, str(tmp_path / "audit.jsonl"))
    req = _DummyRequest(app, payload={"type": "pkg.install", "args": {"packages": ["nginx"]}, "dry_run": False})

    async def _fake_run(cmd, timeout, max_output_bytes):
        return {"rc": 0, "stdout": "installed", "stderr": "", "cmd": " ".join(cmd)}

    monkeypatch.setattr(executor_app, "run_command", _fake_run)
    monkeypatch.setattr(executor_app, "log_event", lambda *_a, **_k: None)

    resp = asyncio.run(executor_app.handle_run(req))
    body = _decode_json_response(resp)
    assert resp.status == 200
    assert body["ok"] is True
    assert body["rc"] == 0


def test_install_package_ja_instalado(tmp_path: Path, monkeypatch):
    cfg = Config(require_peer_uid=False, require_wrappers=False, use_sudo=False, allow_write_actions=True)
    app = _make_app(cfg, str(tmp_path / "audit.jsonl"))
    req = _DummyRequest(app, payload={"type": "pkg.install", "args": {"packages": ["nginx"]}, "dry_run": False})

    async def _fake_run(cmd, timeout, max_output_bytes):
        return {"rc": 0, "stdout": "already the newest version", "stderr": ""}

    monkeypatch.setattr(executor_app, "run_command", _fake_run)
    monkeypatch.setattr(executor_app, "log_event", lambda *_a, **_k: None)
    resp = asyncio.run(executor_app.handle_run(req))
    body = _decode_json_response(resp)
    assert body["ok"] is True
    assert "newest" in body["stdout"]


def test_harden_ssh(tmp_path: Path, monkeypatch):
    playbook = tmp_path / "ssh_hardening.yml"
    playbook.write_text("- hosts: localhost\n  tasks: []\n", encoding="utf-8")
    cfg = Config(
        require_peer_uid=False,
        require_wrappers=False,
        use_sudo=False,
        allow_write_actions=True,
        playbooks_dir=str(tmp_path),
        ansible_preview_execute=True,
    )
    app = _make_app(cfg, str(tmp_path / "audit.jsonl"))
    req = _DummyRequest(
        app,
        payload={
            "type": "ansible.playbook",
            "args": {"playbook": "ssh_hardening.yml", "extra_vars": {"x": 1}},
            "dry_run": True,
        },
    )
    seen = {"cmd": []}

    async def _fake_run(cmd, timeout, max_output_bytes):
        seen["cmd"] = cmd
        return {"rc": 0, "stdout": "+linha\n-linha", "stderr": ""}

    monkeypatch.setattr(executor_app, "run_command", _fake_run)
    monkeypatch.setattr(executor_app, "log_event", lambda *_a, **_k: None)

    resp = asyncio.run(executor_app.handle_run(req))
    body = _decode_json_response(resp)
    assert body["preview_executed"] is True
    assert "--check" in seen["cmd"]
    assert "--diff" in seen["cmd"]


def test_harden_playbook_invalido(tmp_path: Path):
    cfg = Config(playbooks_dir=str(tmp_path))
    actions = build_action_registry(cfg)
    ok, _ = actions["ansible.playbook"].validate({"playbook": "../fora.yml"}, cfg)
    assert not ok


def test_confirm_execute_flow(tmp_path: Path, monkeypatch):
    cfg = Config(require_peer_uid=False, require_wrappers=False, use_sudo=False)
    app = _make_app(cfg, str(tmp_path / "audit.jsonl"))
    req = _DummyRequest(app, payload={"type": "read.os_release", "args": {}, "dry_run": False})

    async def _fake_run(cmd, timeout, max_output_bytes):
        return {"rc": 0, "stdout": "NAME=Ubuntu", "stderr": ""}

    monkeypatch.setattr(executor_app, "run_command", _fake_run)
    monkeypatch.setattr(executor_app, "log_event", lambda *_a, **_k: None)

    resp = asyncio.run(executor_app.handle_run(req))
    body = _decode_json_response(resp)
    assert body["ok"] is True
    assert body["rc"] == 0


def test_pending_actions_persistencia(tmp_path: Path):
    pending_path = tmp_path / "pending.json"
    payload = {"req-1": {"actions": [{"type": "pkg.install"}], "expires_at": merlin_cli.time.time() + 10}}
    merlin_cli.save_pending_actions(str(pending_path), payload)
    loaded = merlin_cli.load_pending_actions(str(pending_path))
    assert "req-1" in loaded


def test_is_action_allowed():
    assert is_action_allowed("read.os_release", allow_write_actions=False)
    assert not is_action_allowed("pkg.install", allow_write_actions=False)


def test_audit_log_registro(tmp_path: Path):
    log_path = ensure_log_dir(str(tmp_path))
    log_event(log_path, {"request_id": "req-1", "ok": True})
    lines = Path(log_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["request_id"] == "req-1"


def test_runner_truncate():
    data, trunc = _truncate(b"abcdef", 3)
    assert data == b"abc"
    assert trunc is True


def test_runner_run_command_ok():
    res = asyncio.run(run_command(["/bin/echo", "hello"], timeout=3, max_output_bytes=1024))
    assert res["rc"] == 0
    assert "hello" in res["stdout"]


def test_runner_run_command_not_found():
    res = asyncio.run(run_command(["/bin/this-command-does-not-exist"], timeout=1, max_output_bytes=64))
    assert res["rc"] in {127, -1}


def test_config_load_env(monkeypatch):
    monkeypatch.setenv("ALLOW_WRITE_ACTIONS", "true")
    monkeypatch.setenv("SOCK_MODE", "660")
    monkeypatch.setenv("DEFAULT_TIMEOUT", "120")
    cfg = load_config()
    assert cfg.allow_write_actions is True
    assert cfg.sock_mode == int("660", 8)
    assert cfg.default_timeout == 120


def test_mock_fixture_systemd(mock_systemd):
    import subprocess

    subprocess.run(["systemctl", "status", "nginx"])
    assert len(mock_systemd) >= 1


def test_mock_fixture_apt(mock_apt):
    import subprocess

    subprocess.run(["apt-get", "install", "--dry-run", "nginx"])
    assert len(mock_apt) >= 1


def test_executor_helpers_parse_and_diff(monkeypatch):
    raw = "NAME=Ubuntu\nVERSION=24.04\n"

    class _OpenCtx:
        def __enter__(self):
            from io import StringIO

            return StringIO(raw)

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("builtins.open", lambda *_a, **_k: _OpenCtx())
    distro = executor_app._parse_os_release()
    assert distro.get("NAME") == "Ubuntu"
    assert executor_app._diff_summary("+a\n-b\n--- x\n+++ y") == "+1 -1"


def test_handle_run_errors_e_reload_acl(tmp_path: Path, monkeypatch):
    cfg = Config(require_peer_uid=False, require_wrappers=False, use_sudo=False)
    app = _make_app(cfg, str(tmp_path / "audit.jsonl"))

    bad_json = _DummyRequest(app, json_exc=ValueError("bad json"))
    resp1 = asyncio.run(executor_app.handle_run(bad_json))
    assert resp1.status == 400

    missing_type = _DummyRequest(app, payload={"args": {}})
    resp2 = asyncio.run(executor_app.handle_run(missing_type))
    assert resp2.status == 400

    unknown = _DummyRequest(app, payload={"type": "nao.existe", "args": {}})
    resp3 = asyncio.run(executor_app.handle_run(unknown))
    assert resp3.status == 400

    monkeypatch.setattr(executor_app, "load_acl_policy", lambda *_a, **_k: {"read.os_release": {"allow_read": True}})
    reload_req = _DummyRequest(app, payload={})
    reload_resp = asyncio.run(executor_app.handle_reload_acl(reload_req))
    payload = _decode_json_response(reload_resp)
    assert payload["ok"] is True
    assert payload["count"] == 1
