"""Controlled function-repair paths; oracle edits are not model rollouts."""
import argparse
import ast
from collections import Counter
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/software-repair"))
from repair_env.runner import Program, Rejected
from repair_env.tasks import make_task

TASKS = ("software_repair-release-d4", "software_repair-kv-d2",
         "software_repair-ignore-d2")


def functions(source):
    lines = source.splitlines(keepends=True)
    return {node.name: "".join(lines[node.lineno - 1:node.end_lineno])
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def repair(source, reference, selected):
    replacements = functions(reference)
    lines = source.splitlines(keepends=True)
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef) and node.name in selected]
    if {node.name for node in nodes} != set(selected):
        raise ValueError("repair requires existing function names")
    for node in reversed(nodes):
        lines[node.lineno - 1:node.end_lineno] = [replacements[node.name]]
    return "".join(lines)


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(map(lambda pair: exact(*pair), zip(actual, expected)))
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(exact(actual[k], expected[k]) for k in actual)
    return actual == expected


def measure(task, source, cases):
    program = Program(source)
    passed, fields, errors = 0, 0, Counter()
    for case in cases:
        try:
            actual = program.run(task.entrypoint, case.args)
            passed += exact(actual, case.expected)
            if type(actual) is dict and type(case.expected) is dict:
                fields += sum(k in actual and exact(actual[k], v) for k, v in case.expected.items())
        except (Rejected, ArithmeticError, TypeError, ValueError, KeyError, IndexError,
                RecursionError, RuntimeError) as exc:
            errors[type(exc).__name__] += 1
    return {"passed": passed, "semantic_fields": fields, "errors": dict(errors)}


def reward(task, measured, baseline, unchanged):
    if unchanged:
        return 0.0
    if measured["passed"] == len(task.hidden):
        return 1.0
    components = task.task_id.startswith(("software_repair-kv-", "software_repair-ignore-"))
    metric = "semantic_fields" if components else "passed"
    total = sum(len(c.expected) for c in task.hidden) if components else len(task.hidden)
    improvement = measured[metric] - baseline[metric]
    return min(.95, improvement / (total - baseline[metric])) if improvement > 0 else 0.0


def audit(task_id, seed):
    task = make_task(task_id, seed)
    initial, reference = functions(task.initial_source), functions(task.reference_source)
    changed = sorted(name for name in initial if initial[name] != reference.get(name))
    if len(changed) > 8:
        raise ValueError("bounded audit permits at most eight changed functions")
    baseline = measure(task, task.initial_source, task.hidden)
    variants = []
    for count in range(len(changed) + 1):
        for selected in combinations(changed, count):
            source = repair(task.initial_source, task.reference_source, selected)
            hidden = measure(task, source, task.hidden)
            public = measure(task, source, task.public)
            variants.append({"repaired_functions": list(selected), "public": public,
                             "hidden": hidden, "reward": reward(task, hidden, baseline, not selected)})
    return {"task_id": task_id, "seed": seed, "changed_functions": changed,
            "fixture_sha256": hashlib.sha256(repr(task).encode()).hexdigest(), "variants": variants}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    rows = [audit(task, 1830000 + index) for task in TASKS for index in range(8)]
    result = {"kind": "controlled_oracle_function_repairs_not_model_solves", "rows": rows,
              "runtime_modified": False, "model_calls": 0,
              "limitations": ["Function-level oracle edits are not sampled model repairs.",
                              "Zero reward can be a real function dependency, not a grader defect.",
                              "This diagnostic alone does not justify a new runtime or task mix."]}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({"fixtures": len(rows), "variants": sum(len(r["variants"]) for r in rows),
                      "errors": sum(sum(v[s]["errors"].values()) for r in rows
                                    for v in r["variants"] for s in ("public", "hidden"))}))


if __name__ == "__main__":
    main()
