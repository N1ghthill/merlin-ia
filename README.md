# Merlin IA (MVP Local)

Assistente local-first com chat em terminal, memória persistente e RAG local.
Local-first assistant with terminal chat, persistent memory, and local RAG.

## Recursos | Features
- Chat em terminal com streaming via Ollama. / Terminal chat with streaming via Ollama.
- Memória persistente em JSONL e perfil canônico do usuário. / Persistent JSONL memory and canonical user profile.
- RAG local com ChromaDB + SentenceTransformers. / Local RAG with ChromaDB + SentenceTransformers.
- Indexação incremental do histórico e pergaminhos. / Incremental indexing for history and scrolls.

## Requisitos | Requirements
- Linux (testado no Debian). / Linux (tested on Debian).
- Python 3.11+.
- Ollama instalado e rodando. / Ollama installed and running.
- Modelo local (default: `qwen2.5:7b`). / Local model (default: `qwen2.5:7b`).

## Setup
```bash
python3 -m venv merlin-venv
source merlin-venv/bin/activate
pip install -r requirements.txt
```

## Uso | Usage
```bash
python merlin_cli.py
```

## Pergaminhos | Scrolls
- Adicione arquivos `.md`/`.txt` em `scrolls/`.
- Rode `python rag_indexer.py` para indexar o conteúdo.
- Evite subir dados pessoais no GitHub.

## Configuração rápida | Quick config
- Troque o modelo alterando `MODEL` em `merlin_cli.py`.
- Ajuste o embedding alterando `EMBED_MODEL_NAME` em `merlin_cli.py`.
