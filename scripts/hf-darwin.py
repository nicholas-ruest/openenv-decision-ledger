#!/usr/bin/env python3
"""Run the explicit calibration loop using an environment-only HF credential."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
token = os.environ.get("HF_TOKEN")
if not token:
    raise SystemExit("HF_TOKEN is unavailable. Configure it privately in ruOS secrets.")
env = os.environ.copy()
env["ARENA_MODEL_API_KEY"] = token
env.setdefault("ARENA_MODEL_BASE_URL", "https://router.huggingface.co/v1")
env.setdefault("ARENA_MODEL_ID", "Qwen/Qwen3.8-27B")
# This pins tokenizer/source accounting; a hosted provider does not attest checkpoint identity.
env.setdefault("ARENA_MODEL_REVISION", "hf-router-qwen3.8-27b-provider-revision-unverified")
env.setdefault("ARENA_TOKENIZER_JSON", "/home/ruv/arena-tokenizer.json")
env.setdefault("ARENA_PYTHON", "/home/ruv/arena-venv/bin/python")
env.setdefault("DARWIN_GATE_KEY_DIR", str(root.parent / "arena-promotion-keys"))
node_bin = Path("/home/ruv/arena-node-tools/node_modules/node/bin")
if node_bin.is_dir():
    env["PATH"] = str(node_bin) + os.pathsep + env.get("PATH", "")
key_dir = Path(env["DARWIN_GATE_KEY_DIR"]).resolve()
if key_dir == root or root in key_dir.parents:
    raise SystemExit("Signing keys must remain outside the repository.")
# No token is included in argv, output, a file, or a public artifact.
result = subprocess.run(["bash", str(root / "scripts/darwin.sh")], env=env)
sys.exit(result.returncode)
