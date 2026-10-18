"""Offline single-category cohort checks; never calls a model or starts training."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from training.config import TrainingConfig, verify_runtime


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def inspect(config, runtime):
    verify_runtime(config, runtime)
    if config.task_ids != ["software_change-d2"]:
        raise ValueError("This focused pilot accepts software_change-d2 only")
    spec = importlib.util.spec_from_file_location("focus_tasks", runtime / "arena_env/tasks.py")
    tasks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tasks)
    splits = {}
    seen = set()
    for name, interval in [("train", config.train_seeds), ("validation", config.validation_seeds), ("test", config.test_seeds)]:
        hashes = []
        for seed in interval.seeds():
            task = tasks.make_task("software_change", seed, 2)
            # Hash public task inputs only. Never export expected answers or rubrics.
            public = {"prompt": task["prompt"], "files": task["files"]}
            identity = digest(public)
            if identity in seen:
                raise ValueError("Repeated public instance within or across splits")
            seen.add(identity)
            if tasks.grade(task, tasks.oracle_answer(task)) != 1 or tasks.grade(task, {}) != 0:
                raise ValueError("Native positive/empty controls failed")
            if digest(public) != digest({"prompt": tasks.make_task("software_change", seed, 2)["prompt"], "files": tasks.make_task("software_change", seed, 2)["files"]}):
                raise ValueError("Reset is nondeterministic")
            hashes.append(identity)
        splits[name] = {"cases": len(hashes), "public_instance_digests": hashes}
    return {"kind": "single_category_offline_preflight", "task_ids": config.task_ids,
            "splits": splits, "unique_instances": len(seen), "native_controls_passed": True,
            "model_calls": 0, "training_started": False, "model_improvement": None,
            "training_ready": False, "remaining_blockers": config.blockers(),
            "limitation": "Oracle controls and deterministic inputs do not establish model learning or ranking."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()
    config = TrainingConfig.model_validate_json(args.config.read_text())
    print(json.dumps(inspect(config, args.runtime_root), indent=2))


if __name__ == "__main__":
    main()
