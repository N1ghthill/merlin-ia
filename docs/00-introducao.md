# Introdução ao Merlin IA

Merlin IA é um assistente local-first para Linux com foco em CLI, API local e automação controlada.

## O que o projeto faz

- Consulta documentos locais sem depender de nuvem.
- Mantém histórico e memória semântica no próprio host.
- Mantém um fluxo único para chat, RAG e Linux Agent.

## Começo Rápido

1. Prepare o ambiente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

2. Garanta o modelo local:

```bash
ollama pull qwen2.5:7b
```

3. Inicie o CLI:

```bash
merlin-ia
```

4. Consulte os caminhos ativos:

```text
/paths
```

5. Adicione arquivos `.md` e `.txt` ao diretório `scrolls_dir` e faça a primeira pergunta.

## Próximos Documentos

- [Instalação](./01-instalacao.md)
- [Como usar](./02-como-usar.md)
- [Arquitetura](./arquitetura.md)
- [API local](./api.md)
