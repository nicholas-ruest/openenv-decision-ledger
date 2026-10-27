"""Measure controlled semantic defects inside prerequisite functions, without model calls."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repair_paths", ROOT / "scripts/audit-software-repair-paths.py")
PATHS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATHS)

DEFECTS = {
    3: (
        ("parent_pruning", "            if ignored:\n                break", "            if False:\n                break"),
        ("last_rule_wins", "for line in ignore_lines:", "for line in ignore_lines[::-1]:"),
        ("implicit_parents", 'prefixes = [path[:i] for i in range(len(path)) if path[i] == "/"] + [path]', "prefixes = [path]"),
    ),
    4: (
        ("negation", 'negative = line[0] == "!"', "negative = False"),
        ("root_relative_slash", 'anchored = anchored or "/" in line', "anchored = False"),
        ("directory_only", 'directory = line.endswith("/")', "directory = False"),
        ("literal_leading_space", "def rule_mode(line, path, is_dir):", "def rule_mode(line, path, is_dir):\n    line = line.strip()"),
    ),
}


def audit(level, seed):
    task = PATHS.make_task(f"software_repair-ignore-d{level}", seed)
    target = "classify_ignore" if level == 3 else "rule_mode"
    baseline = PATHS.measure(task, task.initial_source, task.hidden)
    reference = PATHS.functions(task.reference_source)
    variants = []
    for name, before, after in DEFECTS[level]:
        if task.reference_source.count(before) != 1:
            raise ValueError("semantic mutation anchor must be unique")
        source = task.reference_source.replace(before, after, 1)
        changed = {k for k, value in PATHS.functions(source).items() if value != reference[k]}
        if changed != {target}:
            raise ValueError("semantic mutation changed the supplied prerequisite")
        hidden = PATHS.measure(task, source, task.hidden)
        public = PATHS.measure(task, source, task.public)
        variants.append({"defect": name, "hidden": hidden, "public": public,
                         "hidden_cases": len(task.hidden), "public_cases": len(task.public),
                         "reward": PATHS.reward(task, hidden, baseline, False)})
    return {"task_id": task.task_id, "seed": seed, "target_function": target, "variants": variants}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    result = {"kind": "controlled_semantic_mutants_not_model_rollouts",
              "rows": [audit(level, 1860000 + i) for level in (3, 4) for i in range(8)],
              "model_calls": 0, "runtime_modified": False}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({"fixtures": len(result["rows"]), "model_calls": 0}))


if __name__ == "__main__":
    main()
