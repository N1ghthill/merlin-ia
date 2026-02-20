"""Fixtures compartilhadas para os testes de RAG."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

import pytest


class _FakeEmbeddings:
    def __init__(self, vectors: List[List[float]]):
        self._vectors = vectors

    def tolist(self) -> List[List[float]]:
        return self._vectors


class FakeEmbedder:
    """Embedder determinístico para testes, sem download de modelo."""

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> _FakeEmbeddings:
        vectors: List[List[float]] = []
        for text in texts:
            clean = (text or "").strip()
            vectors.append([float(len(clean)), float(max(1, len(clean.split()))), 1.0])
        return _FakeEmbeddings(vectors)


@pytest.fixture
def isolated_rag_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Path]:
    """Isola os caminhos usados pelo RAG para diretórios temporários."""
    import merlin_cli
    import rag_indexer

    data_dir = tmp_path / "data"
    scrolls_dir = tmp_path / "scrolls"
    chroma_dir = data_dir / "chroma"
    history_path = data_dir / "history.jsonl"
    profile_path = scrolls_dir / "perfil_usuario.md"
    manifest_path = data_dir / "scrolls_index.json"
    linux_actions_path = data_dir / "linux_actions.jsonl"
    linux_pending_path = data_dir / "linux_pending.json"
    audit_fallback_path = data_dir / "merlin_audit.log"

    for module in (rag_indexer, merlin_cli):
        monkeypatch.setattr(module, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(module, "SCROLLS_DIR", str(scrolls_dir))
        monkeypatch.setattr(module, "CHROMA_DIR", str(chroma_dir))
        monkeypatch.setattr(module, "HISTORY_PATH", str(history_path))
        if hasattr(module, "PROFILE_PATH"):
            monkeypatch.setattr(module, "PROFILE_PATH", str(profile_path))
        if hasattr(module, "SCROLLS_MANIFEST_PATH"):
            monkeypatch.setattr(module, "SCROLLS_MANIFEST_PATH", str(manifest_path))
        if hasattr(module, "LINUX_ACTIONS_PATH"):
            monkeypatch.setattr(module, "LINUX_ACTIONS_PATH", str(linux_actions_path))
        if hasattr(module, "LINUX_PENDING_PATH"):
            monkeypatch.setattr(module, "LINUX_PENDING_PATH", str(linux_pending_path))
        if hasattr(module, "AUDIT_LOG_FALLBACK_PATH"):
            monkeypatch.setattr(module, "AUDIT_LOG_FALLBACK_PATH", str(audit_fallback_path))

    return {
        "tmp_path": tmp_path,
        "data_dir": data_dir,
        "scrolls_dir": scrolls_dir,
        "chroma_dir": chroma_dir,
        "history_path": history_path,
        "profile_path": profile_path,
        "manifest_path": manifest_path,
        "linux_actions_path": linux_actions_path,
        "linux_pending_path": linux_pending_path,
        "audit_fallback_path": audit_fallback_path,
    }


@pytest.fixture
def chroma_in_memory_collection(monkeypatch: pytest.MonkeyPatch):
    """Coleção ChromaDB em memória compartilhada pelos testes."""
    import chromadb
    import uuid
    import merlin_cli
    import rag_indexer

    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(name=f"merlin_memory_{uuid.uuid4().hex}")

    monkeypatch.setattr(rag_indexer, "get_collection", lambda: collection)
    monkeypatch.setattr(merlin_cli, "get_collection", lambda: collection)
    return collection


@pytest.fixture
def fake_embedder(monkeypatch: pytest.MonkeyPatch) -> FakeEmbedder:
    """Substitui SentenceTransformer por um embedder leve/determinístico."""
    import merlin_cli
    import rag_indexer

    embedder = FakeEmbedder()
    monkeypatch.setattr(rag_indexer, "SentenceTransformer", lambda *_a, **_k: embedder)
    monkeypatch.setattr(merlin_cli, "SentenceTransformer", lambda *_a, **_k: embedder)
    return embedder


@pytest.fixture
def mock_ollama(monkeypatch: pytest.MonkeyPatch):
    """Mock de `ollama.chat` para testes sem serviço Ollama rodando."""
    import merlin_cli

    calls = []

    def _fake_chat(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        if kwargs.get("stream"):
            return iter(
                [
                    {"message": {"content": "Resposta "}},
                    {"message": {"content": "mockada"}},
                ]
            )
        return {"message": {"content": "Resposta mockada"}}

    monkeypatch.setattr(merlin_cli.ollama, "chat", _fake_chat)
    return calls


@pytest.fixture
def mock_systemd(monkeypatch: pytest.MonkeyPatch):
    """Mock para comandos systemctl."""
    import subprocess

    calls: List[List[str] | str] = []

    def _run(cmd, *args, **kwargs):
        calls.append(cmd)
        text = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        if "status" in text:
            return SimpleNamespace(returncode=0, stdout="active (running)", stderr="")
        if "is-enabled" in text:
            return SimpleNamespace(returncode=0, stdout="enabled", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    return calls


@pytest.fixture
def mock_apt(monkeypatch: pytest.MonkeyPatch):
    """Mock para comandos apt."""
    import subprocess

    calls: List[List[str] | str] = []

    def _run(cmd, *args, **kwargs):
        calls.append(cmd)
        text = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        if "--dry-run" in text:
            return SimpleNamespace(returncode=0, stdout="0 upgraded, 1 newly installed", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    return calls


@pytest.fixture
def mock_audit_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock para arquivo de auditoria usado pelo Merlin CLI."""
    import merlin_cli

    log_file = tmp_path / "audit.log"
    monkeypatch.setattr(merlin_cli, "AUDIT_LOG_DEFAULT_PATH", str(log_file))
    monkeypatch.setattr(merlin_cli, "AUDIT_LOG_FALLBACK_PATH", str(log_file))
    return log_file
