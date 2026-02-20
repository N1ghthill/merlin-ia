#!/bin/bash
# Prepara ambiente para build do Electron

set -e

echo "🧙 Preparando build do Merlin IA..."

if [ ! -d "electron" ]; then
    echo "❌ Execute da raiz do projeto"
    exit 1
fi

cd electron/icons

if command -v convert >/dev/null 2>&1; then
    echo "🖼️ Gerando ícones..."

    convert merlin.png -define icon:auto-resize=256,128,64,48,32,16 merlin.ico

    if command -v iconutil >/dev/null 2>&1; then
        mkdir -p merlin.iconset
        for size in 16 32 64 128 256 512; do
            convert merlin.png -resize ${size}x${size} merlin.iconset/icon_${size}x${size}.png
        done
        iconutil -c icns merlin.iconset -o merlin.icns
        rm -rf merlin.iconset
    else
        echo "⚠️ iconutil não encontrado. Pulando geração de .icns."
    fi
else
    echo "⚠️ ImageMagick não encontrado. Pulando geração de ícones."
fi

cd ../..

if [ ! -d ".venv" ]; then
    echo "🐍 Criando ambiente virtual..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
if [ -f requirements-api.txt ]; then
    pip install -r requirements-api.txt
else
    pip install flask flask-cors
fi

echo "✅ Pronto para build!"
