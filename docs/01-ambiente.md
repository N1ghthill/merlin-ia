# Ambiente de Referência

Este documento registra um perfil simples de ambiente para validar o Merlin IA sem depender de componentes extras fora do stack Python e do Ollama.

## Base recomendada

- Linux
- Python `3.10+`
- `python3-pip`
- `python3-venv`
- Ollama disponível no host

## Checklist rápido

1. Verifique o Python:

```bash
python3 --version
```

2. Verifique o Ollama:

```bash
ollama --version
```

3. Ative o ambiente e rode a suíte:

```bash
source .venv/bin/activate
pytest tests/ -q
```

4. Valide a compilação dos módulos:

```bash
python3 -m compileall merlin_cli.py merlin_api.py rag_indexer.py executor merlin
```
