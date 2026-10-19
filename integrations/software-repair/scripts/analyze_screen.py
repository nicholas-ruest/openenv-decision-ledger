"""Read-only proxy signal gate. Failures never supply reward variance."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "integrations/software-repair"))
from repair_env.tasks import make_task, visible_files  # noqa: E402


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def classify(protocol, rows):
    planned = {tuple(group) for group in protocol["groups"]}
    count = protocol["samples_per_group"]
    if not planned or len(planned) != len(protocol["groups"]) or type(count) is not int or count < 2:
        raise ValueError("invalid predeclared groups")
    seen = set()
    groups = []
    for row in rows:
        key = (row["task_id"], row["seed"])
        sample = row.get("sample")
        identity = (*key, sample)
        if key not in planned or type(sample) is not int or not 0 <= sample < count or identity in seen:
            raise ValueError("duplicate or unplanned sample")
        seen.add(identity)
        reward = row["reward"]
        if type(reward) not in (int, float) or not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError("invalid reward")
        if not row.get("failure") and (row.get("hidden_execution_rejections") != 0 or
                type(row.get("hidden_wrong_answers")) is not int or row.get("solved") != (reward == 1)):
            raise ValueError("completed sample lacks consistent grader diagnostics")
    complete = len(rows) == len(planned) * count
    for task, seed in protocol["groups"]:
        sampled = [row for row in rows if (row["task_id"], row["seed"]) == (task, seed)]
        hashes = {row.get("prompt_sha256") for row in sampled}
        if len(hashes) > 1 or any(not isinstance(h, str) or len(h) != 64 for h in hashes):
            raise ValueError("within-group prompt identity differs or is missing")
        valid = [row["reward"] for row in sampled if not row.get("failure")]
        full = sum(reward == 1 for reward in valid)
        groups.append({"task_id": task, "seed": seed, "samples": len(sampled), "valid": len(valid),
            "full": full, "partial": sum(0 < reward < 1 for reward in valid),
            "wrong": valid.count(0), "valid_rewards": valid,
            "valid_reward_std": statistics.pstdev(valid) if valid else None,
            "failures": dict(Counter(row["failure"] for row in sampled if row.get("failure"))),
            "prompt_sha256": next(iter(hashes)) if hashes else None,
            "productive": len(valid) >= 3 and full > 0 and full < len(valid)})
    calls = [call for row in rows for call in row.get("calls", [])]
    labels = [call["client_call_label"] for call in calls if call.get("client_call_label")]
    response_ids = [call["provider_response_id_sha256"] for call in calls
                    if call.get("provider_response_id_sha256")]
    duplicate_labels = len(labels) != len(set(labels))
    duplicate_ids = len(response_ids) != len(set(response_ids))
    provenance = {"recorded_calls": len(calls), "all_client_labels_available": bool(calls) and len(labels) == len(calls),
        "all_response_ids_available": bool(calls) and len(response_ids) == len(calls),
        "duplicate_client_labels": duplicate_labels, "duplicate_provider_response_ids": duplicate_ids}
    return {"stage": protocol.get("stage"), "complete": complete, "groups": groups,
        "unique_prompts": len(planned), "rollouts": len(rows),
        "sampling_provenance": provenance,
        "genuine_signal_screened": complete and not duplicate_labels and not duplicate_ids
            and any(group["productive"] for group in groups),
        "is_training": False, "private_arena_improvement": None}


def load_verified(directory):
    directory = Path(directory)
    if not (directory / "complete.json").exists():
        raise ValueError("screen has not completed")
    protocol = json.loads((directory / "protocol.json").read_text())
    for name, expected in protocol["source_files_sha256"].items():
        source = (REPO / name).resolve()
        if not source.is_relative_to(REPO) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError("frozen source differs; analyze with the original checkout")
    rows = [json.loads(line) for line in (directory / "episodes.jsonl").read_text().splitlines()]
    for row in rows:
        task = make_task(row["task_id"], row["seed"])
        reset = json.loads(row["messages"][1]["content"])
        if digest({"reset": reset, "files": visible_files(task)}) != row["prompt_sha256"]:
            raise ValueError("saved reset/workspace identity mismatch")
    return protocol, classify(protocol, rows)


def confirmation(screen_protocol, screen, confirm_protocol, confirmed):
    for key in ("provider", "source_files_sha256", "tokenizer_sha256", "samples_per_group"):
        if screen_protocol[key] != confirm_protocol[key]:
            raise ValueError("unmatched confirmation settings")
    if screen_protocol.get("stage") != "screen" or confirm_protocol.get("stage") != "confirm":
        raise ValueError("confirmation stages differ")
    if set(map(tuple, screen_protocol["groups"])) & set(map(tuple, confirm_protocol["groups"])):
        raise ValueError("confirmation prompts overlap")
    if confirm_protocol["groups"] != screen_protocol.get("planned_confirmation_groups"):
        raise ValueError("confirmation differs from predeclared prompts")
    return {"provisional_single_family_signal_confirmed": screen["genuine_signal_screened"] and
            confirmed["genuine_signal_screened"], "is_model_improvement": False,
            "darwin_promotion": False, "arena_submission_authorized": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--confirm", type=Path)
    args = parser.parse_args()
    protocol, result = load_verified(args.directory)
    if args.confirm:
        next_protocol, next_result = load_verified(args.confirm)
        result = {"screen": result, "confirmation": next_result,
                  "decision": confirmation(protocol, result, next_protocol, next_result)}
    print(json.dumps(result, indent=2))
