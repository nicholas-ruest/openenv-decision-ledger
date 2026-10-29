#!/usr/bin/env python3
"""Bounded same-prompt proxy screen; never trains or submits."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path("/home/ruv/openenv-decision-ledger")
RUNNER = ROOT / "integrations/openenv-arena/scripts/calibrate.py"
EXPECTED = "62788e67aa07f5f235c68f654cda84e9130147eb13fa9b9ef1f44a31a8a16420"
if hashlib.sha256(RUNNER.read_bytes()).hexdigest() != EXPECTED:
    raise SystemExit("Runner revision changed; refusing.")
spec = importlib.util.spec_from_file_location("calibration", RUNNER)
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)
original = calibration.run_episode


def fixed_prompt(args, family, attempt, *positional, **kwargs):
    """Keep reset seed fixed; provider sampling remains independent."""
    seed = args.seed
    try:
        args.seed = seed - attempt
        row = original(args, family, attempt, *positional, **kwargs)
    finally:
        args.seed = seed
    if row["seed"] != seed:
        raise RuntimeError("Same-prompt seed invariant failed.")
    row["group_kind"] = "same_prompt_independent_provider_samples"
    row["screen_wrapper_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return row


calibration.run_episode = fixed_prompt
output = ROOT / "runs/same-prompt-screen-20261012"
output.mkdir(exist_ok=False)
for seed in (860000, 860100):
    argv = [
        "--base-url", "https://router.huggingface.co/v1",
        "--model", "Qwen/Qwen3.8-27B",
        "--model-revision", "deepinfra-checkpoint-unverified",
        "--api-key-env", "HF_TOKEN",
        "--task-id", "software_change-d2",
        "--task-id", "finance_ledger-d3",
        "--seed", str(seed), "--max-steps", "4",
        "--max-tokens", "8192", "--max-total-tokens", "250000",
        "--accounting", "arena", "--episode-completion-tokens", "8192",
        "--episode-context-tokens", "16384",
        "--tokenizer-json", "/home/ruv/arena-tokenizer.json",
        "--tokenizer-sha256", "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3",
        "--thinking", "on", "--request-timeout", "180",
        "--output", str(output / f"group-{seed}.jsonl"), "--execute",
    ]
    result = calibration.main(argv)
    if result:
        raise SystemExit(result)
(output / "complete.json").write_text(
    json.dumps({"status": "completed", "groups": 4, "rollouts_per_group": 4,
                "maximum_total_reservation_units": 500000,
                "training": False, "official_evaluation": False}) + "\n"
)
