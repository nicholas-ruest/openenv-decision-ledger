"""Offline assessment of saved matched calibration rows; never launches calls."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re

RUNTIME = "0b8ccc3ca70a67fed5fc5837b69022261cc60497"
TASKS = tuple(f"software_repair-ignore-d{i}" for i in (2, 3, 4))
SEEDS = {"screen": (2180000, 2180100), "confirmation": (2190000, 2190100)}
FAILURES = {"format", "provider", "truncation", "execution", "budget"}


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("complete SHA256 identity required")
    return value


def assess(rows, phase):
    expected = {(task, seed, sample) for task in TASKS for seed in SEEDS[phase] for sample in range(4)}
    observed, calls, responses = set(), set(), set()
    groups = defaultdict(list)
    settings = set()
    for row in rows:
        if type(row.get("seed")) is not int or type(row.get("sample")) is not int:
            raise ValueError("integer procedural/sample identity required")
        key = (row.get("task_id"), row["seed"], row["sample"])
        if key not in expected or key in observed:
            raise ValueError("duplicate or unexpected sample")
        observed.add(key)
        if row.get("runtime_source") != RUNTIME:
            raise ValueError("frozen runtime mismatch")
        settings.add(sha(row.get("settings_sha256")))
        label = row.get("client_call_label")
        if not isinstance(label, str) or not label or label in calls:
            raise ValueError("independent call labels required")
        calls.add(label)
        for field in ("case_sha256", "prompt_sha256", "reset_sha256", "workspace_sha256"):
            sha(row.get(field))
        failure = row.get("failure")
        if failure is not None and failure not in FAILURES:
            raise ValueError("unknown failure class is not a semantic wrong answer")
        if failure is None:
            reward = row.get("reward")
            if type(reward) not in (int, float) or not math.isfinite(reward) or not 0 <= reward <= 1:
                raise ValueError("finite semantic reward required")
            response = sha(row.get("provider_response_id_sha256"))
            if response in responses:
                raise ValueError("replayed provider response")
            responses.add(response)
        groups[key[:2]].append(row)
    if observed != expected or len(settings) != 1:
        raise ValueError("incomplete experiment or mismatched settings")
    results, prompt_ids, workspace_ids = [], set(), set()
    case_by_seed = defaultdict(set)
    for (task, seed), group in sorted(groups.items()):
        for field in ("case_sha256", "prompt_sha256", "reset_sha256", "workspace_sha256"):
            if len({r[field] for r in group}) != 1:
                raise ValueError("same-prompt reset/workspace mismatch")
        prompt, workspace = group[0]["prompt_sha256"], group[0]["workspace_sha256"]
        if prompt in prompt_ids or workspace in workspace_ids:
            raise ValueError("distinct task/prompt groups require distinct identities")
        prompt_ids.add(prompt)
        workspace_ids.add(workspace)
        case_by_seed[seed].add(group[0]["case_sha256"])
        valid = [r["reward"] for r in group if r["failure"] is None]
        results.append({"task_id": task, "seed": seed, "valid": len(valid),
                        "full": sum(v == 1 for v in valid),
                        "partial": sum(0 < v < 1 for v in valid), "wrong": sum(v == 0 for v in valid),
                        "failures": dict(Counter(r["failure"] for r in group if r["failure"])),
                        "productive": len(valid) == 4 and 1 in valid and any(v < 1 for v in valid)})
    if any(len(v) != 1 for v in case_by_seed.values()) or len(set.union(*case_by_seed.values())) != 2:
        raise ValueError("unmatched cases across tasks or duplicate procedural prompts")
    return {"phase": phase, "groups": results, "settings_sha256": next(iter(settings)),
            "case_ids": sorted(set.union(*case_by_seed.values())), "prompt_ids": sorted(prompt_ids),
            "call_ids": sorted(calls), "response_ids": sorted(responses),
            "provisional_productive_tasks": [t for t in TASKS if all(g["productive"] for g in results if g["task_id"] == t)],
            "limitation": "Saved-row checks require separate raw-record attestation; no learning/promotion claim."}


def confirm(screen_rows, confirmation_rows):
    # Re-derive from samples; never trust a caller's productive-summary flag.
    screen = assess(screen_rows, "screen")
    confirmation = assess(confirmation_rows, "confirmation")
    if screen["settings_sha256"] != confirmation["settings_sha256"]:
        raise ValueError("matched confirmation settings required")
    for field in ("case_ids", "prompt_ids", "call_ids", "response_ids"):
        if set(screen[field]) & set(confirmation[field]):
            raise ValueError("confirmation replay or prompt leakage")
    return {"independently_productive_tasks": sorted(set(screen["provisional_productive_tasks"]) &
                                                     set(confirmation["provisional_productive_tasks"])),
            "model_improvement_claim": False, "promotion": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=tuple(SEEDS), required=True)
    parser.add_argument("--records", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assess([json.loads(x) for x in args.records.read_text().splitlines() if x], args.phase), indent=2))
