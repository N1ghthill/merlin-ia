#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate

# CPU tuning (ajuste se quiser)
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=14
export MKL_NUM_THREADS=14
export NUMEXPR_NUM_THREADS=14

# Memória semântica: atualizar rápido (versão final de hoje)
export MERLIN_PROFILE_UPDATE_EVERY=2

exec python merlin.py

