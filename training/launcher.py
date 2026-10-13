"""Read-only plan and offline CPU smoke; paid execution is locked."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from training.config import TrainingConfig, verify_runtime


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--cpu-smoke", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    config = TrainingConfig.model_validate_json(args.config.read_text())
    verify_runtime(config, args.runtime_root)
    if args.execute:
        raise SystemExit(
            "Paid execution is locked: no approved GPU quote/budget or target hardware smoke."
        )
    if args.plan:
        print(json.dumps({
            "mode": "preparation", "blockers": config.blockers(),
            "task_ids": config.task_ids,
            "train_cases": len(config.task_ids) * config.train_seeds.count,
            "validation_cases": len(config.task_ids) * config.validation_seeds.count,
            "test_cases": len(config.task_ids) * config.test_seeds.count,
            "num_generations": config.num_generations,
            "runtime_verified": True,
            "paid_execution_enabled": False,
        }, indent=2))
        return 0
    if args.output is None:
        parser.error("--cpu-smoke requires --output (a new directory)")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["WANDB_DISABLED"] = "true"
    from training.cpu_smoke import run_cpu_smoke
    print(json.dumps(run_cpu_smoke(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
