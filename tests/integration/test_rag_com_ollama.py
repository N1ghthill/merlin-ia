"""Testes de integração leve do fluxo RAG com Ollama mockado."""

from __future__ import annotations

import merlin_cli


def test_stream_chat_usa_ollama_mockado(mock_ollama, capsys):
    messages = [
        {"role": "system", "content": "Sistema"},
        {"role": "user", "content": "Fale algo"},
    ]

    answer = merlin_cli.stream_chat(messages)
    out = capsys.readouterr().out

    assert answer == "Resposta mockada"
    assert "Resposta mockada" in out
    assert len(mock_ollama) == 1
    assert mock_ollama[0]["kwargs"]["stream"] is True


def test_fluxo_recuperacao_e_montagem_rag_block(
    chroma_in_memory_collection,
    fake_embedder,
):
    cache = {}
    merlin_cli.index_message_incremental(
        cache,
        role="assistant",
        text="Merlin IA mantém memória semântica local para respostas melhores.",
        ts="2026-01-03T11:30:00",
    )

    result = merlin_cli.retrieve_context("memória semântica", cache, top_k=1)
    rag_block = merlin_cli.build_rag_block(result)

    assert (result.get("documents") or [[]])[0]
    assert "MEMÓRIA_RECUPERADA" in rag_block
    assert "histórico (assistant, 2026-01-03T11:30:00)" in rag_block
