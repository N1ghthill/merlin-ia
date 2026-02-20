# Build do Zero

Este guia cobre o fluxo completo para preparar o ambiente de desenvolvimento e gerar pacotes do Merlin IA para distribuição.

## O que este guia cobre

- Preparação do ambiente Python.
- Dependências do frontend Electron.
- Geração de artefatos para Linux, Windows e macOS.

## Passo a passo

1. Clone o projeto e configure o ambiente Python:

```bash
git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

2. Instale dependências do Electron:

```bash
cd electron
npm install
```

3. Gere os pacotes desejados:

```bash
# Linux (.deb)
npm run dist:deb

# Linux (.rpm)
npm run dist:rpm

# Windows (.exe)
npm run dist:win

# macOS (.dmg)
npm run dist:mac
```

## Dicas

- Execute `pytest tests/ -v` antes de empacotar.
- Publique os artefatos na página de Releases para facilitar instalação.
