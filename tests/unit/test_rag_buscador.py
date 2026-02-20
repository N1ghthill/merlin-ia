"""Testes unitários para busca e montagem de contexto RAG."""

from __future__ import annotations

import merlin_cli


def test_retrieve_context_sem_dados_retorna_estruturas_vazias(chroma_in_memory_collection):
    result = merlin_cli.retrieve_context("qualquer termo", embedder_cache={}, top_k=3)
    assert result == {"documents": [[]], "metadatas": [[]]}


def test_busca_por_termo_conhecido(
    chroma_in_memory_collection,
    fake_embedder,
):
    cache = {}
    merlin_cli.index_message_incremental(
        cache,
        role="user",
        text="O Merlin IA é um assistente local. Ele usa RAG.",
        ts="2026-01-02T09:00:00",
    )

    result = merlin_cli.retrieve_context("assistente local", cache, top_k=3)
    docs = (result.get("documents") or [[]])[0]

    assert len(docs) > 0
    assert "assistente local" in docs[0].lower()


def test_index_message_incremental_ignora_role_invalido(
    chroma_in_memory_collection,
    fake_embedder,
):
    cache = {}
    merlin_cli.index_message_incremental(cache, role="system", text="não indexar", ts="2026-01-01T00:00:00")
    merlin_cli.index_message_incremental(cache, role="user", text="   ", ts="2026-01-01T00:00:01")
    assert chroma_in_memory_collection.count() == 0


def test_build_rag_block_formata_fontes():
    result = {
        "documents": [["Texto do histórico", "Texto do pergaminho"]],
        "metadatas": [
            [
                {"source": "history", "role": "user", "ts": "2026-01-01T10:00:00"},
                {"source": "scroll", "path": "scrolls/sample.md"},
            ]
        ],
    }

    block = merlin_cli.build_rag_block(result)

    assert "MEMÓRIA_RECUPERADA" in block
    assert "histórico (user, 2026-01-01T10:00:00)" in block
    assert "pergaminho (scrolls/sample.md)" in block
