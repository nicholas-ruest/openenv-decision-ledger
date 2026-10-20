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
sys.path.insert(0, str(ROOT / "integrations/software-repair/scripts"))
from screen_profiles import get_profile, sampling_settings, REPLAY_TASKS, REPLAY_SEEDS

TASKS, SEEDS = REPLAY_TASKS, REPLAY_SEEDS


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def build(profile_name="replay_compare"):
    if profile_name not in ("replay_compare", "merge_compare"):
        raise ValueError("offline comparison profile required")
    stages = {}
    workspaces = set()
    for stage in ("screen", "confirm"):
        profile = get_profile(profile_name, stage)
        groups = []
        for task_id, seed in profile["groups"]:
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
                         "samples_per_prompt": profile["samples_per_group"],
                         "planned_rollouts": profile["samples_per_group"] * len(groups),
                         "max_calls": profile["max_calls"]}
    source = [Path(__file__), ROOT / "scripts/repair-signal-screen.py",
              ROOT / "integrations/software-repair/scripts/analyze_screen.py",
              ROOT / "integrations/software-repair/scripts/screen_profiles.py",
              ROOT / "integrations/software-repair/scripts/screen_deadline.py",
              ROOT / "integrations/openenv-arena/scripts/calibrate.py",
              *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py"))]
    return {"plan_version": 2, "profile": profile_name,
        "signal_task_ids": get_profile(profile_name, "screen")["signal_task_ids"],
        "executed": False, "paid_execution_allowed": False,
        "source_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
                                     .decode().strip(),
        "source_files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in source},
        "stages": stages, "confirmation_conditional_on_candidate_signal": True,
        **({"confirmation_conditional_on_replay_d3_signal": True} if profile_name == "replay_compare" else {}),
        "intended_settings": sampling_settings(),
        "unverified": ["Provider selected metadata and price quote must be frozen at admission.",
            "Private billing reconciliation and shared reservation admission are not performed.",
            "The runner shares this comparison profile but paid execution is unconditionally disabled.",
            "Local worker supervision does not attest remote request cancellation or billing stop.",
            "Workspace hashes are not native reset observation hashes; those must match within live groups.",
            "Source revision records the parent checkout; source hashes include local plan content.",
            "Arena checkpoint, thinking and chat wrapper equivalence is unattested."],
        "new_model_calls": 0, "is_training": False, "mix_adoption": False,
        "arena_submission_authorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("replay_compare", "merge_compare"), default="replay_compare")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    content = json.dumps(build(args.profile), indent=2) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(content)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
