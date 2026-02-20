"""Testes unitários para merlin_cli.py."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import merlin_cli


class _DummyResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _patch_inputs(monkeypatch, values):
    it = iter(values)

    def _fake_input(_prompt: str = "") -> str:
        try:
            return next(it)
        except StopIteration as exc:
            raise EOFError from exc

    monkeypatch.setattr("builtins.input", _fake_input)


def _prepare_main_defaults(monkeypatch):
    monkeypatch.setattr(merlin_cli, "get_collection", lambda: SimpleNamespace(count=lambda: 0))
    monkeypatch.setattr(merlin_cli, "retrieve_context", lambda *_a, **_k: {"documents": [[]], "metadatas": [[]]})
    monkeypatch.setattr(merlin_cli, "index_message_incremental", lambda *_a, **_k: None)
    monkeypatch.setattr(merlin_cli, "stream_chat", lambda *_a, **_k: "Resposta de teste")
    monkeypatch.setattr(merlin_cli, "run_reindex", lambda: True)
    monkeypatch.setattr(merlin_cli, "index_scrolls_incremental", lambda *_a, **_k: (1, 2))


def test_ensure_dirs_cria_estrutura(isolated_rag_paths):
    merlin_cli.ensure_dirs()
    assert isolated_rag_paths["data_dir"].exists()
    assert isolated_rag_paths["scrolls_dir"].exists()
    assert isolated_rag_paths["chroma_dir"].exists()


def test_now_iso_tem_formato_iso():
    ts = merlin_cli.now_iso()
    assert "T" in ts
    assert len(ts) >= 19


def test_append_jsonl_e_load_history(isolated_rag_paths):
    history_path = isolated_rag_paths["history_path"]
    history_path.parent.mkdir(parents=True, exist_ok=True)
    merlin_cli.append_jsonl(str(history_path), {"role": "user", "content": "Olá"})
    merlin_cli.append_jsonl(str(history_path), {"role": "assistant", "content": "Oi"})
    items = merlin_cli.load_history(str(history_path))
    assert len(items) == 2
    assert items[0]["role"] == "user"


def test_resolve_audit_log_path_com_fallback(monkeypatch, tmp_path: Path):
    preferred = tmp_path / "preferred.log"
    fallback = tmp_path / "fallback.log"
    calls = {"n": 0}

    def _touch(path: str) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("nope")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).touch()

    monkeypatch.setattr(merlin_cli, "_touch_path", _touch)
    chosen, warning = merlin_cli.resolve_audit_log_path(str(preferred), str(fallback))
    assert chosen == str(fallback)
    assert "usando" in (warning or "")


def test_resolve_audit_log_path_falha_total(monkeypatch, tmp_path: Path):
    preferred = tmp_path / "preferred.log"
    fallback = tmp_path / "fallback.log"
    monkeypatch.setattr(merlin_cli, "_touch_path", lambda *_a, **_k: (_ for _ in ()).throw(PermissionError("nope")))
    chosen, warning = merlin_cli.resolve_audit_log_path(str(preferred), str(fallback))
    assert chosen is None
    assert "Auditoria indisponível" in (warning or "")


def test_get_confirm_user_subprocess(monkeypatch):
    monkeypatch.setattr(
        merlin_cli.subprocess,
        "run",
        lambda *_a, **_k: _DummyResult(returncode=0, stdout="irving\n"),
    )
    assert merlin_cli.get_confirm_user() == "irving"


def test_get_confirm_user_fallback_getpass(monkeypatch):
    def _raise(*_a, **_k):
        raise RuntimeError("fail")

    monkeypatch.setattr(merlin_cli.subprocess, "run", _raise)
    monkeypatch.setattr(merlin_cli.getpass, "getuser", lambda: "fallback-user")
    assert merlin_cli.get_confirm_user() == "fallback-user"


def test_get_confirm_user_unknown_quando_tudo_falha(monkeypatch):
    def _raise(*_a, **_k):
        raise RuntimeError("fail")

    monkeypatch.setattr(merlin_cli.subprocess, "run", _raise)
    monkeypatch.setattr(merlin_cli.getpass, "getuser", _raise)
    assert merlin_cli.get_confirm_user() == "unknown"


def test_log_audit_event_escreve_ts(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    merlin_cli.log_audit_event(str(log_path), {"request_id": "req-1"})
    line = log_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["request_id"] == "req-1"
    assert "ts" in payload


def test_audit_execute_results_gera_registros(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    actions = [{"type": "pkg.install", "args": {"packages": ["nginx"]}}]
    results = [{"cmd": "apt-get install nginx", "rc": 0, "ok": True}]
    merlin_cli.audit_execute_results(str(log_path), "req-1", actions, results, "tester")
    payload = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert payload["action_type"] == "pkg.install"
    assert payload["confirmed_by"] == "tester"


def test_list_processes_parseia_saida(monkeypatch):
    output = "PID PPID COMMAND\n1 0 init\n200 1 /usr/bin/python\n"
    monkeypatch.setattr(merlin_cli.subprocess, "run", lambda *_a, **_k: _DummyResult(stdout=output))
    items = merlin_cli._list_processes()
    assert (200, 1, "/usr/bin/python") in items


def test_list_processes_quando_subprocess_falha(monkeypatch):
    monkeypatch.setattr(
        merlin_cli.subprocess,
        "run",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("falhou")),
    )
    assert merlin_cli._list_processes() == []


def test_list_processes_ignora_linhas_invalidas(monkeypatch):
    output = "PID PPID COMMAND\nlinha invalida\nx y z\n"
    monkeypatch.setattr(merlin_cli.subprocess, "run", lambda *_a, **_k: _DummyResult(stdout=output))
    assert merlin_cli._list_processes() == []


def test_find_executor_pids_systemctl_ok(monkeypatch):
    def _run(cmd, *args, **kwargs):
        if cmd[:2] == ["systemctl", "show"]:
            return _DummyResult(returncode=0, stdout="123\n")
        return _DummyResult(returncode=0, stdout="")

    monkeypatch.setattr(merlin_cli.subprocess, "run", _run)
    pids = merlin_cli._find_executor_pids([(10, 1, "executor.executor")])
    assert pids == [123]


def test_find_executor_pids_via_lista_processos(monkeypatch):
    monkeypatch.setattr(merlin_cli.subprocess, "run", lambda *_a, **_k: _DummyResult(returncode=1, stdout="0"))
    pids = merlin_cli._find_executor_pids([(50, 1, "python executor.executor"), (51, 1, "other")])
    assert pids == [50]


def test_collect_descendants():
    proc = [(10, 1, "a"), (20, 10, "b"), (21, 10, "c"), (30, 20, "d")]
    desc = merlin_cli._collect_descendants(proc, [10])
    assert desc == [20, 21, 30]


def test_kill_executor_children_executor_inexistente(monkeypatch):
    monkeypatch.setattr(merlin_cli, "_list_processes", lambda: [(1, 0, "init")])
    monkeypatch.setattr(merlin_cli, "_find_executor_pids", lambda _p: [])
    out = merlin_cli.kill_executor_children()
    assert out["attempted"] == 0
    assert "executor not running" in out["errors"][0]


def test_kill_executor_children_fluxo_de_kill(monkeypatch):
    monkeypatch.setattr(merlin_cli, "_list_processes", lambda: [(1, 0, "init"), (10, 1, "exec"), (20, 10, "child")])
    monkeypatch.setattr(merlin_cli, "_find_executor_pids", lambda _p: [10])
    monkeypatch.setattr(merlin_cli, "_collect_descendants", lambda _p, _r: [20])
    kills = []

    def _kill(pid, sig):
        kills.append((pid, sig))
        if sig == 0:
            return None

    monkeypatch.setattr(merlin_cli.os, "kill", _kill)
    monkeypatch.setattr(merlin_cli.time, "sleep", lambda *_a, **_k: None)
    out = merlin_cli.kill_executor_children()
    assert out["attempted"] == 1
    assert out["killed"] == 1
    assert len(kills) >= 2


def test_truncate_e_summarize_linux_result():
    txt = "x" * 20
    assert "[truncated at 5 chars]" in merlin_cli._truncate_text(txt, 5)

    res = merlin_cli._summarize_linux_result(
        {"ok": True, "stdout": "abcde12345", "stderr": "erro12345", "rc": 0},
        max_chars=5,
    )
    assert "stdout" in res and "[truncated at 5 chars]" in res["stdout"]
    assert "stderr" in res and "[truncated at 5 chars]" in res["stderr"]


def test_service_missing_e_skip_enable():
    missing = {"stdout": "Unit xyz could not be found", "stderr": ""}
    assert merlin_cli._service_unit_missing(missing)

    class _LinuxTool:
        def run(self, *_a, **_k):
            return missing

    assert merlin_cli._should_skip_service_enable(_LinuxTool(), "nginx", "req-1")
    assert not merlin_cli._service_unit_missing("invalid")
    assert not merlin_cli._should_skip_service_enable(_LinuxTool(), "", "req-1")


def test_impact_summary_e_diff_summary():
    actions = [
        {"type": "pkg.install", "args": {"packages": ["nginx"]}},
        {"type": "service.control", "args": {"service": "nginx", "operation": "restart"}},
    ]
    results = [{"cmd": "apt install nginx", "stdout": "+a\n-b\n--- x\n+++ y"}]
    lines = merlin_cli.impact_summary(actions, results, max_cmd_chars=20)
    assert any("Risco estimado" in line for line in lines)
    assert merlin_cli.diff_summary(results) == "Preview diff: +1 -1 (ansible --diff)"
    assert merlin_cli.diff_summary([{"stdout": "sem diff"}]) is None


def test_record_tail_pending_history_helpers(tmp_path: Path):
    log_path = tmp_path / "linux_actions.jsonl"
    merlin_cli.record_linux_results(
        str(log_path),
        "req-1",
        [{"type": "read.os_release", "args": {}}],
        [{"ok": True, "stdout": "ok"}],
        mode="diagnose",
        max_chars=100,
    )
    items = merlin_cli.tail_linux_actions(str(log_path), n=5)
    assert len(items) == 1

    pending_path = tmp_path / "pending.json"
    merlin_cli.save_pending_actions(
        str(pending_path),
        {"req-1": {"actions": [{"type": "read.os_release"}], "expires_at": merlin_cli.time.time() + 50}},
    )
    loaded = merlin_cli.load_pending_actions(str(pending_path))
    assert "req-1" in loaded
    cleaned = merlin_cli.cleanup_pending_actions({"a": {"expires_at": 0}, "b": {"expires_at": merlin_cli.time.time() + 10}})
    assert "b" in cleaned and "a" not in cleaned


def test_format_index_linux_action_e_index(monkeypatch, fake_embedder):
    calls = []

    class _Col:
        def add(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(merlin_cli, "get_collection", lambda: _Col())
    monkeypatch.setattr(merlin_cli, "ensure_embedder", lambda _cache: fake_embedder)
    text = merlin_cli.format_linux_action_for_index(
        "req-1",
        "dry_run",
        [{"type": "read.os_release", "args": {}}],
        [{"ok": True, "stdout": "ok"}],
        max_chars=100,
    )
    assert "LINUX_ACTION" in text
    merlin_cli.index_linux_action(
        {},
        request_id="req-1",
        mode="dry_run",
        actions=[{"type": "read.os_release", "args": {}}],
        results=[{"ok": True, "stdout": "ok"}],
        max_chars=100,
    )
    assert calls


def test_profile_helpers(isolated_rag_paths):
    profile_path = isolated_rag_paths["profile_path"]
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    raw = "# PERFIL_USUARIO\nnome: Merlin\npreferencia_desenvolvimento: clean code\n"
    profile_path.write_text(raw, encoding="utf-8")
    data, text = merlin_cli.load_profile()
    assert data["nome"] == "Merlin"
    assert "PERFIL_USUARIO" in text

    merlin_cli.write_profile({"nome": "Iris"})
    assert "nome: Iris" in profile_path.read_text(encoding="utf-8")
    block = merlin_cli.build_profile_block({"nome": "Iris"})
    assert "PERFIL_USUARIO" in block
    wants = merlin_cli.match_profile_question("qual é meu nome e minha preferência?")
    assert "nome" in wants
    answer = merlin_cli.answer_from_profile({"nome": "Iris"}, ["nome", "preferencia_desenvolvimento"])
    assert "Iris" in answer


def test_run_reindex_missing_file(monkeypatch):
    monkeypatch.setattr(merlin_cli.os.path, "exists", lambda _p: False)
    assert not merlin_cli.run_reindex()


def test_run_reindex_sucesso(monkeypatch):
    monkeypatch.setattr(merlin_cli.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(merlin_cli.subprocess, "run", lambda *_a, **_k: _DummyResult(returncode=0))
    assert merlin_cli.run_reindex()


def test_run_reindex_retorno_nao_zero(monkeypatch):
    monkeypatch.setattr(merlin_cli.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(merlin_cli.subprocess, "run", lambda *_a, **_k: _DummyResult(returncode=2))
    assert not merlin_cli.run_reindex()


def test_run_reindex_com_excecao(monkeypatch):
    monkeypatch.setattr(merlin_cli.os.path, "exists", lambda _p: True)

    def _raise(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(merlin_cli.subprocess, "run", _raise)
    assert not merlin_cli.run_reindex()


def test_get_collection_configura_chroma(monkeypatch):
    captured = {}

    class _FakeClient:
        def __init__(self, path, settings):
            captured["path"] = path
            captured["settings"] = settings

        def get_or_create_collection(self, name):
            captured["name"] = name
            return {"collection": name}

    monkeypatch.setattr(merlin_cli.chromadb, "PersistentClient", _FakeClient)
    col = merlin_cli.get_collection()
    assert col == {"collection": "merlin_memory"}
    assert captured["path"] == merlin_cli.CHROMA_DIR
    assert captured["name"] == "merlin_memory"


def test_build_rag_block_com_docs_invalidos():
    result = {
        "documents": [["", "texto válido"]],
        "metadatas": [["meta inválida", {"source": "custom"}]],
    }
    block = merlin_cli.build_rag_block(result)
    assert "custom" in block


def test_load_scrolls_manifest_variacoes(isolated_rag_paths):
    manifest_path = isolated_rag_paths["manifest_path"]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_path.write_text("[]", encoding="utf-8")
    assert merlin_cli.load_scrolls_manifest() == {"files": {}}

    manifest_path.write_text('{"qualquer": 1}', encoding="utf-8")
    assert merlin_cli.load_scrolls_manifest() == {"qualquer": 1, "files": {}}

    manifest_path.write_text("{json invalido", encoding="utf-8")
    assert merlin_cli.load_scrolls_manifest() == {"files": {}}


def test_manifest_scrolls_e_indexacao(isolated_rag_paths, chroma_in_memory_collection, fake_embedder):
    isolated_rag_paths["data_dir"].mkdir(parents=True, exist_ok=True)
    scrolls_dir = isolated_rag_paths["scrolls_dir"]
    scrolls_dir.mkdir(parents=True, exist_ok=True)
    (scrolls_dir / "doc.md").write_text("conteudo de scroll", encoding="utf-8")

    files_idx, chunks = merlin_cli.index_scrolls_incremental({}, include_profile=False)
    assert files_idx == 1
    assert chunks > 0

    files_idx2, chunks2 = merlin_cli.index_scrolls_incremental({}, include_profile=False)
    assert files_idx2 == 0
    assert chunks2 == 0


def test_cmd_help_imprime_comandos(capsys):
    merlin_cli.cmd_help(linux_enabled=True)
    out = capsys.readouterr().out
    assert "/help" in out
    assert "/linux" in out


def test_main_sem_argumentos(monkeypatch, isolated_rag_paths, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "0")
    _patch_inputs(monkeypatch, ["exit"])
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "Merlin IA" in out
    assert "Até logo." in out


def test_main_comandos_basicos(monkeypatch, isolated_rag_paths, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "0")
    _patch_inputs(monkeypatch, ["/help", "/where", "/set nome Iris", "/profile", "/stats", "/reset", "exit"])
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "Comandos:" in out
    assert "Perfil atualizado" in out
    assert "Contexto em memória limpo" in out


def test_main_set_invalido(monkeypatch, isolated_rag_paths, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "0")
    _patch_inputs(monkeypatch, ["/set chave_sem_valor", "exit"])
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "Uso: /set chave valor" in out


def test_main_comando_desconhecido_vai_fluxo_normal(monkeypatch, isolated_rag_paths, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "0")
    _patch_inputs(monkeypatch, ["pergunta comum", "/sources", "exit"])
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "Merlin>" in out


def test_main_intercepta_pergunta_de_perfil(monkeypatch, isolated_rag_paths, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "0")
    isolated_rag_paths["profile_path"].parent.mkdir(parents=True, exist_ok=True)
    isolated_rag_paths["profile_path"].write_text("# PERFIL_USUARIO\nnome: Aline\n", encoding="utf-8")
    _patch_inputs(monkeypatch, ["qual é meu nome?", "exit"])
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "seu nome é **Aline**" in out


def test_main_executor_desativado_para_linux(monkeypatch, isolated_rag_paths, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "0")
    _patch_inputs(monkeypatch, ["/linux read.os_release {}", "CONFIRM EXECUTE req-x", "exit"])
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "Executor Linux desativado" in out


def test_main_linux_fluxo_completo(monkeypatch, isolated_rag_paths, mock_audit_log, capsys):
    _prepare_main_defaults(monkeypatch)
    monkeypatch.setenv("MERLIN_ENABLE_EXECUTOR", "1")

    class _Resp:
        def json(self):
            return {"ok": True, "count": 1}

    class _FakeLinuxTool:
        def __init__(self):
            self.base = "http://linux-agent.local"
            self.calls = []
            self.session = SimpleNamespace(post=lambda *_a, **_k: _Resp())

        def whoami(self):
            return {"ok": True, "whoami": {"user": "tester"}}

        def run(self, action_type, args=None, dry_run=True, request_id=None):
            payload = {"type": action_type, "args": args or {}, "dry_run": dry_run, "request_id": request_id}
            self.calls.append(payload)
            if action_type == "read.service_status" and dry_run is False:
                return {
                    "ok": False,
                    "rc": 4,
                    "stdout": "Unit nginx could not be found",
                    "stderr": "unit not found",
                    "cmd": "systemctl status nginx",
                }
            return {
                "ok": True,
                "dry_run": dry_run,
                "rc": 0,
                "stdout": "+line\n-line",
                "stderr": "",
                "cmd": f"{action_type} {args or {}}",
            }

    seq = {"n": 0}

    def _uuid4():
        seq["n"] += 1
        return f"req-{seq['n']}"

    monkeypatch.setattr(merlin_cli, "LinuxTool", _FakeLinuxTool)
    monkeypatch.setattr(merlin_cli.uuid, "uuid4", _uuid4)
    monkeypatch.setattr(
        merlin_cli,
        "detect_intent",
        lambda text: {"intent": "diagnose", "service": "nginx", "lines": 10} if text == "auto diag" else None,
    )
    _patch_inputs(
        monkeypatch,
        [
            "/linux-install nginx apt",
            "/linux-pending show req-1",
            "/linux-exec CONFIRM EXECUTE req-1",
            "/linux whoami",
            "/linux read.os_release {}",
            "/linux read.os_release {invalid",
            "/linux-reload-acl",
            "/linux-history 5",
            "/linux-audit 5",
            "/linux-auto status",
            "/linux-auto on",
            "auto diag",
            "/linux-lockdown",
            "/linux-exec CONFIRM EXECUTE req-2",
            "exit",
        ],
    )
    merlin_cli.main()
    out = capsys.readouterr().out
    assert "Ações pendentes registradas" in out
    assert "Lockdown ativado" in out
    assert "Linux read-only mode ativo" in out
    assert mock_audit_log.exists()
