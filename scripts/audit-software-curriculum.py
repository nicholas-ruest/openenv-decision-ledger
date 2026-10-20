"""Offline repair-path audit; controlled edits are not model rollouts."""

import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/software-repair"))

from repair_env.runner import Program, Rejected
from repair_env.tasks import TRAINING_TASK_IDS, make_task, task_fingerprint, visible_files

DIAGNOSTICS = ["software_repair-plan-d3", "software_repair-plan-d4", "software_repair-release-d1"]


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) in (list, tuple):
        return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected))
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(exact(actual[k], expected[k]) for k in actual)
    return actual == expected


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def evaluate(task, source):
    program = Program(source)
    result = {}
    for split, cases in (("public", task.public), ("hidden", task.hidden)):
        passed, errors = 0, Counter()
        for case in cases:
            try:
                passed += exact(program.run(task.entrypoint, case.args), case.expected)
            except (Rejected, ArithmeticError, TypeError, ValueError, KeyError, IndexError,
                    RecursionError, RuntimeError) as exc:
                errors[type(exc).__name__] += 1
        result[split + "_passed"] = passed
        result[split + "_errors"] = dict(errors)
    return result


def edits(task):
    """Catalogue exact local edits; selecting a subset is a diagnostic only."""
    _, family, level = task.task_id.split("-")
    if family == "plan" and level in ("d3", "d4"):
        candidates = [
            ("unknown_dedup", "unknown = sorted([name for name in changed if name not in graph])",
             "unknown = sorted(set([name for name in changed if name not in graph]))"),
            ("ready_order", "order.append(max(ready))", "order.append(min(ready))"),
            ("cycles_order", '"cycles": sorted(cycles)[::-1]', '"cycles": sorted(cycles)'),
            ("component_order", "cycles.append(sorted(component)[::-1])", "cycles.append(sorted(component))"),
            ("affected_expansion", "while False:", "while growing:"),
            ("downstream_blocking", "for name in []:", "for name in affected:"),
        ]
    elif family == "release":
        candidates = [
            ("buildable_coverage", 'required = set(base["order"] + base["blocked"])',
             'required = set(base["order"])'),
            ("coverage_before_cost", "key = (cost, len(uncovered),", "key = (len(uncovered), cost,"),
            ("inclusive_budget", "if cost < budget:", "if cost <= budget:"),
            ("suite_tie_break", ", selected[::-1])", ", selected)"),
        ]
    elif family == "plan" and level == "d1":
        candidates = [("consumer_expansion", "growing = False\n    while", "growing = True\n    while")]
    elif family == "cover" and level == "d1":
        candidates = [
            ("cost_objective", "score = [len(chosen), cost, chosen]", "score = [cost, len(chosen), chosen]"),
            ("reported_cost_index", '"cost": best[1]', '"cost": best[0]'),
        ]
    elif family == "merge":
        candidates = [
            ("nested_end", "result[-1][1] = pair[1]", "result[-1][1] = max(result[-1][1], pair[1])"),
            ("touching_flag", "or pair[0] == result[-1][1]", "or merge_touching and pair[0] == result[-1][1]"),
        ]
    elif family == "replay":
        candidates = [
            ("undo", "                pass", '                active.pop(event["target"])'),
            ("duplicate_guard", "if True:", "if identifier not in seen:"),
        ]
    else:
        candidates = []
    return [(name, old, new) for name, old, new in candidates if old in task.initial_source]


def controls(task):
    local = edits(task)
    if local:
        for _, old, _ in local:
            if task.initial_source.count(old) != 1:
                raise ValueError("ambiguous controlled edit")
        repaired = task.initial_source
        for _, old, new in local:
            repaired = repaired.replace(old, new, 1)
        if Program(repaired).fingerprint != Program(task.reference_source).fingerprint:
            raise ValueError("catalogue does not completely restore the reference")
    variants = []
    for size in range(1, len(local)):
        for chosen in combinations(local, size):
            source = task.initial_source
            for _, old, new in chosen:
                source = source.replace(old, new, 1)
            variants.append(("local_edit_subset", [item[0] for item in chosen], source))
    # Empty stubs have no useful local-edit lattice. These separately labelled
    # controls implement one contract component using reference code.
    if task.task_id == "software_repair-plan-d2":
        source = task.reference_source.split("    result = []", 1)[0] + "    return sorted(affected)\n"
        variants.append(("component_control", ["affected_set_without_topological_order"], source))
    if task.task_id == "software_repair-cover-d2":
        source = task.reference_source.replace('"cost": best[0]', '"cost": 0')
        variants.append(("component_control", ["selection_without_reported_cost"], source))
    return local, variants


def audit_instance(task):
    baseline = evaluate(task, task.initial_source)
    reference = evaluate(task, task.reference_source)
    if reference["public_passed"] != 6 or reference["hidden_passed"] != 30:
        raise ValueError("reference disagrees with independent oracle or interpreter")
    if baseline["hidden_passed"] == 30:
        raise ValueError("baseline has no hidden defect")
    public = [fingerprint(case.args) for case in task.public]
    hidden = [fingerprint(case.args) for case in task.hidden]
    if len(set(public)) != 6 or len(set(hidden)) != 30 or set(public) & set(hidden):
        raise ValueError("duplicate or overlapping cases")
    local, variants = controls(task)
    measured = []
    for kind, names, source in variants:
        result = evaluate(task, source)
        passed = result["hidden_passed"]
        reward = (1.0 if passed == 30 else min(0.95, (passed - baseline["hidden_passed"]) /
                  (30 - baseline["hidden_passed"])) if passed > baseline["hidden_passed"] else 0.0)
        measured.append({"kind": kind, "edits": names, **result, "formula_reward": reward,
                         "public_full_hidden_incomplete": result["public_passed"] == 6 and passed < 30})
    files = visible_files(task)
    return {"task_id": task.task_id, "seed": task.seed, "task_fingerprint": task_fingerprint(task),
            "baseline": baseline, "reference": reference, "local_edit_count": len(local),
            "controlled_variants": measured,
            "workspace_utf8_bytes": {name: len(content.encode()) for name, content in files.items()},
            "public_hidden_disjoint": True, "counts_as_model_rollout": False}


def run(seed, count):
    if type(seed) is not int or type(count) is not int or not 1 <= count <= 32 or seed < 0:
        raise ValueError("bounded nonnegative seed range required")
    rows = [audit_instance(make_task(task_id, current))
            for task_id in TRAINING_TASK_IDS + DIAGNOSTICS for current in range(seed, seed + count)]
    summary = {}
    for task_id in TRAINING_TASK_IDS + DIAGNOSTICS:
        selected = [row for row in rows if row["task_id"] == task_id]
        variants = [item for row in selected for item in row["controlled_variants"]]
        valid = [item for item in variants if not item["hidden_errors"]]
        summary[task_id] = {
            "instances": len(selected), "in_provisional_training_mix": task_id in TRAINING_TASK_IDS,
            "baseline_public_passed": [row["baseline"]["public_passed"] for row in selected],
            "baseline_hidden_passed": [row["baseline"]["hidden_passed"] for row in selected],
            "controlled_variants": len(variants), "controlled_execution_failures": len(variants) - len(valid),
            "valid_zero_reward": sum(row["formula_reward"] == 0 for row in valid),
            "valid_partial_reward": sum(0 < row["formula_reward"] < 1 for row in valid),
            "valid_full_reward": sum(row["formula_reward"] == 1 for row in valid),
            "public_full_hidden_incomplete": sum(row["public_full_hidden_incomplete"] for row in valid),
        }
    return {"audit_version": 1, "seed_start": seed, "seed_count_per_task": count,
            "unique_task_instances": len(rows), "summary": summary, "rows": rows,
            "new_model_calls": 0, "is_training": False, "training_mix_changed": False,
            "limitations": ["Controlled edits are constructed diagnostics, not model actions.",
                            "The environment reward formula is reproduced; native parity is tested separately.",
                            "No within-prompt model variance, training or ranking gain is established.",
                            "Single-edit tasks have no proper nonempty edit subset.",
                            "Component controls for empty stubs are not local-edit subsets."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite an audit archive")
    report = run(args.seed, args.count)
    report["source_revision"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
    report["source_files_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in [Path(__file__), *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py"))]}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("unique_task_instances", "summary", "new_model_calls")}))


if __name__ == "__main__":
    main()
