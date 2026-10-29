#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/integrations/openenv-arena"
python -m pytest -q tests
openenv validate --url "${ARENA_ENV_URL:-http://127.0.0.1:8000}"
python -m scripts.replay_native --url "${ARENA_ENV_URL:-http://127.0.0.1:8000}" --output evidence/native-replay.json
