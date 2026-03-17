from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import merlin_api


def test_health_retorna_paths(monkeypatch):
    monkeypatch.setattr(merlin_api, "process_question", lambda question: f"ok:{question}")
    monkeypatch.setattr(merlin_api, "rag_indexer", SimpleNamespace(main=lambda: None))
    monkeypatch.setattr(merlin_api, "load_profile_content", lambda: "perfil carregado")
    monkeypatch.setattr(
        merlin_api,
        "describe_paths",
        lambda: {"storage_mode": "project", "scrolls_dir": "/tmp/scrolls"},
    )

    client = merlin_api.app.test_client()
    resp = client.get("/health")
    body = resp.get_json()

    assert resp.status_code == 200
    assert body["status"] == "alive"
    assert body["core_ready"] is True
    assert body["rag_ready"] is True
    assert body["profile_loaded"] is True
    assert body["paths"]["storage_mode"] == "project"


def test_ask_valida_payload_vazio():
    client = merlin_api.app.test_client()
    resp = client.post("/ask", json={"question": "   "})
    body = resp.get_json()

    assert resp.status_code == 400
    assert body["error"] == "Pergunta vazia"


def test_ask_retorna_resposta(monkeypatch):
    monkeypatch.setattr(merlin_api, "process_question", lambda question: f"Resposta para: {question}")

    client = merlin_api.app.test_client()
    resp = client.post("/ask", json={"question": "Oi"})
    body = resp.get_json()

    assert resp.status_code == 200
    assert body["status"] == "success"
    assert body["answer"] == "Resposta para: Oi"


def test_documents_lista_apenas_md_txt_e_marca_indexacao(tmp_path: Path, monkeypatch):
    scrolls = tmp_path / "scrolls"
    scrolls.mkdir()
    indexed = scrolls / "indexed.md"
    indexed.write_text("# doc\n", encoding="utf-8")
    note = scrolls / "note.txt"
    note.write_text("nota\n", encoding="utf-8")
    ignored = scrolls / "ignored.pdf"
    ignored.write_text("pdf\n", encoding="utf-8")

    monkeypatch.setattr(merlin_api, "scrolls_dir", lambda: scrolls)
    monkeypatch.setattr(
        merlin_api,
        "load_scrolls_manifest",
        lambda: {"files": {"scrolls/indexed.md": {"fp": "fp-indexed"}}},
    )
    monkeypatch.setattr(
        merlin_api,
        "relative_scroll_path",
        lambda path: f"scrolls/{Path(path).name}",
    )
    monkeypatch.setattr(
        merlin_api,
        "file_fingerprint",
        lambda path: "fp-indexed" if path.endswith("indexed.md") else "fp-other",
    )

    client = merlin_api.app.test_client()
    resp = client.get("/documents")
    body = resp.get_json()

    assert resp.status_code == 200
    assert [doc["name"] for doc in body["documents"]] == ["indexed.md", "note.txt"]
    assert body["documents"][0]["indexed"] is True
    assert body["documents"][1]["indexed"] is False


def test_index_dispara_reindex(monkeypatch):
    calls = []

    class _ImmediateThread:
        def __init__(self, target, daemon):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(merlin_api, "rag_indexer", SimpleNamespace(main=lambda: calls.append("reindexed")))
    monkeypatch.setattr(merlin_api.threading, "Thread", _ImmediateThread)

    client = merlin_api.app.test_client()
    resp = client.post("/index")
    body = resp.get_json()

    assert resp.status_code == 200
    assert body["status"] == "indexing_started"
    assert calls == ["reindexed"]
