#!/bin/bash
# Executado após instalação do .deb

set -e

echo "🧙 Configurando Merlin IA..."

APP_ROOT="/opt/Merlin IA"
RESOURCE_ROOT="$APP_ROOT/resources"

if [ ! -d "$RESOURCE_ROOT" ]; then
    APP_ROOT="/opt/merlin-ia"
    RESOURCE_ROOT="$APP_ROOT"
fi

if [ ! -d "$RESOURCE_ROOT/.venv" ]; then
    python3 -m venv "$RESOURCE_ROOT/.venv"
fi

"$RESOURCE_ROOT/.venv/bin/pip" install -r "$RESOURCE_ROOT/requirements.txt"
if [ -f "$RESOURCE_ROOT/requirements-api.txt" ]; then
    "$RESOURCE_ROOT/.venv/bin/pip" install -r "$RESOURCE_ROOT/requirements-api.txt"
else
    "$RESOURCE_ROOT/.venv/bin/pip" install flask flask-cors
fi

mkdir -p /var/log/merlin
chmod 755 /var/log/merlin

if [ -f "$RESOURCE_ROOT/scripts/merlin-wrapper.sh" ]; then
    install -m 755 "$RESOURCE_ROOT/scripts/merlin-wrapper.sh" /usr/bin/merlin-ia-wrapper
fi

echo "✅ Merlin IA instalado!"
echo "🚀 Execute com: merlin-ia"
