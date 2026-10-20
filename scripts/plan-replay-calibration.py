"""Offline review packet only: no provider, credential or execution capability."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/software-repair"))
from repair_env.tasks import make_task, task_fingerprint, visible_files

TASKS = ("software_repair-replay-d2", "software_repair-replay-d3")
SEEDS = {"screen": (1060000, 1060100), "confirm": (1061000, 1061100)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def build():
    stages = {}
    workspaces = set()
    for stage, seeds in SEEDS.items():
        groups = []
        for task_id in TASKS:
            for seed in seeds:
                task = make_task(task_id, seed)
                files = visible_files(task)
                workspace = digest(files)
                if workspace in workspaces:
                    raise ValueError("planned distinct prompts share a workspace")
                workspaces.add(workspace)
                groups.append({"task_id": task_id, "seed": seed,
                    "workspace_sha256": workspace, "task_fingerprint": task_fingerprint(task),
                    "workspace_utf8_bytes": sum(len(s.encode()) for s in files.values())})
        stages[stage] = {"groups": groups, "distinct_task_prompts": len(groups),
                         "samples_per_prompt": 4, "planned_rollouts": 4 * len(groups),
                         "max_calls": 12 * 4 * len(groups)}
    source = [Path(__file__), ROOT / "scripts/repair-signal-screen.py",
              ROOT / "integrations/software-repair/scripts/analyze_screen.py",
              ROOT / "integrations/openenv-arena/scripts/calibrate.py",
              *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py"))]
    return {"plan_version": 1, "executed": False, "paid_execution_allowed": False,
        "source_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
                                     .decode().strip(),
        "source_files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in source},
        "stages": stages, "confirmation_conditional_on_replay_d3_signal": True,
        "intended_settings": {"model": "Qwen/Qwen3.8-27B", "provider": "deepinfra",
            "tokenizer_sha256": "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3",
            "temperature": 0.7, "thinking_requested": True, "response_format": "json_object",
            "max_actions": 12, "episode_generation_observation_units": 8192,
            "context_units": 16384, "stage_wall_seconds": 1200, "retries": 0},
        "unverified": ["Provider selected metadata and price quote must be frozen at admission.",
            "Private billing reconciliation and shared reservation admission are not performed.",
            "The existing runner still has fixed release-task groups; it must be configured and tested first.",
            "Workspace hashes are not native reset observation hashes; those must match within live groups.",
            "Source revision records the parent checkout; source hashes include local plan content.",
            "Arena checkpoint, thinking and chat wrapper equivalence is unattested."],
        "new_model_calls": 0, "is_training": False, "mix_adoption": False,
        "arena_submission_authorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    content = json.dumps(build(), indent=2) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(content)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
