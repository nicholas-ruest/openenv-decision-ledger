"""Offline repair-path audit; controlled edits are not model rollouts."""

import argparse
from collections import Counter, defaultdict
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

DIAGNOSTICS = ["software_repair-plan-d3", "software_repair-plan-d4", "software_repair-release-d1",
               "software_repair-replay-d3"]


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


def typed_value(value, *, input_order=True):
    """No bool/int or list/tuple collapse; preserve observable input-map order.

    Expected dict order is ignored like the grader. This is a content identity,
    not an assertion that renamed/reordered inputs are semantically equivalent.
    """
    kind = type(value)
    if kind in (str, int, bool, type(None)):
        return [kind.__name__, value]
    if kind in (list, tuple):
        return [kind.__name__, [typed_value(item, input_order=input_order) for item in value]]
    if kind is dict:
        items = [[typed_value(key, input_order=input_order), typed_value(item, input_order=input_order)]
                 for key, item in value.items()]
        if not input_order:
            items.sort(key=lambda item: json.dumps(item[0], sort_keys=True))
        return ["dict", items]
    raise TypeError("unsupported audit identity type")


def contract_identity(task):
    return fingerprint([task.entrypoint, Program(task.reference_source).fingerprint])


def case_identity(task, case):
    return fingerprint([contract_identity(task), typed_value(case.args)])


def cohort_diversity(tasks):
    """Count actual content, not seed-bearing task IDs or source comments."""
    cases, suites = defaultdict(list), defaultdict(list)
    for task in tasks:
        contract = contract_identity(task)
        split_signatures = {}
        for split, items in (("public", task.public), ("hidden", task.hidden)):
            signatures = []
            for case in items:
                key = fingerprint([contract, typed_value(case.args)])
                label = fingerprint(typed_value(case.expected, input_order=False))
                cases[key].append({"task_id": task.task_id, "seed": task.seed, "split": split,
                                   "expected_sha256": label})
                signatures.append([key, label])
            split_signatures[split] = sorted(signatures)
        signature = fingerprint([contract, Program(task.initial_source).fingerprint, split_signatures])
        suites[signature].append({"task_id": task.task_id, "seed": task.seed})
    duplicated = {key: owners for key, owners in cases.items() if len(owners) > 1}
    cross_seed = {key: owners for key, owners in duplicated.items() if len({o["seed"] for o in owners}) > 1}
    cross_task = {key: owners for key, owners in duplicated.items() if len({o["task_id"] for o in owners}) > 1}
    split_overlap = {key: owners for key, owners in duplicated.items()
                     if {o["split"] for o in owners} == {"public", "hidden"}}
    conflicts = {key: owners for key, owners in cases.items()
                 if len({o["expected_sha256"] for o in owners}) > 1}
    return {"case_occurrences": sum(map(len, cases.values())), "distinct_input_keys": len(cases),
        "repeated_input_occurrences": sum(len(owners) - 1 for owners in duplicated.values()),
        "duplicated_input_keys": len(duplicated), "cross_seed_duplicate_input_keys": len(cross_seed),
        "cross_task_duplicate_input_keys": len(cross_task), "public_hidden_overlap_input_keys": len(split_overlap),
        "conflicting_expected_label_keys": len(conflicts),
        "seed_independent_content_suites": len(suites),
        "duplicated_content_suites": {key: owners for key, owners in suites.items() if len(owners) > 1},
        "duplicate_input_owners": duplicated, "conflicting_label_owners": conflicts,
        "identity_limitations": ["Input dict insertion order is preserved; expected dict order is ignored.",
            "Exact typed inputs are compared within the same reference-AST contract, not up to renaming.",
            "Seed and source comments are excluded from suite signatures; these are not observed prompt hashes.",
            "Cross-level reuse is reported, not automatically classified as data leakage."]}


def isolated_defects(task, local):
    """Leave one catalogued defect while fixing every other catalogued edit.

    Inverting repaired text is unsafe: correct loop text may occur elsewhere.
    Original defect sites are unique and checked before each forward edit.
    """
    measured = []
    for name, _, _ in local:
        mutant = task.initial_source
        for other, old, new in local:
            if other == name:
                continue
            if mutant.count(old) != 1:
                raise ValueError("ambiguous isolated defect forward edit")
            mutant = mutant.replace(old, new, 1)
        result = evaluate(task, mutant)
        public_errors, hidden_errors = bool(result["public_errors"]), bool(result["hidden_errors"])
        public_wrong = len(task.public) - result["public_passed"] - sum(result["public_errors"].values())
        hidden_wrong = len(task.hidden) - result["hidden_passed"] - sum(result["hidden_errors"].values())
        measured.append({"defect": name, **result, "public_wrong_answers": public_wrong,
            "hidden_wrong_answers": hidden_wrong,
            "public_semantic_detection": not public_errors and public_wrong > 0,
            "hidden_semantic_activation": not hidden_errors and hidden_wrong > 0,
            "hidden_active_public_missed": not public_errors and not hidden_errors
                and hidden_wrong > 0 and public_wrong == 0})
    return measured


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
    read_all = json.dumps(files, separators=(",", ":"))
    case_views = [json.dumps({"test": number, "args": case.args, "expected": case.expected},
                            separators=(",", ":")) for number, case in enumerate(task.public, 1)]
    return {"task_id": task.task_id, "seed": task.seed, "task_fingerprint": task_fingerprint(task),
            "baseline": baseline, "reference": reference, "local_edit_count": len(local),
            "controlled_variants": measured,
            "isolated_defects": isolated_defects(task, local),
            "isolated_defect_scope": "catalogued local edits only; empty-stub component controls excluded",
            "workspace_utf8_bytes": {name: len(content.encode()) for name, content in files.items()},
            "read_content_utf8_bytes": {"all": len(read_all.encode()), "source": len(files["src/solution.py"].encode()),
                                        "individual_public_cases": [len(text.encode()) for text in case_views]},
            "public_hidden_disjoint": True, "counts_as_model_rollout": False}


def run(seed, count, task_ids=None):
    if type(seed) is not int or type(count) is not int or not 1 <= count <= 32 or seed < 0:
        raise ValueError("bounded nonnegative seed range required")
    task_ids = TRAINING_TASK_IDS + DIAGNOSTICS if task_ids is None else task_ids
    if not task_ids or len(set(task_ids)) != len(task_ids) or not set(task_ids) <= set(TRAINING_TASK_IDS + DIAGNOSTICS):
        raise ValueError("known distinct audit task IDs required")
    tasks = [make_task(task_id, current) for task_id in task_ids for current in range(seed, seed + count)]
    rows = [audit_instance(task) for task in tasks]
    summary = {}
    for task_id in task_ids:
        selected = [row for row in rows if row["task_id"] == task_id]
        variants = [item for row in selected for item in row["controlled_variants"]]
        valid = [item for item in variants if not item["hidden_errors"]]
        defects = [item for row in selected for item in row["isolated_defects"]]
        summary[task_id] = {
            "instances": len(selected), "in_provisional_training_mix": task_id in TRAINING_TASK_IDS,
            "baseline_public_passed": [row["baseline"]["public_passed"] for row in selected],
            "baseline_hidden_passed": [row["baseline"]["hidden_passed"] for row in selected],
            "controlled_variants": len(variants), "controlled_execution_failures": len(variants) - len(valid),
            "valid_zero_reward": sum(row["formula_reward"] == 0 for row in valid),
            "valid_partial_reward": sum(0 < row["formula_reward"] < 1 for row in valid),
            "valid_full_reward": sum(row["formula_reward"] == 1 for row in valid),
            "public_full_hidden_incomplete": sum(row["public_full_hidden_incomplete"] for row in valid),
            "isolated_catalogued_defects": len(defects),
            "isolated_public_semantic_detections": sum(item["public_semantic_detection"] for item in defects),
            "isolated_hidden_semantic_activations": sum(item["hidden_semantic_activation"] for item in defects),
            "isolated_hidden_active_public_missed": sum(item["hidden_active_public_missed"] for item in defects),
            "isolated_execution_failures": sum(bool(item["public_errors"] or item["hidden_errors"]) for item in defects),
        }
    return {"audit_version": 2, "seed_start": seed, "seed_count_per_task": count,
            "unique_task_instances": len(rows), "summary": summary, "rows": rows,
            "cohort_diversity": cohort_diversity(tasks),
            "new_model_calls": 0, "is_training": False, "training_mix_changed": False,
            "limitations": ["Controlled edits are constructed diagnostics, not model actions.",
                            "The environment reward formula is reproduced; native parity is tested separately.",
                            "No within-prompt model variance, training or ranking gain is established.",
                            "Single-edit tasks have no proper nonempty edit subset.",
                            "Component controls for empty stubs are not local-edit subsets.",
                            "Byte counts reproduce read content only, not observation envelopes or tokenizer costs.",
                            "Isolated mutants measure catalogued defect detection, not arbitrary candidate-code coverage."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--tasks", nargs="+", choices=TRAINING_TASK_IDS + DIAGNOSTICS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite an audit archive")
    report = run(args.seed, args.count, args.tasks)
    report["source_revision"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
    report["source_files_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in [Path(__file__), *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py"))]}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("unique_task_instances", "summary", "new_model_calls")}))


if __name__ == "__main__":
    main()
