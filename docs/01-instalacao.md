# Instalação do Merlin IA

Este guia cobre a instalação do Merlin IA a partir do código-fonte em Linux.

## Pré-requisitos

```bash
sudo apt install -y python3 python3-pip python3-venv
```

Ollama também precisa estar disponível no host:

```bash
ollama --version
ollama pull qwen2.5:7b
```

## Instalação

```bash
git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

## Verificação Rápida

```bash
source .venv/bin/activate
merlin-ia
merlin-api --port 3030
merlin-index
```

## Armazenamento

- Em um clone Git gravável, o Merlin tende a usar `MERLIN_STORAGE_MODE=project`, com dados em `./data` e documentos em `./scrolls`.
- Fora desse cenário, usa `MERLIN_STORAGE_MODE=user`, com paths XDG em `~/.local/share/merlin-ia` e `~/.local/state/merlin-ia`.

Para fixar o modo manualmente:

```bash
export MERLIN_STORAGE_MODE=project
export MERLIN_STORAGE_MODE=user
```

Também é possível sobrescrever paths específicos com `MERLIN_SCROLLS_DIR`, `MERLIN_HISTORY_PATH`, `MERLIN_CHROMA_DIR` e variáveis correlatas.
