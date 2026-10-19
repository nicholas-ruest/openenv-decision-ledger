"""Export visible task workspaces and an exact image-bound request draft; never POST."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repair_env.environment import RepairAction, RepairObservation  # noqa: E402
from repair_env.tasks import TRAINING_TASK_IDS, make_task, visible_files  # noqa: E402


def request(image):
    if not re.fullmatch(r"ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:[0-9a-f]{64}", image):
        raise ValueError("Exact published environment image required")
    tasks = [{"task_id": task_id, "split": "train", "reset_wall_s": 120,
        "rollout_wall_s": 600, "verifier_wall_s": 30, "tool_wall_s": 20,
        "tool_calls_total": 12, "tool_calls_per_minute": 60,
        "completion_tokens": 8192, "context_tokens": 16384,
        "cpu_floor_vcpus": 1, "memory_gib": 2, "workspace_gib": 2} for task_id in TRAINING_TASK_IDS]
    return {"submission_id": "decision-ledger-software-repair-v3-20261019",
        "name": "Decision Ledger: software repair workflow candidate",
        "image": image, "source": "https://github.com/nicholas-ruest/openenv-decision-ledger",
        "dataset": "GlobalBusinessAdvisors/openenv-decision-ledger",
        "schema": {"action": RepairAction.model_json_schema(), "observation": RepairObservation.model_json_schema()},
        "tasks": tasks, "example_actions": [{"op": "read", "path": "*"}, {"op": "submit"}],
        "finish_action": {"op": "submit"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "tasks.jsonl").open("w") as stream:
        for task_id in TRAINING_TASK_IDS:
            for seed in range(984000, 984016):
                task = make_task(task_id, seed)
                stream.write(json.dumps({"task_id": task_id, "seed": seed,
                    "files": visible_files(task), "prompt": task.instructions}) + "\n")
    (args.output / "submission-candidate.json").write_text(json.dumps(request(args.image), indent=2))
    (args.output / "REVIEW.json").write_text(json.dumps({"submitted": False,
        "approval_required": True, "target_model_calibrated": False,
        "dataset_update_required_before_submission": True,
        "hypothesis": "edit/test/retest workflows may transfer better than graph-answer JSON",
        "private_arena_score": None}, indent=2))
    (args.output / "README.md").write_text("---\nlicense: mit\ntask_categories:\n- text-generation\n---\n\n"
        "# Decision Ledger software repair candidate\n\n8 provisional tasks across four harder Python repair families and two difficulty levels. "
        "Actions: list/read/write/test/submit. Candidate Python is interpreted by a documented bounded subset; "
        "no host Python, shell, imports or network. Visible tests give feedback; hidden inputs are independently "
        "generated, disjoint from visible inputs. Reward requires improving hidden results over the broken module; "
        "full reward requires every hidden case. No rewards for formatting or unchanged code.\n\n"
        "This export is a candidate, not a submitted or trained model. Target-model signal and transfer remain unverified. "
        "No private Arena evaluation data is included. Existing graph tasks/source remain a separate baseline.\n")
