# 📦 Instalação do Merlin IA

Este guia cobre a instalação do Merlin IA em Linux e também o caminho de build para Windows e macOS.

## Linux (Ubuntu/Debian)

### Via `.deb` (recomendado)

1. Baixe o `.deb` da [página de releases](https://github.com/N1ghthill/merlin-ia/releases)
2. Instale: `sudo dpkg -i merlin-ia*.deb`
3. Execute: `merlin-ia`

### Via código-fonte (para desenvolvimento)

```bash
git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# CLI mode
python merlin_cli.py

# UI mode (Electron)
cd electron
npm install
npm start
```

## Windows

```bash
# Build do .exe
cd electron
npm run dist:win
# O instalador estará em electron/dist/
```

## macOS

```bash
# Build do .dmg
cd electron
npm run dist:mac
```
