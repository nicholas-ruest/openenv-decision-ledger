"""Read-only proxy signal gate. Failures never supply reward variance."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "integrations/software-repair"))
from repair_env.tasks import make_task, visible_files  # noqa: E402


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def sampling_provenance(rows):
    calls = [call for row in rows for call in row.get("calls", [])]
    labels = [call["client_call_label"] for call in calls
              if isinstance(call.get("client_call_label"), str) and call["client_call_label"].strip()]
    response_ids = [call["provider_response_id_sha256"] for call in calls
                    if isinstance(call.get("provider_response_id_sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", call["provider_response_id_sha256"])]
    return {"recorded_calls": len(calls), "all_client_labels_available": bool(calls) and len(labels) == len(calls),
        "all_response_ids_available": bool(calls) and len(response_ids) == len(calls),
        "duplicate_client_labels": len(labels) != len(set(labels)),
        "duplicate_provider_response_ids": len(response_ids) != len(set(response_ids)),
        "completed_rollouts_have_calls": all(row.get("calls") for row in rows if not row.get("failure")),
        "client_label_hashes": sorted(hashlib.sha256(label.encode()).hexdigest() for label in labels),
        "provider_response_id_hashes": sorted(response_ids)}


def identities_verified(provenance):
    return (provenance["all_client_labels_available"] and provenance["all_response_ids_available"]
            and provenance["completed_rollouts_have_calls"] and not provenance["duplicate_client_labels"]
            and not provenance["duplicate_provider_response_ids"])


def signal_tasks(protocol):
    planned = {task for task, _ in protocol["groups"]}
    targets = protocol.get("signal_task_ids")
    if targets is None:
        # A mixed legacy archive has no declared candidate arm. Keep descriptive
        # results, but never let an unrelated task supply its promotion signal.
        return sorted(planned) if len(planned) == 1 else []
    if (type(targets) is not list or not targets or any(type(t) is not str for t in targets)
            or len(set(targets)) != len(targets) or not set(targets) <= planned):
        raise ValueError("invalid declared signal tasks")
    return targets


def classify(protocol, rows):
    planned = {tuple(group) for group in protocol["groups"]}
    count = protocol["samples_per_group"]
    if not planned or len(planned) != len(protocol["groups"]) or type(count) is not int or count < 2:
        raise ValueError("invalid predeclared groups")
    targets = signal_tasks(protocol)
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
        wrong = row.get("hidden_wrong_answers")
        rejected = row.get("hidden_execution_rejections")
        if not row.get("failure") and (type(rejected) is not int or rejected != 0 or
                type(wrong) is not int or wrong < 0 or
                (reward == 1 and wrong != 0) or (reward < 1 and wrong == 0) or
                type(row.get("solved")) is not bool or row["solved"] != (reward == 1)):
            raise ValueError("completed sample lacks consistent grader diagnostics")
    complete = len(rows) == len(planned) * count
    for task, seed in protocol["groups"]:
        sampled = [row for row in rows if (row["task_id"], row["seed"]) == (task, seed)]
        hashes = {row.get("prompt_sha256") for row in sampled}
        if len(hashes) > 1 or any(not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes):
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
    observed_prompts = [g["prompt_sha256"] for g in groups if g["samples"]]
    if len(observed_prompts) != len(set(observed_prompts)):
        raise ValueError("distinct groups reuse a prompt identity")
    provenance = sampling_provenance(rows)
    tasks = {}
    for task_id in sorted({task for task, _ in planned}):
        selected = [row for row in rows if row["task_id"] == task_id]
        selected_groups = [group for group in groups if group["task_id"] == task_id]
        own_provenance = sampling_provenance(selected)
        # Missing calls in another arm remain that arm's failure. Reused call
        # identities anywhere in the comparison invalidate independence.
        own_identity = (identities_verified(own_provenance) and
                        not provenance["duplicate_client_labels"] and
                        not provenance["duplicate_provider_response_ids"])
        own_complete = len(selected) == len(selected_groups) * count
        tasks[task_id] = {"complete": own_complete,
            "productive_groups": sum(group["productive"] for group in selected_groups),
            "sampling_provenance": own_provenance, "sampling_identity_verified": own_identity,
            "genuine_signal_screened": own_complete and own_identity
                and any(group["productive"] for group in selected_groups)}
    return {"stage": protocol.get("stage"), "complete": complete, "groups": groups,
        "unique_prompts": len(planned), "rollouts": len(rows),
        "distinct_observed_prompts": len(observed_prompts),
        "signal_gate_version": 3, "sampling_provenance": provenance,
        "sampling_identity_verified": identities_verified(provenance),
        "signal_task_ids": targets, "tasks": tasks,
        "genuine_signal_screened": complete and bool(targets)
            and all(tasks[task]["genuine_signal_screened"] for task in targets),
        "is_training": False, "private_arena_improvement": None}


def verify_worker_receipt(directory, protocol):
    supervision = protocol.get("worker_supervision")
    if supervision is None:
        if "integrations/software-repair/scripts/screen_deadline.py" in protocol.get("source_files_sha256", {}):
            raise ValueError("supervised worker marker missing")
        return  # Historical archives retain their original unsupervised protocol.
    if type(supervision) is not dict or supervision.get("required") is not True:
        raise ValueError("invalid worker supervision protocol")
    limit = supervision.get("wall_seconds")
    if type(limit) not in (int, float) or not math.isfinite(limit) or not 0 < limit <= 1200:
        raise ValueError("invalid worker supervision bound")
    if "sampling_settings" in protocol and protocol["sampling_settings"].get("stage_wall_seconds") != limit:
        raise ValueError("worker bound differs from frozen settings")
    directory = Path(directory)
    receipt = directory.with_name(directory.name + ".worker.jsonl")
    if not receipt.is_file():
        raise ValueError("supervised worker receipt unavailable")
    events = [json.loads(line) for line in receipt.read_text().splitlines() if line.strip()]
    if len(events) != 3 or [e.get("event") for e in events] != ["starting", "started", "terminal"]:
        raise ValueError("supervised worker lifecycle incomplete")
    started, worker, terminal = events
    if (started.get("wall_seconds") != supervision.get("wall_seconds")
            or type(worker.get("pid")) is not int or worker["pid"] <= 0
            or terminal.get("pid") != worker["pid"] or terminal.get("status") != "completed"
            or terminal.get("shutdown_verified") is not True
            or terminal.get("finished_before_deadline") is not True
            or type(terminal.get("worker_exitcode")) is not int or terminal["worker_exitcode"] != 0):
        raise ValueError("supervised worker did not complete within deadline")


def load_verified(directory):
    directory = Path(directory)
    if not (directory / "complete.json").exists():
        raise ValueError("screen has not completed")
    protocol = json.loads((directory / "protocol.json").read_text())
    verify_worker_receipt(directory, protocol)
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
    for key in ("provider", "source_files_sha256", "tokenizer_sha256", "samples_per_group",
                "profile", "signal_task_ids", "sampling_settings"):
        if screen_protocol.get(key) != confirm_protocol.get(key):
            raise ValueError("unmatched confirmation settings")
    if screen_protocol.get("stage") != "screen" or confirm_protocol.get("stage") != "confirm":
        raise ValueError("confirmation stages differ")
    if set(map(tuple, screen_protocol["groups"])) & set(map(tuple, confirm_protocol["groups"])):
        raise ValueError("confirmation prompts overlap")
    if confirm_protocol["groups"] != screen_protocol.get("planned_confirmation_groups"):
        raise ValueError("confirmation differs from predeclared prompts")
    targets = signal_tasks(screen_protocol)
    if targets != signal_tasks(confirm_protocol):
        raise ValueError("unmatched signal tasks")
    arms = {}
    for task_id in sorted({task for task, _ in screen_protocol["groups"]}):
        first = screen.get("tasks", {}).get(task_id, {})
        fresh = confirmed.get("tasks", {}).get(task_id, {})
        independent = (screen.get("signal_gate_version") == confirmed.get("signal_gate_version") == 3
                       and first.get("sampling_identity_verified") is True
                       and fresh.get("sampling_identity_verified") is True)
        for field in ("client_label_hashes", "provider_response_id_hashes"):
            left = set(first.get("sampling_provenance", {}).get(field, []))
            right = set(fresh.get("sampling_provenance", {}).get(field, []))
            all_before = set(screen.get("sampling_provenance", {}).get(field, []))
            all_after = set(confirmed.get("sampling_provenance", {}).get(field, []))
            independent = (independent and bool(left) and bool(right)
                           and left.isdisjoint(all_after) and right.isdisjoint(all_before))
        before = {g["prompt_sha256"] for g in screen["groups"] if g["task_id"] == task_id}
        after = {g["prompt_sha256"] for g in confirmed["groups"] if g["task_id"] == task_id}
        prompts_disjoint = bool(before) and bool(after) and before.isdisjoint(after)
        arms[task_id] = {"signal_required": task_id in targets,
            "sampling_identities_disjoint": bool(independent), "prompt_identities_disjoint": prompts_disjoint,
            "confirmed": bool(first.get("genuine_signal_screened") and fresh.get("genuine_signal_screened")
                              and independent and prompts_disjoint)}
    independent = bool(targets) and all(arms[t]["sampling_identities_disjoint"] for t in targets)
    return {"provisional_single_family_signal_confirmed": screen["genuine_signal_screened"] and
            confirmed["genuine_signal_screened"] and bool(targets) and all(arms[t]["confirmed"] for t in targets),
            "signal_task_ids": targets, "tasks": arms,
            "sampling_identities_disjoint": bool(independent), "is_model_improvement": False,
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
