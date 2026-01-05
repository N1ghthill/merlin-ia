# Merlin IA (MVP Local)

Assistente local-first (CPU) com:
- Chat em terminal
- Memória persistente (JSONL)
- Perfil canônico do usuário (determinístico)
- RAG local (ChromaDB + SentenceTransformers)
- Indexação incremental do histórico e pergaminhos

## Requisitos
- Linux (testado em Debian)
- Python 3.11+ (ideal 3.13)
- Ollama instalado e rodando
- Modelo baixado (ex: qwen2.5:7b)

## Setup
```bash
python3 -m venv merlin-venv
source merlin-venv/bin/activate
pip install -r requirements.txt
