"""Testes unitários para o indexador RAG."""

from __future__ import annotations

import json
from pathlib import Path

import rag_indexer


def test_chunk_text_vazio_retorna_lista_vazia():
    assert rag_indexer.chunk_text("") == []
    assert rag_indexer.chunk_text("   ") == []


def test_chunk_text_gera_chunks_com_overlap():
    text = "A" * (rag_indexer.CHUNK_SIZE + 200)
    chunks = rag_indexer.chunk_text(text)

    assert len(chunks) == 2
    assert len(chunks[0]) == rag_indexer.CHUNK_SIZE
    expected_second = text[rag_indexer.CHUNK_SIZE - rag_indexer.CHUNK_OVERLAP :]
    assert chunks[1] == expected_second


def test_read_history_messages_filtra_linhas_invalidas(tmp_path: Path):
    history = tmp_path / "history.jsonl"
    history.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "Pergunta", "ts": "2026-01-01T10:00:00"}),
                "{linha invalida",
                json.dumps({"role": "system", "content": "ignorar"}),
                json.dumps({"role": "assistant", "content": "Resposta", "ts": "2026-01-01T10:00:01"}),
                json.dumps({"role": "user", "content": 123}),
            ]
        ),
        encoding="utf-8",
    )

    messages = rag_indexer.read_history_messages(str(history))

    assert len(messages) == 2
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_read_scroll_files_ler_apenas_md_txt_e_ignorar_decode_error(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ok.txt").write_text("conteudo txt", encoding="utf-8")
    (tmp_path / "ok.md").write_text("# Titulo\nconteudo md", encoding="utf-8")
    (tmp_path / "ignorar.csv").write_text("a,b,c", encoding="utf-8")
    (tmp_path / "docs" / "invalido.md").write_bytes(b"\xff\xfe\xfd")

    files = rag_indexer.read_scroll_files(str(tmp_path))
    names = {Path(path).name for path, _ in files}

    assert "ok.txt" in names
    assert "ok.md" in names
    assert "ignorar.csv" not in names
    assert "invalido.md" not in names


def test_main_indexa_historico_e_scrolls(
    isolated_rag_paths,
    chroma_in_memory_collection,
    fake_embedder,
):
    data_dir = isolated_rag_paths["data_dir"]
    scrolls_dir = isolated_rag_paths["scrolls_dir"]
    history_path = isolated_rag_paths["history_path"]

    data_dir.mkdir(parents=True, exist_ok=True)
    scrolls_dir.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps({"role": "user", "content": "Memória do usuário", "ts": "2026-01-01T12:00:00"}) + "\n",
        encoding="utf-8",
    )
    (scrolls_dir / "sample.txt").write_text("Pergaminho de teste do Merlin IA.", encoding="utf-8")

    rag_indexer.main()

    assert chroma_in_memory_collection.count() > 0
    payload = chroma_in_memory_collection.get(include=["metadatas"])
    sources = {meta.get("source") for meta in payload.get("metadatas", []) if isinstance(meta, dict)}
    assert "history" in sources
    assert "scroll" in sources


def test_main_com_scroll_vazio_nao_quebra(
    isolated_rag_paths,
    chroma_in_memory_collection,
    fake_embedder,
):
    scrolls_dir = isolated_rag_paths["scrolls_dir"]
    scrolls_dir.mkdir(parents=True, exist_ok=True)
    (scrolls_dir / "empty.txt").write_text("", encoding="utf-8")

    rag_indexer.main()

    assert chroma_in_memory_collection.count() == 0
