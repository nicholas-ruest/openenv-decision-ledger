#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
: "${TRAINING_PYTHON:?Set TRAINING_PYTHON to the isolated training interpreter}"
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/integrations/openenv-arena${PYTHONPATH:+:$PYTHONPATH}"
export HF_HUB_OFFLINE=1
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export CUDA_VISIBLE_DEVICES=""
cd "$REPO_ROOT"
"$TRAINING_PYTHON" -m pytest -q tests/training
"$TRAINING_PYTHON" -m training.launcher --plan \
  --config config/private-training-preparation.json \
  --runtime-root integrations/openenv-arena
"$TRAINING_PYTHON" -m training.launcher --cpu-smoke \
  --config config/private-training-preparation.json \
  --runtime-root integrations/openenv-arena \
  --output "${TRAINING_SMOKE_OUTPUT:?Set a new output directory}"
"$TRAINING_PYTHON" -m training.launcher --cpu-smoke --architecture qwen3_5 \
  --config config/private-training-preparation.json \
  --runtime-root integrations/openenv-arena \
  --output "${TRAINING_SMOKE_OUTPUT}-qwen"
