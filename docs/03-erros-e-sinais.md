# Erros e Sinais

Este guia resume falhas comuns e um fluxo curto de diagnóstico.

## Sinais comuns

- Ollama não responde.
- Dependência Python ausente.
- RAG não encontra documentos esperados.
- Comandos `/linux-*` não executam por falta de executor/socket.

## Diagnóstico rápido

1. Ative o ambiente e garanta dependências:

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

2. Verifique o Ollama:

```bash
ollama --version
ollama list
```

3. Abra o CLI e consulte os caminhos:

```bash
merlin-ia
```

```text
/paths
```

4. Reindexe os dados locais se necessário:

```text
/index_scrolls
/reindex
```

5. Para problemas no Linux Agent:

```bash
ls -l /run/linux-agent/agent.sock
systemctl status linux-agent.socket
```

## Quando abrir issue

Inclua:

- comando executado
- mensagem de erro
- saída de `/paths`
- versão do Python e do Ollama
