#!/usr/bin/env python3
"""Finite, explicitly authorized difficulty/thinking comparison; never submits."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path("/home/ruv/openenv-decision-ledger")
out = root / "runs/learning-matrix-20261012"
out.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env["PYTHONPATH"] = str(root / "integrations/openenv-arena")
runner = root / "integrations/openenv-arena/scripts/calibrate.py"
for thinking in ("on", "off"):
    target = out / f"d1-thinking-{thinking}.jsonl"
    prior = []
    for part in out.glob(f"d1-thinking-{thinking}*.jsonl"):
        prior.extend(json.loads(line) for line in part.read_text().splitlines())
    done = {}
    for row in prior:
        if row.get("type") == "episode":
            done.setdefault(row["family"], set()).add(row["seed"])
    families = ("software_change", "industrial_schedule", "science_calibration",
                "office_reconciliation", "finance_ledger", "math_route",
                "security_triage", "media_timeline")
    pending = [family for family in families if len(done.get(family, set())) < 4]
    if not pending:
        print(f"Already complete: thinking={thinking}", flush=True)
        continue
    if target.exists():
        target.rename(out / f"d1-thinking-{thinking}-interrupted.jsonl")
    cmd = [sys.executable, str(runner), "--base-url", "https://router.huggingface.co/v1",
           "--model", "Qwen/Qwen3.8-27B", "--model-revision", "deepinfra-checkpoint-unverified",
           "--api-key-env", "HF_TOKEN", "--difficulty", "1", "--seed", "830000",
           "--max-steps", "4", "--max-tokens", "8192", "--max-total-tokens", "500000",
           "--accounting", "arena", "--episode-completion-tokens", "8192",
           "--episode-context-tokens", "16384", "--tokenizer-json", "/home/ruv/arena-tokenizer.json",
           "--tokenizer-sha256", "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3",
           "--thinking", thinking, "--request-timeout", "120", "--output", str(target), "--execute"]
    for family in pending:
        cmd.extend(["--task-id", family])
    print(f"Starting d1 thinking={thinking}; pending={pending}.", flush=True)
    with (out / f"d1-thinking-{thinking}.log").open("w") as log:
        result = subprocess.run(cmd, cwd=root, env=env, stdout=log, stderr=log, timeout=5400)
    print(f"Finished thinking={thinking}, exit={result.returncode}", flush=True)
    if result.returncode:
        print("Stopping queue on failed/incomplete run.", flush=True)
        sys.exit(result.returncode)
reports = []
for thinking in ("on", "off"):
    episodes = {}
    for path in sorted(out.glob(f"d1-thinking-{thinking}*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("type") == "episode":
                episodes[(row["family"], row["seed"])] = row
    rows = list(episodes.values())
    reports.append({"thinking": thinking, "unique_episodes": len(rows),
                    "full_solves": sum(row["solved"] for row in rows),
                    "mean_reward": sum(row["reward"] for row in rows) / len(rows) if rows else None})
(out / "comparison.json").write_text(json.dumps(reports, indent=2) + "\n")
print(json.dumps(reports), flush=True)
