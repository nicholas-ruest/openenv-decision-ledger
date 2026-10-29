"""Read-only finish-action diagnostics; never convert failed rollouts into solves."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def replay_episode(row):
    from repair_env.environment import RepairAction, RepairEnvironment, check
    from repair_env.runner import Program, Rejected
    from repair_env.tasks import SOURCE_PATH, visible_files

    env = RepairEnvironment()
    env.reset(task_id=row["task_id"], seed=row["seed"])
    messages = row["messages"]
    reset = json.loads(messages[1]["content"])
    if digest({"reset": reset, "files": visible_files(env._task)}) != row["prompt_sha256"]:
        raise ValueError("saved reset/workspace identity mismatch")
    actions = []
    # Only an assistant action followed by its saved user observation was executed.
    # A truncated or invalid final reply without an observation is never applied.
    for index in range(2, len(messages) - 1):
        message, following = messages[index:index + 2]
        if message["role"] != "assistant" or following["role"] != "user":
            continue
        value = json.loads(message["content"])
        if value == {"finish": True}:
            value = {"op": "submit"}
        elif type(value) is dict and set(value) == {"action"}:
            value = value["action"]
        action = RepairAction.model_validate(value)
        observation = env.step(action)
        if observation.model_dump() != json.loads(following["content"]):
            raise ValueError("replayed observation differs from saved execution")
        actions.append(action.op)
    source_changed = env._files[SOURCE_PATH] != env._task.initial_source
    try:
        passed, outcomes = check(Program(env._files[SOURCE_PATH]), env._task,
                                 env._task.hidden, details=True)
        errors = Counter(item["error"] for item in outcomes if item["error"])
    except Rejected as exc:
        passed, errors = 0, Counter({"rejected: " + str(exc): len(env._task.hidden)})
    final = env._observe() if env._done else env.step(RepairAction(op="submit"))
    category = ("execution_failure" if errors else "unchanged" if not source_changed else
                "valid_full" if final.reward == 1 else
                "valid_partial" if final.reward > 0 else "valid_wrong")
    return {"task_id": row["task_id"], "seed": row["seed"], "sample": row["sample"],
            "original_failure": row.get("failure"), "original_reward": row["reward"],
            "replayed_actions": actions, "source_changed": source_changed,
            "offline_finish_reward": final.reward, "hidden_passed": passed,
            "execution_errors": dict(errors), "diagnostic_category": category,
            "counts_as_new_live_solve": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.source_root.resolve()
    protocol = json.loads((args.directory / "protocol.json").read_text())
    for name, expected in protocol["source_files_sha256"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("frozen source differs")
    sys.path.insert(0, str(root / "integrations/software-repair"))
    raw = (args.directory / "episodes.jsonl").read_bytes()
    rows = [replay_episode(json.loads(line)) for line in raw.splitlines() if line.strip()]
    print(json.dumps({"raw_sha256": hashlib.sha256(raw).hexdigest(),
        "rows": rows, "diagnostic_counts": dict(Counter(row["diagnostic_category"] for row in rows)),
        "original_failure_labels_preserved": True, "new_model_calls": 0,
        "is_training": False, "live_solve_count_changed": False,
        "arena_wrapper_equivalence_attested": False}, indent=2))


if __name__ == "__main__":
    main()
