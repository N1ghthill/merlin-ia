# Bootstrap do Zero

Este guia cobre o bootstrap do Merlin IA a partir de uma máquina Linux limpa.

## Passo a passo

```bash
sudo apt install -y git python3 python3-pip python3-venv

git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

Instale ou valide o Ollama:

```bash
ollama --version
ollama pull qwen2.5:7b
```

## Validação mínima

```bash
make test
make compile
merlin-ia
```

Depois da primeira execução, rode `/paths` para confirmar quais diretórios o runtime selecionou.

## Armazenamento

- Em um clone Git gravável, o modo tende a ser `project`.
- Fora disso, o fallback é `user`, usando os diretórios XDG do usuário.

Para fixar o modo:

```bash
export MERLIN_STORAGE_MODE=project
export MERLIN_STORAGE_MODE=user
```
