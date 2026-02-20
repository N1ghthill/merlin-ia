#!/bin/bash
# Wrapper para executar o Merlin IA

set -e

APP_ROOT="/opt/Merlin IA"
RESOURCE_ROOT="$APP_ROOT/resources"

if [ ! -d "$RESOURCE_ROOT" ]; then
    APP_ROOT="/opt/merlin-ia"
    RESOURCE_ROOT="$APP_ROOT"
fi

cd "$RESOURCE_ROOT"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

python3 merlin_api.py --port 3030 &
API_PID=$!

sleep 2

if [ -x "$APP_ROOT/merlin-ia" ]; then
    "$APP_ROOT/merlin-ia"
elif [ -x "$RESOURCE_ROOT/electron/node_modules/.bin/electron" ]; then
    cd electron
    npm start
else
    echo "❌ Executável do Merlin IA não encontrado."
fi

kill "$API_PID" 2>/dev/null || true
