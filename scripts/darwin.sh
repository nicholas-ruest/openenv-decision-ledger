#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${ARENA_MODEL_BASE_URL:?Set an existing target-model endpoint}"
: "${ARENA_MODEL_ID:?Set the model advertised by /v1/models}"
: "${ARENA_MODEL_REVISION:?Pin the served model revision}"
: "${ARENA_TOKENIZER_JSON:?Set the pinned tokenizer JSON path}"
: "${ARENA_MODEL_API_KEY:?Keep the model credential in the environment}"
: "${DARWIN_GATE_KEY_DIR:?Set a signing-key directory outside the repository}"
PYTHON_BIN="${ARENA_PYTHON:-$REPO_ROOT/.venv/bin/python}"
RUN_ROOT="${ARENA_RUN_ROOT:-$REPO_ROOT/runs/manual}"
cd "$REPO_ROOT/vendor/metaharness/integrations/openenv-arena-darwin"
node --experimental-strip-types run-darwin.mjs --work-root "$RUN_ROOT"   --generations 2 --children 3 --concurrency 1 --seed-base 700000   --attempts 8 --confirm-attempts 32 --max-total-new-cells 120 --   --env-dir "$REPO_ROOT/integrations/openenv-arena" --python "$PYTHON_BIN"   --tokenizer-json "$ARENA_TOKENIZER_JSON" --base-url "$ARENA_MODEL_BASE_URL"   --model "$ARENA_MODEL_ID" --model-revision "$ARENA_MODEL_REVISION"   --cache-dir "$RUN_ROOT/cache" --concurrency 2
# Use the upstream signed Flywheel gate on confirmation reports before promotion.
# This script never submits, posts, rents a GPU or schedules future work.

"$PYTHON_BIN" -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r.get("evidence")=="evaluator_scorecards" and r.get("confirmation",{}).get("status")=="measured", "Real target-model confirmation is required"' "$RUN_ROOT/reports/darwin-run.json"
node --experimental-strip-types gate.mjs --run "$RUN_ROOT/reports/darwin-run.json" --out "$RUN_ROOT/promotion-receipt.json"
node --experimental-strip-types gate.mjs --verify "$RUN_ROOT/promotion-receipt.json" --key-dir "$DARWIN_GATE_KEY_DIR"
