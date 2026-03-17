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

export MERLIN_STORAGE_MODE="${MERLIN_STORAGE_MODE:-project}"

exec python -m merlin_cli
